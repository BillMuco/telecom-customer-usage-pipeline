from __future__ import annotations

import argparse
from pathlib import PurePosixPath

from pyspark.sql import SparkSession


GOLD_TABLES = [
    "gold_churn_by_contract",
    "gold_churn_by_tenure_band",
    "gold_churn_by_payment_method",
    "gold_customer_risk_summary",
    "gold_executive_kpis",
]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("verify-delta-customer-churn-layers")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def print_table_summary(spark: SparkSession, table_name: str, path: str) -> None:
    df = spark.read.format("delta").load(path)
    print(f"\n{table_name}")
    print(f"Path: {path}")
    print(f"Rows: {df.count()}")
    print(f"Columns: {len(df.columns)}")
    df.show(5, truncate=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify local Delta customer churn layers.")
    parser.add_argument(
        "--delta-root",
        default="/opt/telecom-pipeline/data/delta",
        help="Root folder containing Delta bronze/silver/gold data.",
    )
    args = parser.parse_args()

    spark = build_spark()
    delta_root = PurePosixPath(args.delta_root)

    try:
        print_table_summary(spark, "delta_bronze_customer_churn", str(delta_root / "bronze" / "customer_churn"))
        print_table_summary(spark, "delta_silver_customer_churn", str(delta_root / "silver" / "customer_churn"))

        for table_name in GOLD_TABLES:
            print_table_summary(
                spark,
                f"delta_{table_name}",
                str(delta_root / "gold" / "customer_churn" / table_name),
            )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
