#!/bin/sh
set -eu

: "${AIRFLOW_DB_USER:?AIRFLOW_DB_USER is required}"
: "${AIRFLOW_DB_PASSWORD:?AIRFLOW_DB_PASSWORD is required}"
: "${AIRFLOW_DB_NAME:?AIRFLOW_DB_NAME is required}"

psql --set ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" <<-'EOSQL'
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS quality;
EOSQL

psql --set ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set airflow_db_user="$AIRFLOW_DB_USER" \
    --set airflow_db_password="$AIRFLOW_DB_PASSWORD" \
    --set airflow_db_name="$AIRFLOW_DB_NAME" <<-'EOSQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'airflow_db_user', :'airflow_db_password')
WHERE NOT EXISTS (
    SELECT FROM pg_catalog.pg_roles WHERE rolname = :'airflow_db_user'
) \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'airflow_db_name', :'airflow_db_user')
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = :'airflow_db_name'
) \gexec
EOSQL
