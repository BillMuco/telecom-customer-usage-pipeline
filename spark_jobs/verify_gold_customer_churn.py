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


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify gold customer churn Parquet outputs.")
    parser.add_argument(
        "--input-root",
        default="/opt/telecom-pipeline/data/gold/customer_churn",
        help="Gold customer churn root folder visible to Spark.",
    )
    args = parser.parse_args()

    spark = SparkSession.builder.appName("verify-gold-customer-churn").getOrCreate()
    try:
        for table_name in GOLD_TABLES:
            path = str(PurePosixPath(args.input_root) / table_name)
            df = spark.read.parquet(path)
            print(f"\n{table_name}")
            print(f"Rows: {df.count()}")
            df.printSchema()
            df.show(10, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
