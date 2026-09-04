"""Validate the business values in the Gold executive KPI Delta table."""

from __future__ import annotations

import argparse

from pyspark.sql import SparkSession


EXPECTED = {
    "total_customers": 7043,
    "churned_customers": 1869,
    "overall_churn_rate_pct": 26.54,
    "avg_monthly_charges": 64.76,
    "estimated_monthly_revenue": 456116.60,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/delta/gold/customer_churn/gold_executive_kpis",
        help="Gold executive KPI Delta table path visible to Spark.",
    )
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("test-gold-customer-churn-kpis")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )
    try:
        df = spark.read.format("delta").load(args.input)
        rows = df.collect()
        if len(rows) != 1:
            raise AssertionError(f"Expected exactly one KPI row, found {len(rows)}")

        row = rows[0].asDict()
        for column, expected in EXPECTED.items():
            actual = row[column]
            if isinstance(expected, float):
                if abs(float(actual) - expected) > 0.01:
                    raise AssertionError(f"{column}: expected {expected}, found {actual}")
            elif actual != expected:
                raise AssertionError(f"{column}: expected {expected}, found {actual}")

        print("Gold KPI tests passed")
        for column, expected in EXPECTED.items():
            print(f"{column}: {row[column]} (expected {expected})")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
