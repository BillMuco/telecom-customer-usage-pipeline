from __future__ import annotations

import argparse

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


BOOLEAN_SOURCE_COLUMNS = [
    "partner",
    "dependents",
    "phone_service",
    "paperless_billing",
]

SERVICE_COLUMNS = [
    "phone_service",
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("telecom-silver-customer-churn")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def yes_no_to_boolean(column_name: str):
    return F.when(F.col(column_name) == "Yes", F.lit(True)).when(F.col(column_name) == "No", F.lit(False))


def build_tenure_band() -> F.Column:
    return (
        F.when(F.col("tenure") == 0, "new_customer")
        .when(F.col("tenure").between(1, 12), "1_12_months")
        .when(F.col("tenure").between(13, 24), "13_24_months")
        .when(F.col("tenure").between(25, 48), "25_48_months")
        .otherwise("49_plus_months")
    )


def build_monthly_charge_band() -> F.Column:
    return (
        F.when(F.col("monthly_charges") < 35, "low")
        .when(F.col("monthly_charges") < 70, "medium")
        .otherwise("high")
    )


def build_contract_months() -> F.Column:
    return (
        F.when(F.col("contract") == "Month-to-month", F.lit(1))
        .when(F.col("contract") == "One year", F.lit(12))
        .when(F.col("contract") == "Two year", F.lit(24))
    )


def build_payment_method_group() -> F.Column:
    return F.when(F.col("payment_method").contains("automatic"), "automatic").otherwise("manual")


def to_silver(bronze_df: DataFrame) -> DataFrame:
    silver_df = bronze_df.withColumn(
        "total_charges_clean",
        F.when(
            F.col("total_charges").isNull() & (F.col("tenure") == 0),
            F.lit(0.0),
        ).otherwise(F.col("total_charges")),
    )

    for column_name in BOOLEAN_SOURCE_COLUMNS:
        silver_df = silver_df.withColumn(f"is_{column_name}", yes_no_to_boolean(column_name))

    service_count_expr = sum(
        F.when(F.col(column_name) == "Yes", F.lit(1)).otherwise(F.lit(0))
        for column_name in SERVICE_COLUMNS
    )

    return (
        silver_df.withColumn("is_senior_citizen", F.col("senior_citizen") == 1)
        .withColumn("churn_flag", F.when(F.col("churn") == "Yes", F.lit(1)).otherwise(F.lit(0)))
        .withColumn("tenure_band", build_tenure_band())
        .withColumn("monthly_charge_band", build_monthly_charge_band())
        .withColumn("contract_months", build_contract_months())
        .withColumn("payment_method_group", build_payment_method_group())
        .withColumn("active_service_count", service_count_expr)
        .withColumn("average_charge_per_tenure_month", F.col("total_charges_clean") / F.greatest(F.col("tenure"), F.lit(1)))
        .withColumn("silver_transformed_at_utc", F.current_timestamp())
        .drop("total_charges")
        .withColumnRenamed("total_charges_clean", "total_charges")
    )


def validate_silver(silver_df: DataFrame) -> None:
    row_count = silver_df.count()
    if row_count == 0:
        raise ValueError("Silver customer churn output has zero rows.")

    duplicate_customer_ids = silver_df.groupBy("customer_id").count().filter(F.col("count") > 1).count()
    if duplicate_customer_ids > 0:
        raise ValueError(f"Found {duplicate_customer_ids} duplicated customer_id values.")

    null_total_charges = silver_df.filter(F.col("total_charges").isNull()).count()
    if null_total_charges > 0:
        raise ValueError(f"Found {null_total_charges} rows with null total_charges after silver cleaning.")

    invalid_churn_flags = silver_df.filter(~F.col("churn_flag").isin([0, 1]) | F.col("churn_flag").isNull()).count()
    if invalid_churn_flags > 0:
        raise ValueError(f"Found {invalid_churn_flags} invalid churn_flag values.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform bronze customer churn data to silver Parquet.")
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/bronze/customer_churn",
        help="Bronze customer churn Parquet path visible to Spark.",
    )
    parser.add_argument(
        "--output",
        default="/opt/telecom-pipeline/data/silver/customer_churn",
        help="Silver customer churn Parquet output path visible to Spark.",
    )
    args = parser.parse_args()

    spark = build_spark()
    try:
        bronze_df = spark.read.parquet(args.input)
        silver_df = to_silver(bronze_df)
        validate_silver(silver_df)
        silver_df.write.mode("overwrite").parquet(args.output)
        print(f"Silver customer churn rows written: {silver_df.count()}")
        print(f"Silver output path: {args.output}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
