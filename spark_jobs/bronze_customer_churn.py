from __future__ import annotations

import argparse

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType


RAW_COLUMNS = [
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
]


RENAMED_COLUMNS = {
    "customerID": "customer_id",
    "SeniorCitizen": "senior_citizen",
    "Partner": "partner",
    "Dependents": "dependents",
    "PhoneService": "phone_service",
    "MultipleLines": "multiple_lines",
    "InternetService": "internet_service",
    "OnlineSecurity": "online_security",
    "OnlineBackup": "online_backup",
    "DeviceProtection": "device_protection",
    "TechSupport": "tech_support",
    "StreamingTV": "streaming_tv",
    "StreamingMovies": "streaming_movies",
    "Contract": "contract",
    "PaperlessBilling": "paperless_billing",
    "PaymentMethod": "payment_method",
    "MonthlyCharges": "monthly_charges",
    "TotalCharges": "total_charges",
    "Churn": "churn",
}


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("telecom-bronze-customer-churn")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def read_raw_customer_churn(spark: SparkSession, input_path: str) -> DataFrame:
    schema = StructType([StructField(column, StringType(), True) for column in RAW_COLUMNS])
    return (
        spark.read.option("header", "true")
        .option("mode", "FAILFAST")
        .schema(schema)
        .csv(input_path)
    )


def to_bronze(raw_df: DataFrame, source_path: str) -> DataFrame:
    trimmed_df = raw_df.select([F.trim(F.col(column)).alias(column) for column in RAW_COLUMNS])

    renamed_df = trimmed_df
    for old_name, new_name in RENAMED_COLUMNS.items():
        renamed_df = renamed_df.withColumnRenamed(old_name, new_name)

    return (
        renamed_df.withColumn("senior_citizen", F.col("senior_citizen").cast("int"))
        .withColumn("tenure", F.col("tenure").cast("int"))
        .withColumn("monthly_charges", F.col("monthly_charges").cast("double"))
        .withColumn("total_charges_raw", F.col("total_charges"))
        .withColumn(
            "total_charges",
            F.when(F.col("total_charges") == "", F.lit(None)).otherwise(F.col("total_charges")).cast("double"),
        )
        .withColumn("total_charges_was_blank", F.col("total_charges_raw") == "")
        .withColumn("source_file", F.lit(source_path))
        .withColumn("ingested_at_utc", F.current_timestamp())
    )


def validate_bronze(bronze_df: DataFrame) -> None:
    row_count = bronze_df.count()
    if row_count == 0:
        raise ValueError("Bronze customer churn output has zero rows.")

    duplicate_customer_ids = (
        bronze_df.groupBy("customer_id")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )
    if duplicate_customer_ids > 0:
        raise ValueError(f"Found {duplicate_customer_ids} duplicated customer_id values.")

    missing_customer_ids = bronze_df.filter(F.col("customer_id").isNull() | (F.col("customer_id") == "")).count()
    if missing_customer_ids > 0:
        raise ValueError(f"Found {missing_customer_ids} rows with missing customer_id.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest raw Telco Customer Churn CSV to bronze Parquet.")
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/raw/customer_churn/telco_customer_churn.csv",
        help="Input raw CSV path visible to Spark.",
    )
    parser.add_argument(
        "--output",
        default="/opt/telecom-pipeline/data/bronze/customer_churn",
        help="Output bronze Parquet folder visible to Spark.",
    )
    args = parser.parse_args()

    spark = build_spark()
    try:
        raw_df = read_raw_customer_churn(spark, args.input)
        bronze_df = to_bronze(raw_df, args.input)
        validate_bronze(bronze_df)
        bronze_df.write.mode("overwrite").parquet(args.output)
        print(f"Bronze customer churn rows written: {bronze_df.count()}")
        print(f"Bronze output path: {args.output}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
