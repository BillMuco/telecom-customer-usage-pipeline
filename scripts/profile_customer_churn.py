from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


EXPECTED_COLUMNS = [
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

NUMERIC_COLUMNS = ["tenure", "MonthlyCharges", "TotalCharges"]
CATEGORICAL_COLUMNS = ["gender", "SeniorCitizen", "Contract", "InternetService", "PaymentMethod", "Churn"]


def parse_decimal(value: str) -> Decimal | None:
    value = value.strip()
    if value == "":
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def profile(input_path: Path) -> dict:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row.")

        columns = reader.fieldnames
        missing_by_column = Counter()
        category_counts: dict[str, Counter] = {column: Counter() for column in CATEGORICAL_COLUMNS}
        numeric_invalid = Counter()
        numeric_negative = Counter()
        numeric_min: dict[str, Decimal | None] = {column: None for column in NUMERIC_COLUMNS}
        numeric_max: dict[str, Decimal | None] = {column: None for column in NUMERIC_COLUMNS}
        customer_ids = Counter()
        sample_rows = []
        row_count = 0

        for row in reader:
            row_count += 1
            if len(sample_rows) < 5:
                sample_rows.append(row)

            customer_id = row.get("customerID", "").strip()
            if customer_id:
                customer_ids[customer_id] += 1

            for column in columns:
                if row.get(column, "").strip() == "":
                    missing_by_column[column] += 1

            for column in CATEGORICAL_COLUMNS:
                if column in row:
                    category_counts[column][row[column].strip() or "<missing>"] += 1

            for column in NUMERIC_COLUMNS:
                if column not in row:
                    continue
                value = parse_decimal(row[column])
                if value is None:
                    numeric_invalid[column] += 1
                    continue
                if value < 0:
                    numeric_negative[column] += 1
                if numeric_min[column] is None or value < numeric_min[column]:
                    numeric_min[column] = value
                if numeric_max[column] is None or value > numeric_max[column]:
                    numeric_max[column] = value

    duplicate_customer_ids = {customer_id: count for customer_id, count in customer_ids.items() if count > 1}

    return {
        "input_path": input_path,
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "missing_expected_columns": [column for column in EXPECTED_COLUMNS if column not in columns],
        "unexpected_columns": [column for column in columns if column not in EXPECTED_COLUMNS],
        "missing_by_column": missing_by_column,
        "duplicate_customer_id_count": len(duplicate_customer_ids),
        "category_counts": category_counts,
        "numeric_invalid": numeric_invalid,
        "numeric_negative": numeric_negative,
        "numeric_min": numeric_min,
        "numeric_max": numeric_max,
        "sample_rows": sample_rows,
    }


def write_markdown_report(result: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Customer Churn Raw Data Profile",
        "",
        f"- Input file: `{result['input_path']}`",
        f"- Row count: `{result['row_count']}`",
        f"- Column count: `{result['column_count']}`",
        "",
        "## Schema Check",
        "",
        f"- Missing expected columns: `{', '.join(result['missing_expected_columns']) or 'None'}`",
        f"- Unexpected columns: `{', '.join(result['unexpected_columns']) or 'None'}`",
        "",
        "## Missing Values",
        "",
        "| Column | Missing rows |",
        "| --- | ---: |",
    ]

    for column in result["columns"]:
        lines.append(f"| {column} | {result['missing_by_column'].get(column, 0)} |")

    lines.extend(
        [
            "",
            "## Duplicate Customer IDs",
            "",
            f"- Duplicate `customerID` values: `{result['duplicate_customer_id_count']}`",
            "",
            "## Numeric Checks",
            "",
            "| Column | Invalid/blank numeric values | Negative values | Min | Max |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for column in NUMERIC_COLUMNS:
        lines.append(
            "| {column} | {invalid} | {negative} | {minimum} | {maximum} |".format(
                column=column,
                invalid=result["numeric_invalid"].get(column, 0),
                negative=result["numeric_negative"].get(column, 0),
                minimum=result["numeric_min"].get(column),
                maximum=result["numeric_max"].get(column),
            )
        )

    lines.extend(["", "## Category Distributions", ""])

    for column, counts in result["category_counts"].items():
        lines.extend([f"### {column}", "", "| Value | Rows |", "| --- | ---: |"])
        for value, count in counts.most_common():
            lines.append(f"| {value} | {count} |")
        lines.append("")

    lines.extend(["## Sample Rows", "", "| customerID | tenure | MonthlyCharges | TotalCharges | Churn |", "| --- | ---: | ---: | ---: | --- |"])

    for row in result["sample_rows"]:
        lines.append(
            "| {customerID} | {tenure} | {MonthlyCharges} | {TotalCharges} | {Churn} |".format(
                customerID=row.get("customerID", ""),
                tenure=row.get("tenure", ""),
                MonthlyCharges=row.get("MonthlyCharges", ""),
                TotalCharges=row.get("TotalCharges", ""),
                Churn=row.get("Churn", ""),
            )
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(result: dict, output_path: Path) -> None:
    print("Customer churn raw data profile")
    print(f"Input: {result['input_path']}")
    print(f"Rows: {result['row_count']}")
    print(f"Columns: {result['column_count']}")
    print(f"Missing expected columns: {result['missing_expected_columns'] or 'None'}")
    print(f"Unexpected columns: {result['unexpected_columns'] or 'None'}")
    print(f"Duplicate customerID values: {result['duplicate_customer_id_count']}")
    print("Numeric invalid/blank values:")
    for column in NUMERIC_COLUMNS:
        print(f"  {column}: {result['numeric_invalid'].get(column, 0)}")
    print(f"Report written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the raw Telco Customer Churn CSV.")
    parser.add_argument(
        "--input",
        default="data/raw/customer_churn/telco_customer_churn.csv",
        help="Path to the raw customer churn CSV.",
    )
    parser.add_argument(
        "--output",
        default="reports/data_profiles/customer_churn_profile.md",
        help="Path for the Markdown profile report.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    result = profile(input_path)
    write_markdown_report(result, output_path)
    print_summary(result, output_path)


if __name__ == "__main__":
    main()
