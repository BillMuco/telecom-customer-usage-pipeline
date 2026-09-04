from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


REQUIRED_COLUMNS = [
    "customer_id",
    "gender",
    "senior_citizen",
    "partner",
    "dependents",
    "tenure",
    "phone_service",
    "multiple_lines",
    "internet_service",
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
    "contract",
    "paperless_billing",
    "payment_method",
    "monthly_charges",
    "total_charges",
    "churn",
    "total_charges_raw",
    "total_charges_was_blank",
    "source_file",
    "ingested_at_utc",
]

DOMAIN_RULES = {
    "gender": ["Female", "Male"],
    "senior_citizen": [0, 1],
    "partner": ["No", "Yes"],
    "dependents": ["No", "Yes"],
    "phone_service": ["No", "Yes"],
    "internet_service": ["DSL", "Fiber optic", "No"],
    "contract": ["Month-to-month", "One year", "Two year"],
    "paperless_billing": ["No", "Yes"],
    "churn": ["No", "Yes"],
}


def build_spark() -> SparkSession:
    return SparkSession.builder.appName("quality-bronze-customer-churn").getOrCreate()


def add_check(
    checks: list[dict],
    *,
    name: str,
    dimension: str,
    severity: str,
    passed: bool,
    observed_value: int | str,
    rule: str,
) -> None:
    checks.append(
        {
            "name": name,
            "dimension": dimension,
            "severity": severity,
            "status": "PASS" if passed else "FAIL",
            "observed_value": observed_value,
            "rule": rule,
        }
    )


def count_missing(df: DataFrame, column: str) -> int:
    return df.filter(F.col(column).isNull() | (F.trim(F.col(column).cast("string")) == "")).count()


def run_quality_checks(df: DataFrame) -> dict:
    checks: list[dict] = []
    row_count = df.count()
    columns = df.columns

    missing_required_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    add_check(
        checks,
        name="required_columns_present",
        dimension="completeness",
        severity="critical",
        passed=len(missing_required_columns) == 0,
        observed_value=", ".join(missing_required_columns) if missing_required_columns else "None",
        rule="All expected bronze columns must be present.",
    )

    add_check(
        checks,
        name="row_count_positive",
        dimension="completeness",
        severity="critical",
        passed=row_count > 0,
        observed_value=row_count,
        rule="Bronze dataset must contain at least one row.",
    )

    if missing_required_columns:
        return {"row_count": row_count, "checks": checks}

    missing_customer_ids = count_missing(df, "customer_id")
    add_check(
        checks,
        name="customer_id_not_null",
        dimension="completeness",
        severity="critical",
        passed=missing_customer_ids == 0,
        observed_value=missing_customer_ids,
        rule="customer_id must not be missing.",
    )

    duplicate_customer_ids = df.groupBy("customer_id").count().filter(F.col("count") > 1).count()
    add_check(
        checks,
        name="customer_id_unique",
        dimension="uniqueness",
        severity="critical",
        passed=duplicate_customer_ids == 0,
        observed_value=duplicate_customer_ids,
        rule="customer_id must be unique in the customer baseline dataset.",
    )

    for column, allowed_values in DOMAIN_RULES.items():
        invalid_count = df.filter(~F.col(column).isin(allowed_values) | F.col(column).isNull()).count()
        add_check(
            checks,
            name=f"{column}_domain_valid",
            dimension="validity",
            severity="critical",
            passed=invalid_count == 0,
            observed_value=invalid_count,
            rule=f"{column} must be one of: {allowed_values}.",
        )

    numeric_rules = [
        ("tenure", F.col("tenure") < 0, "tenure must not be negative."),
        ("monthly_charges", F.col("monthly_charges") < 0, "monthly_charges must not be negative."),
        ("total_charges", F.col("total_charges") < 0, "total_charges must not be negative when present."),
    ]

    for column, condition, rule in numeric_rules:
        invalid_count = df.filter(condition).count()
        add_check(
            checks,
            name=f"{column}_non_negative",
            dimension="accuracy",
            severity="critical",
            passed=invalid_count == 0,
            observed_value=invalid_count,
            rule=rule,
        )

    blank_total_with_positive_tenure = df.filter((F.col("total_charges_was_blank") == True) & (F.col("tenure") > 0)).count()
    add_check(
        checks,
        name="blank_total_charges_only_for_zero_tenure",
        dimension="consistency",
        severity="critical",
        passed=blank_total_with_positive_tenure == 0,
        observed_value=blank_total_with_positive_tenure,
        rule="Blank total_charges is allowed only when tenure is zero.",
    )

    blank_total_count = df.filter(F.col("total_charges_was_blank") == True).count()
    add_check(
        checks,
        name="blank_total_charges_tracked",
        dimension="completeness",
        severity="warning",
        passed=True,
        observed_value=blank_total_count,
        rule="Blank source TotalCharges values must be tracked for silver cleaning.",
    )

    missing_ingestion_metadata = count_missing(df, "source_file") + df.filter(F.col("ingested_at_utc").isNull()).count()
    add_check(
        checks,
        name="ingestion_metadata_present",
        dimension="timeliness",
        severity="critical",
        passed=missing_ingestion_metadata == 0,
        observed_value=missing_ingestion_metadata,
        rule="source_file and ingested_at_utc must be populated.",
    )

    failed_critical_count = sum(1 for check in checks if check["severity"] == "critical" and check["status"] == "FAIL")

    return {
        "dataset": "bronze.customer_churn",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "column_count": len(columns),
        "failed_critical_count": failed_critical_count,
        "checks": checks,
    }


def write_reports(result: dict, json_output: Path, markdown_output: Path) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    json_output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Bronze Customer Churn Data Quality Report",
        "",
        f"- Dataset: `{result['dataset']}`",
        f"- Checked at UTC: `{result['checked_at_utc']}`",
        f"- Row count: `{result['row_count']}`",
        f"- Column count: `{result['column_count']}`",
        f"- Failed critical checks: `{result['failed_critical_count']}`",
        "",
        "## Checks",
        "",
        "| Check | Dimension | Severity | Status | Observed | Rule |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]

    for check in result["checks"]:
        lines.append(
            "| {name} | {dimension} | {severity} | {status} | {observed_value} | {rule} |".format(
                **check
            )
        )

    markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run data quality checks on bronze customer churn data.")
    parser.add_argument(
        "--input",
        default="/opt/telecom-pipeline/data/bronze/customer_churn",
        help="Bronze customer churn Parquet path visible to Spark.",
    )
    parser.add_argument(
        "--json-output",
        default="/opt/telecom-pipeline/reports/data_quality/customer_churn_bronze_quality.json",
        help="JSON quality report path.",
    )
    parser.add_argument(
        "--markdown-output",
        default="/opt/telecom-pipeline/reports/data_quality/customer_churn_bronze_quality.md",
        help="Markdown quality report path.",
    )
    args = parser.parse_args()

    spark = build_spark()
    try:
        df = spark.read.parquet(args.input)
        result = run_quality_checks(df)
        write_reports(result, Path(args.json_output), Path(args.markdown_output))
        print(f"Quality dataset: {result['dataset']}")
        print(f"Rows checked: {result['row_count']}")
        print(f"Critical failures: {result['failed_critical_count']}")
        print(f"JSON report: {args.json_output}")
        print(f"Markdown report: {args.markdown_output}")
        if result["failed_critical_count"] > 0:
            raise RuntimeError("Critical data quality checks failed.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
