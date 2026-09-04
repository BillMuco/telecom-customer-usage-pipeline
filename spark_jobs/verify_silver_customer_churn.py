from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify silver customer churn Parquet output.")
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/silver/customer_churn",
        help="Silver Parquet folder visible to Spark.",
    )
    args = parser.parse_args()

    spark = SparkSession.builder.appName("verify-silver-customer-churn").getOrCreate()
    try:
        df = spark.read.parquet(args.input)
        print(f"Silver rows: {df.count()}")
        print(f"Silver columns: {len(df.columns)}")
        print(f"Null total_charges rows: {df.filter(F.col('total_charges').isNull()).count()}")
        print(f"Blank source TotalCharges tracked: {df.filter(F.col('total_charges_was_blank') == True).count()}")
        df.printSchema()
        df.select(
            "customer_id",
            "tenure",
            "total_charges",
            "total_charges_was_blank",
            "churn_flag",
            "tenure_band",
            "monthly_charge_band",
            "active_service_count",
        ).show(10, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
