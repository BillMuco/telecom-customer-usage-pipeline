# Delta Lake Local Support

Phase 4B adds local Delta Lake outputs while keeping the existing Parquet pipeline working.

## Why Delta Lake

Plain Parquet stores data files. Delta Lake stores Parquet data files plus a transaction log in `_delta_log`.

That log gives the lakehouse stronger behavior:

- safer overwrites
- schema tracking
- table history
- easier registration in Databricks
- better foundation for bronze, silver, and gold tables

## Current Local Approach

The existing Spark jobs already produce Parquet:

```text
data/bronze/customer_churn/
data/silver/customer_churn/
data/gold/customer_churn/
```

The Delta conversion job reads those Parquet layers and writes Delta copies:

```text
data/delta/bronze/customer_churn/
data/delta/silver/customer_churn/
data/delta/gold/customer_churn/
```

## Scripts

Write Delta layers:

```text
spark_jobs/write_delta_customer_churn_layers.py
```

Verify Delta layers:

```text
spark_jobs/verify_delta_customer_churn_layers.py
```

## Run Command

The base Spark Docker image does not include Delta Lake jars, so the command uses `--packages` to load Delta at runtime:

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --packages io.delta:delta-spark_2.12:3.2.0 `
  --conf spark.jars.ivy=/tmp/.ivy2 `
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension `
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/write_delta_customer_churn_layers.py
```

## Verify Command

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit `
  --packages io.delta:delta-spark_2.12:3.2.0 `
  --conf spark.jars.ivy=/tmp/.ivy2 `
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension `
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog `
  --master spark://spark-master:7077 `
  /opt/telecom-pipeline/spark_jobs/verify_delta_customer_churn_layers.py
```

## How To Recognize Delta Output

Each Delta table folder should contain:

```text
_delta_log/
part-....snappy.parquet
```

The Parquet file holds the actual data. The `_delta_log` folder holds Delta transaction metadata.
