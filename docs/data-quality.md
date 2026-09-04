# Data Quality

Data quality checks decide whether a dataset is safe to move from one layer to the next.

## Bronze Customer Churn Checks

Script:

```text
spark_jobs/quality_bronze_customer_churn.py
```

Input:

```text
data/bronze/customer_churn/
```

Reports:

```text
reports/data_quality/customer_churn_bronze_quality.json
reports/data_quality/customer_churn_bronze_quality.md
```

## Dimensions Covered

- Completeness: required columns, positive row count, non-missing customer IDs.
- Uniqueness: one row per `customer_id`.
- Validity: allowed category values.
- Accuracy: numeric values are not negative.
- Consistency: blank `total_charges` only appears when `tenure` is zero.
- Timeliness: ingestion metadata exists.

## Run Command

From the project folder:

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/quality_bronze_customer_churn.py
```

## Promotion Rule

The dataset can move to silver only when all critical checks pass.

Warnings are allowed, but they must be explained and handled in the silver transformation.
