from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify bronze customer churn Parquet output.")
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/bronze/customer_churn",
        help="Bronze Parquet folder visible to Spark.",
    )
    args = parser.parse_args()

    spark = SparkSession.builder.appName("verify-bronze-customer-churn").getOrCreate()
    try:
        df = spark.read.parquet(args.input)
        print(f"Bronze rows: {df.count()}")
        print(f"Bronze columns: {len(df.columns)}")
        print(f"Blank total_charges rows: {df.filter(F.col('total_charges_was_blank') == True).count()}")
        df.printSchema()
        df.select(
            "customer_id",
            "tenure",
            "monthly_charges",
            "total_charges",
            "total_charges_was_blank",
            "churn",
        ).show(5, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
