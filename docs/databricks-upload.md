# Databricks Upload Path

Phase 4C prepares the local project to upload Delta Lake outputs to Databricks.

## Goal

The local pipeline already writes Delta tables here:

```text
data/delta/bronze/customer_churn/
data/delta/silver/customer_churn/
data/delta/gold/customer_churn/
```

The upload script copies those Delta folders to a Databricks Unity Catalog Volume:

```text
dbfs:/Volumes/<catalog>/<schema>/<volume>/telecom-customer-usage-pipeline/delta/
```

That gives Databricks access to the same bronze, silver, and gold Delta tables created locally.

## Required Databricks Values

Add these values to `.env`:

```text
DATABRICKS_HOST=https://dbc-xxxxxxxx-xxxx.cloud.databricks.com
DATABRICKS_TOKEN=your_personal_access_token
DATABRICKS_REMOTE_ROOT=dbfs:/Volumes/<catalog>/<schema>/<volume>/telecom-customer-usage-pipeline/delta
```

Do not commit `.env`. It contains secrets.

## Why Not FileStore

Some Databricks workspaces disable legacy public DBFS root storage. In that case, paths like this fail:

```text
dbfs:/FileStore/...
```

Use Unity Catalog Volumes instead:

```text
dbfs:/Volumes/<catalog>/<schema>/<volume>/...
```

This is better for governance because the files are controlled by catalog permissions.

## Create A Volume

In Databricks:

1. Open **Catalog**.
2. Choose or create a catalog.
3. Choose or create a schema.
4. Create a volume, for example `telecom_pipeline`.
5. Update `.env` with the real path.

Example:

```text
DATABRICKS_REMOTE_ROOT=dbfs:/Volumes/workspace/default/telecom_pipeline/telecom-customer-usage-pipeline/delta
```

Use the actual catalog and schema names from your workspace.

## Optional SQL Registration Values

Use these only after a Databricks SQL Warehouse exists:

```text
DATABRICKS_REGISTER_TABLES=true
DATABRICKS_WAREHOUSE_ID=your_sql_warehouse_id
DATABRICKS_SQL_SCHEMA=telecom_customer_usage
```

If Unity Catalog is configured, also set:

```text
DATABRICKS_SQL_CATALOG=your_catalog_name
```

## Dry Run

Run this first. It checks what would upload without calling Databricks:

```powershell
python .\scripts\upload_delta_to_databricks.py --dry-run
```

## Upload All Delta Layers

```powershell
python .\scripts\upload_delta_to_databricks.py --scope all
```

## Upload Gold Only

Gold-only upload is safer for dashboard tools because Gold tables are business-ready:

```powershell
python .\scripts\upload_delta_to_databricks.py --scope gold
```

## Upload And Register SQL Tables

Only use this after the SQL Warehouse is available:

```powershell
python .\scripts\upload_delta_to_databricks.py --scope gold --register-tables
```

Expected SQL tables:

```text
telecom_customer_usage.gold_churn_by_contract
telecom_customer_usage.gold_churn_by_tenure_band
telecom_customer_usage.gold_churn_by_payment_method
telecom_customer_usage.gold_customer_risk_summary
telecom_customer_usage.gold_executive_kpis
```

## Debugging

Common failures:

- `DATABRICKS_HOST and DATABRICKS_TOKEN`: `.env` is missing or incomplete.
- `401 Unauthorized`: token is wrong, expired, or copied with spaces.
- `403 Forbidden`: token user does not have permission to write to DBFS or create SQL tables.
- `Public DBFS root is disabled`: replace any `dbfs:/FileStore/...` path with a `dbfs:/Volumes/...` path.
- `DATABRICKS_WAREHOUSE_ID`: table registration was requested before creating a SQL Warehouse.
- No `_delta_log`: the local Delta writer has not been run yet.

## Sensitive Data Rule

Bronze and silver can contain customer-level data. For Godrisoft Insights, expose Gold tables first and use read-only access.

## Recruiter Explanation

This phase automates the handoff from local Spark Delta outputs to Databricks. It shows that the pipeline can move from local engineering to a cloud analytics serving layer without manually dragging files around.
