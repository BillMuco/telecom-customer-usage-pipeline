# Gold Analytics

Gold data is business-ready data. It is built for dashboards, reports, and decision-making.

## Customer Churn Gold Job

Script:

```text
spark_jobs/gold_customer_churn.py
```

Input:

```text
data/silver/customer_churn/
```

Output root:

```text
data/gold/customer_churn/
```

## Gold Tables Created

| Table | Business question |
| --- | --- |
| `gold_churn_by_contract` | Which contract types have the highest churn? |
| `gold_churn_by_tenure_band` | At what customer age does churn happen most? |
| `gold_churn_by_payment_method` | Do manual or automatic payment customers churn more? |
| `gold_customer_risk_summary` | Which customers look highest risk based on business rules? |
| `gold_executive_kpis` | What are the headline customer and revenue KPIs? |

## What The Job Does

- Reads the cleaned Silver customer churn Parquet data.
- Aggregates churn rates by important business dimensions.
- Creates a customer-level risk table using simple explainable rules.
- Creates one executive KPI table for reporting.
- Writes each Gold table as a separate Parquet dataset.

## Idempotency

Each Gold table writes with `mode("overwrite")`, so rerunning the job recreates the same outputs instead of appending duplicates.

## Run Command

From the project folder:

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/gold_customer_churn.py
```

## Verify Command

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/verify_gold_customer_churn.py
```
