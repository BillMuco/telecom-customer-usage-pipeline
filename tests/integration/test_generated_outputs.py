"""Integration checks that require a completed local pipeline run."""

from pathlib import Path

import pytest


pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"

GOLD_TABLES = {
    "gold_churn_by_contract",
    "gold_churn_by_payment_method",
    "gold_churn_by_tenure_band",
    "gold_customer_risk_summary",
    "gold_executive_kpis",
}


def test_delta_layers_exist():
    delta_root = DATA_ROOT / "delta"
    assert (delta_root / "bronze" / "customer_churn" / "_delta_log").is_dir()
    assert (delta_root / "silver" / "customer_churn" / "_delta_log").is_dir()

    gold_root = delta_root / "gold" / "customer_churn"
    actual_tables = {path.name for path in gold_root.iterdir() if path.is_dir()}
    assert actual_tables == GOLD_TABLES
    assert all((gold_root / table / "_delta_log").is_dir() for table in GOLD_TABLES)


def test_parquet_success_markers_exist():
    expected_markers = [
        DATA_ROOT / "bronze" / "customer_churn" / "_SUCCESS",
        DATA_ROOT / "silver" / "customer_churn" / "_SUCCESS",
        *[
            DATA_ROOT / "gold" / "customer_churn" / table / "_SUCCESS"
            for table in GOLD_TABLES
        ],
    ]
    assert all(marker.is_file() for marker in expected_markers)
