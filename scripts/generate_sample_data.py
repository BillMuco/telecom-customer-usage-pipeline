"""Generate a deterministic, fictional Telco Customer Churn sample."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


COLUMNS = [
    "customerID", "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
    "MonthlyCharges", "TotalCharges", "Churn",
]


def build_rows(count: int, seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []

    for index in range(1, count + 1):
        tenure = rng.randint(0, 72)
        phone = rng.random() < 0.90
        internet = rng.choices(["DSL", "Fiber optic", "No"], [0.35, 0.45, 0.20])[0]
        contract = rng.choices(["Month-to-month", "One year", "Two year"], [0.55, 0.25, 0.20])[0]
        payment = rng.choice([
            "Electronic check", "Mailed check", "Bank transfer (automatic)",
            "Credit card (automatic)",
        ])

        if internet == "No":
            internet_options = {name: "No internet service" for name in (
                "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
                "StreamingTV", "StreamingMovies",
            )}
        else:
            internet_options = {
                name: rng.choice(["Yes", "No"])
                for name in (
                    "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
                    "StreamingTV", "StreamingMovies",
                )
            }

        monthly = 18.0
        if phone:
            monthly += 15.0
        if internet == "DSL":
            monthly += 25.0
        elif internet == "Fiber optic":
            monthly += 45.0
        monthly += 6.0 * sum(value == "Yes" for value in internet_options.values())
        monthly = round(monthly + rng.uniform(-2.5, 2.5), 2)

        churn_score = 0.05
        churn_score += 0.30 if contract == "Month-to-month" else -0.03
        churn_score += 0.10 if payment == "Electronic check" else 0
        churn_score += 0.08 if internet == "Fiber optic" else 0
        churn_score += 0.12 if tenure < 12 else (-0.08 if tenure >= 49 else 0)
        churn = "Yes" if rng.random() < max(0.01, min(0.80, churn_score)) else "No"

        total = "" if tenure == 0 else f"{monthly * tenure * rng.uniform(0.96, 1.04):.2f}"
        row = {
            "customerID": f"SYNTH-{index:05d}",
            "gender": rng.choice(["Female", "Male"]),
            "SeniorCitizen": rng.choice([0, 0, 0, 1]),
            "Partner": rng.choice(["Yes", "No"]),
            "Dependents": rng.choice(["Yes", "No"]),
            "tenure": tenure,
            "PhoneService": "Yes" if phone else "No",
            "MultipleLines": rng.choice(["Yes", "No"]) if phone else "No phone service",
            "InternetService": internet,
            **internet_options,
            "Contract": contract,
            "PaperlessBilling": rng.choice(["Yes", "No"]),
            "PaymentMethod": payment,
            "MonthlyCharges": f"{monthly:.2f}",
            "TotalCharges": total,
            "Churn": churn,
        }
        rows.append(row)

    return rows


def write_sample(output: Path, count: int, seed: int, force: bool) -> None:
    if count < 1:
        raise ValueError("--rows must be at least 1")
    if output.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {output}; pass --force to replace it.")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(build_rows(count, seed))


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "data" / "samples" / "telco_customer_churn_synthetic.csv",
    )
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    write_sample(args.output, args.rows, args.seed, args.force)
    print(f"Generated {args.rows} fictional rows at {args.output}")


if __name__ == "__main__":
    main()
