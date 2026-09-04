from __future__ import annotations

import argparse
from pathlib import PurePosixPath

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


GOLD_TABLES = [
    "gold_churn_by_contract",
    "gold_churn_by_tenure_band",
    "gold_churn_by_payment_method",
    "gold_customer_risk_summary",
    "gold_executive_kpis",
]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("telecom-gold-customer-churn")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def churn_summary(df: DataFrame, group_column: str) -> DataFrame:
    return (
        df.groupBy(group_column)
        .agg(
            F.count("*").alias("total_customers"),
            F.sum("churn_flag").alias("churned_customers"),
            F.round(F.avg("churn_flag") * 100, 2).alias("churn_rate_pct"),
            F.round(F.avg("monthly_charges"), 2).alias("avg_monthly_charges"),
            F.round(F.avg("total_charges"), 2).alias("avg_total_charges"),
        )
        .withColumn("gold_created_at_utc", F.current_timestamp())
        .orderBy(F.desc("churn_rate_pct"), F.desc("total_customers"))
    )


def build_customer_risk_summary(df: DataFrame) -> DataFrame:
    risk_score = (
        F.when(F.col("contract") == "Month-to-month", F.lit(30)).otherwise(F.lit(0))
        + F.when(F.col("tenure") <= 12, F.lit(25)).otherwise(F.lit(0))
        + F.when(F.col("monthly_charge_band") == "high", F.lit(20)).otherwise(F.lit(0))
        + F.when(F.col("internet_service") == "Fiber optic", F.lit(10)).otherwise(F.lit(0))
        + F.when(F.col("payment_method_group") == "manual", F.lit(10)).otherwise(F.lit(0))
        + F.when(F.col("active_service_count") <= 2, F.lit(5)).otherwise(F.lit(0))
    )

    return (
        df.select(
            "customer_id",
            "gender",
            "senior_citizen",
            "tenure",
            "tenure_band",
            "contract",
            "payment_method_group",
            "internet_service",
            "monthly_charges",
            "monthly_charge_band",
            "total_charges",
            "active_service_count",
            "churn",
            "churn_flag",
        )
        .withColumn("risk_score", risk_score)
        .withColumn(
            "risk_level",
            F.when(F.col("risk_score") >= 70, "high")
            .when(F.col("risk_score") >= 40, "medium")
            .otherwise("low"),
        )
        .withColumn("gold_created_at_utc", F.current_timestamp())
        .orderBy(F.desc("risk_score"), F.desc("monthly_charges"))
    )


def build_executive_kpis(df: DataFrame) -> DataFrame:
    return df.agg(
        F.count("*").alias("total_customers"),
        F.sum("churn_flag").alias("churned_customers"),
        F.round(F.avg("churn_flag") * 100, 2).alias("overall_churn_rate_pct"),
        F.round(F.avg("monthly_charges"), 2).alias("avg_monthly_charges"),
        F.round(F.sum("monthly_charges"), 2).alias("estimated_monthly_revenue"),
        F.round(F.avg("total_charges"), 2).alias("avg_total_charges"),
        F.round(F.avg("active_service_count"), 2).alias("avg_active_service_count"),
    ).withColumn("gold_created_at_utc", F.current_timestamp())


def build_gold_tables(silver_df: DataFrame) -> dict[str, DataFrame]:
    return {
        "gold_churn_by_contract": churn_summary(silver_df, "contract"),
        "gold_churn_by_tenure_band": churn_summary(silver_df, "tenure_band"),
        "gold_churn_by_payment_method": churn_summary(silver_df, "payment_method_group"),
        "gold_customer_risk_summary": build_customer_risk_summary(silver_df),
        "gold_executive_kpis": build_executive_kpis(silver_df),
    }


def validate_gold_table(table_name: str, df: DataFrame) -> int:
    row_count = df.count()
    if row_count == 0:
        raise ValueError(f"{table_name} has zero rows.")
    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build gold analytics tables from silver customer churn data.")
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/silver/customer_churn",
        help="Silver customer churn Parquet path visible to Spark.",
    )
    parser.add_argument(
        "--output-root",
        default="/opt/telecom-pipeline/data/gold/customer_churn",
        help="Gold output root folder visible to Spark.",
    )
    args = parser.parse_args()

    spark = build_spark()
    try:
        silver_df = spark.read.parquet(args.input)
        gold_tables = build_gold_tables(silver_df)

        for table_name in GOLD_TABLES:
            gold_df = gold_tables[table_name]
            row_count = validate_gold_table(table_name, gold_df)
            output_path = str(PurePosixPath(args.output_root) / table_name)
            gold_df.write.mode("overwrite").parquet(output_path)
            print(f"{table_name}: wrote {row_count} rows to {output_path}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
