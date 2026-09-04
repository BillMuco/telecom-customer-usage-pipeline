[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
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
        $output = & docker compose @Arguments 2>&1
        if ($LASTEXITCODE -ne 0) {
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
        & docker compose exec -T airflow-scheduler `
            python -m airflow jobs check --job-type SchedulerJob --local *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 5
    }
    throw "Airflow scheduler did not become ready within $TimeoutSeconds seconds."
}

function Get-DagState {
    $output = Invoke-DockerCompose -Capture -Arguments @(
        "exec", "-T", "airflow-scheduler",
        "python", "-m", "airflow", "dags", "state", $DagId, $RunId
    )

    $knownStates = @("queued", "running", "success", "failed")
    $state = $output |
        ForEach-Object { $_.ToString().Trim().ToLowerInvariant() } |
        Where-Object { $knownStates -contains $_ } |
        Select-Object -Last 1

    if (-not $state) {
        throw "Could not determine the DAG state from Airflow output."
    }
    return $state
}

Push-Location $ProjectRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker is not available. Start Docker Desktop and try again."
    }
    if (-not (Test-Path -LiteralPath $SourceCsv -PathType Leaf)) {
        throw "Missing source CSV: $SourceCsv"
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
        Write-Host "Running repository validation tests..." -ForegroundColor Cyan
        & python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Repository validation tests failed."
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
