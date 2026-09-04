# Bronze Ingestion

Bronze ingestion converts raw source files into a technical storage format that is easier for Spark to process.

## Customer Churn Bronze Job

Script:

```text
spark_jobs/bronze_customer_churn.py
```

Input:

```text
data/raw/customer_churn/telco_customer_churn.csv
```

Output:

```text
data/bronze/customer_churn/
```

## What The Job Does

- Reads the raw CSV with an explicit schema.
- Trims text fields.
- Renames columns from source style to snake_case.
- Casts numeric fields:
  - `senior_citizen` to integer
  - `tenure` to integer
  - `monthly_charges` to double
  - `total_charges` to double
- Keeps `total_charges_raw` for traceability.
- Adds `total_charges_was_blank` to track records where the source value was blank.
- Adds ingestion metadata:
  - `source_file`
  - `ingested_at_utc`
- Writes the result as Parquet.

## Idempotency

The job writes with `mode("overwrite")`.

That means rerunning the same job recreates the same bronze folder instead of appending duplicate records.

## Validation

The job fails if:

- The output would contain zero rows.
- `customer_id` is missing.
- `customer_id` contains duplicates.

## Run Command

From the project folder:

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/bronze_customer_churn.py
```
