# Silver Transformation

Silver data is cleaned, standardized, and prepared for analytics.

## Customer Churn Silver Job

Script:

```text
spark_jobs/silver_customer_churn.py
```

Input:

```text
data/bronze/customer_churn/
```

Output:

```text
data/silver/customer_churn/
```

## What The Job Does

- Reads validated bronze Parquet.
- Replaces blank `total_charges` values with `0.0` only when `tenure` is `0`.
- Keeps `total_charges_raw` and `total_charges_was_blank` for traceability.
- Adds boolean fields such as `is_partner`, `is_dependents`, and `is_phone_service`.
- Adds `churn_flag` for analytics and modeling.
- Adds business-friendly fields:
  - `tenure_band`
  - `monthly_charge_band`
  - `contract_months`
  - `payment_method_group`
  - `active_service_count`
  - `average_charge_per_tenure_month`
- Writes silver output as Parquet.

## Idempotency

The job writes with `mode("overwrite")`, so rerunning the same transformation recreates the silver output instead of appending duplicates.

## Validation

The job fails if:

- The output has zero rows.
- `customer_id` is duplicated.
- `total_charges` is still null after cleaning.
- `churn_flag` is not `0` or `1`.

## Run Command

From the project folder:

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/silver_customer_churn.py
```
