from __future__ import annotations

import argparse
from pathlib import PurePosixPath

from pyspark.sql import DataFrame, SparkSession


GOLD_TABLES = [
    "gold_churn_by_contract",
    "gold_churn_by_tenure_band",
    "gold_churn_by_payment_method",
    "gold_customer_risk_summary",
    "gold_executive_kpis",
]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("telecom-delta-customer-churn-layers")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def write_delta(df: DataFrame, output_path: str) -> None:
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write local Delta copies of customer churn bronze, silver, and gold layers.")
    parser.add_argument(
        "--parquet-root",
        default="/opt/telecom-pipeline/data",
        help="Root folder containing existing Parquet bronze/silver/gold data.",
    )
    parser.add_argument(
        "--delta-root",
        default="/opt/telecom-pipeline/data/delta",
        help="Root folder where Delta bronze/silver/gold data will be written.",
    )
    args = parser.parse_args()

    spark = build_spark()
    parquet_root = PurePosixPath(args.parquet_root)
    delta_root = PurePosixPath(args.delta_root)

    try:
        bronze_df = spark.read.parquet(str(parquet_root / "bronze" / "customer_churn"))
        bronze_output = str(delta_root / "bronze" / "customer_churn")
        write_delta(bronze_df, bronze_output)
        print(f"delta bronze customer_churn: wrote {bronze_df.count()} rows to {bronze_output}")

        silver_df = spark.read.parquet(str(parquet_root / "silver" / "customer_churn"))
        silver_output = str(delta_root / "silver" / "customer_churn")
        write_delta(silver_df, silver_output)
        print(f"delta silver customer_churn: wrote {silver_df.count()} rows to {silver_output}")

        for table_name in GOLD_TABLES:
            gold_input = str(parquet_root / "gold" / "customer_churn" / table_name)
            gold_output = str(delta_root / "gold" / "customer_churn" / table_name)
            gold_df = spark.read.parquet(gold_input)
            write_delta(gold_df, gold_output)
            print(f"delta gold {table_name}: wrote {gold_df.count()} rows to {gold_output}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
