"""Airflow orchestration for the telecom customer churn pipeline.

The Spark connection should point to the local Spark master:
spark://spark-master:7077
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator


SPARK_CONNECTION = "spark_local"
SPARK_JOBS = "/opt/telecom-pipeline/spark_jobs"

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def spark_task(task_id: str, application: str) -> SparkSubmitOperator:
    return SparkSubmitOperator(
        task_id=task_id,
        conn_id=SPARK_CONNECTION,
        application=f"{SPARK_JOBS}/{application}",
        name=task_id,
        verbose=False,
    )


with DAG(
    dag_id="telecom_customer_usage_pipeline",
    description="Run Bronze, quality, Silver, and Gold telecom analytics processing.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["telecom", "spark", "customer-churn"],
) as dag:
    ingest_bronze = spark_task("ingest_bronze", "bronze_customer_churn.py")
    validate_bronze = spark_task("validate_bronze", "quality_bronze_customer_churn.py")
    transform_silver = spark_task("transform_silver", "silver_customer_churn.py")
    build_gold = spark_task("build_gold", "gold_customer_churn.py")
    verify_outputs = spark_task("verify_outputs", "verify_gold_customer_churn.py")

    ingest_bronze >> validate_bronze >> transform_silver >> build_gold >> verify_outputs
