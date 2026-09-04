"""Tests for the redistributable synthetic dataset and setup utility."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = PROJECT_ROOT / "data" / "samples" / "telco_customer_churn_synthetic.csv"
EXPECTED_COLUMNS = [
    "customerID", "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
    "MonthlyCharges", "TotalCharges", "Churn",
]


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def test_committed_sample_is_small_and_fictional():
    columns, rows = read_rows(SAMPLE)

    assert columns == EXPECTED_COLUMNS
    assert len(rows) == 100
    assert len({row["customerID"] for row in rows}) == len(rows)
    assert all(row["customerID"].startswith("SYNTH-") for row in rows)
    assert {row["Churn"] for row in rows} <= {"Yes", "No"}


def test_generator_is_deterministic(tmp_path: Path):
    generated = tmp_path / "generated.csv"
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "generate_sample_data.py"),
            "--output", str(generated), "--rows", "100", "--seed", "42",
        ],
        check=True,
    )

    assert generated.read_bytes() == SAMPLE.read_bytes()


def test_setup_installs_sample_without_silent_overwrite(tmp_path: Path):
    destination = tmp_path / "raw" / "telco_customer_churn.csv"
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "setup_data.py"),
        "--source", "sample", "--destination", str(destination),
    ]

    subprocess.run(command, check=True)
    assert destination.read_bytes() == SAMPLE.read_bytes()

    repeated = subprocess.run(command, capture_output=True, text=True)
    assert repeated.returncode != 0
    assert "Refusing to overwrite" in repeated.stderr
