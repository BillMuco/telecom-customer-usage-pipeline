# Docker Platform Runbook

This runbook describes the local runtime platform for the telecom data engineering project.

## Services

- PostgreSQL: analytics database
- Spark master: Spark cluster coordinator
- Spark worker: Spark execution worker
- Airflow webserver: DAG UI and API
- Airflow scheduler: orchestration and Spark submission

Airflow mounts `./data` and `./reports` at `/opt/telecom-pipeline` so Spark jobs and orchestration tasks share the same pipeline artifacts.

## First-Time Setup

From the project folder:

```powershell
Copy-Item .env.example .env
docker compose up -d
```

Before starting Docker, replace the `change_me_...` Airflow database and administrator passwords in `.env`. The PostgreSQL initialization script creates the Airflow role and database from those environment values on a new volume.

Existing PostgreSQL volumes retain the credentials with which they were originally initialized. Changing `AIRFLOW_DB_PASSWORD` later requires a matching database-role password update or an intentional local database reset.

## Verify Services

Check containers:

```powershell
docker compose ps
```

Check PostgreSQL:

```powershell
docker compose exec postgres psql -U telecom_user -d telecom_analytics -c "\dn"
```

Expected schemas:

```text
bronze
silver
gold
quality
```

Check Spark:

```powershell
docker compose exec spark-master /opt/spark/bin/spark-submit --version
```

Spark UI:

```text
http://localhost:8081
```

Spark Worker UI:

```text
http://localhost:8082
```

Airflow UI:

```text
http://localhost:8080
```

Verify the DAG is registered without import errors:

```powershell
docker compose exec -T airflow-scheduler python -m airflow dags list-import-errors
docker compose exec -T airflow-scheduler python -m airflow dags list
```

## Stop Services

```powershell
docker compose down
```

To remove the PostgreSQL volume and reset the database:

```powershell
docker compose down -v
```

Use `down -v` only when you intentionally want to delete local database state.
