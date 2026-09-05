[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [ValidateSet("sample", "ibm")]
    [string]$DataSource = "sample",
    [switch]$ForceDataSetup,
    [int]$TimeoutSeconds = 1200,
    [int]$PollSeconds = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DagId = "telecom_customer_usage_pipeline"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourceCsv = Join-Path $ProjectRoot "data\raw\customer_churn\telco_customer_churn.csv"
$RunId = "demo__$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))"

function Invoke-DockerCompose {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [switch]$Capture
    )

    if ($Capture) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $output = & docker compose @Arguments 2>&1
            $dockerComposeExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }

        if ($dockerComposeExitCode -ne 0) {
            throw "docker compose $($Arguments -join ' ') failed:`n$($output -join [Environment]::NewLine)"
        }
        return $output
    }

    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

function Wait-ForScheduler {
    param([datetime]$Deadline)

    Write-Host "Waiting for the Airflow scheduler..." -ForegroundColor Cyan
    while ([DateTime]::UtcNow -lt $Deadline) {
        # Windows PowerShell converts native stderr into an ErrorRecord. During
        # startup Airflow legitimately reports "No alive jobs found", so keep
        # that probe non-terminating and use its process exit code for polling.
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & docker compose exec -T airflow-scheduler `
                python -m airflow jobs check --job-type SchedulerJob --local *> $null
            $schedulerCheckExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }

        if ($schedulerCheckExitCode -eq 0) {
            return
        }
        Start-Sleep -Seconds 5
    }
    throw "Airflow scheduler did not become ready within $TimeoutSeconds seconds."
}

function Get-DagState {
    $output = Invoke-DockerCompose -Capture -Arguments @(
        "exec", "-T", "airflow-scheduler",
        "python", "-c",
        "import sys; from airflow.models import DagRun; from airflow.settings import Session; session = Session(); run = session.query(DagRun).filter(DagRun.dag_id == sys.argv[1], DagRun.run_id == sys.argv[2]).one_or_none(); print(run.state if run else 'not_found'); session.close()",
        $DagId, $RunId
    )

    $knownStates = @("not_found", "queued", "running", "success", "failed")
    $state = $output |
        ForEach-Object { $_.ToString().Trim().ToLowerInvariant() } |
        Where-Object { $knownStates -contains $_ } |
        Select-Object -Last 1

    if (-not $state) {
        throw "Could not determine the DAG state from Airflow output."
    }
    if ($state -eq "not_found") {
        return "queued"
    }
    return $state
}

Push-Location $ProjectRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is not available. Start Docker Desktop and try again."
    }
    if ($ForceDataSetup -or -not (Test-Path -LiteralPath $SourceCsv -PathType Leaf)) {
        Write-Host "Preparing the $DataSource source dataset..." -ForegroundColor Cyan
        $setupArguments = @("$PSScriptRoot\setup_data.py", "--source", $DataSource)
        if ($ForceDataSetup) {
            $setupArguments += "--force"
        }
        & python @setupArguments
        if ($LASTEXITCODE -ne 0) {
            throw "Dataset setup failed."
        }
    }

    Write-Host "Validating Docker Compose configuration..." -ForegroundColor Cyan
    Invoke-DockerCompose -Arguments @("config", "--quiet")

    $upArguments = @("up", "-d")
    if (-not $SkipBuild) {
        $upArguments += "--build"
    }
    Write-Host "Starting the local platform..." -ForegroundColor Cyan
    Invoke-DockerCompose -Arguments $upArguments

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    Wait-ForScheduler -Deadline $deadline

    Write-Host "Checking DAG imports..." -ForegroundColor Cyan
    Invoke-DockerCompose -Arguments @(
        "exec", "-T", "airflow-scheduler",
        "python", "-m", "airflow", "dags", "list-import-errors"
    )

    Write-Host "Triggering $DagId as $RunId..." -ForegroundColor Cyan
    Invoke-DockerCompose -Arguments @(
        "exec", "-T", "airflow-scheduler",
        "python", "-m", "airflow", "dags", "trigger", "--run-id", $RunId, $DagId
    )

    do {
        Start-Sleep -Seconds $PollSeconds
        $state = Get-DagState
        Write-Host "DAG state: $state"
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "DAG run exceeded the $TimeoutSeconds-second timeout."
        }
    } while ($state -notin @("success", "failed"))

    Write-Host "Final task states:" -ForegroundColor Cyan
    Invoke-DockerCompose -Arguments @(
        "exec", "-T", "airflow-scheduler",
        "python", "-m", "airflow", "tasks", "states-for-dag-run", $DagId, $RunId
    )

    if ($state -ne "success") {
        throw "The demonstration DAG run failed. Inspect its task logs at http://localhost:8080."
    }

    if (-not $SkipTests) {
        Write-Host "Running fresh-clone unit tests..." -ForegroundColor Cyan
        & python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Fresh-clone unit tests failed."
        }

        Write-Host "Running generated-output integration tests..." -ForegroundColor Cyan
        & python -m pytest -q -m integration
        if ($LASTEXITCODE -ne 0) {
            throw "Generated-output integration tests failed."
        }
    }

    Write-Host ""
    Write-Host "Demo completed successfully." -ForegroundColor Green
    Write-Host "Run ID: $RunId"
    Write-Host "Airflow: http://localhost:8080/dags/$DagId/grid"
    Write-Host "Spark master: http://localhost:8081"
    Write-Host "Quality report: reports/data_quality/customer_churn_bronze_quality.md"
}
finally {
    Pop-Location
}

