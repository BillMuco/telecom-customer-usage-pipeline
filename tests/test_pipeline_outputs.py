"""Fast regression tests for the checked-in pipeline evidence and outputs."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DELTA_ROOT = PROJECT_ROOT / "data" / "delta"
QUALITY_REPORT = PROJECT_ROOT / "reports" / "data_quality" / "customer_churn_bronze_quality.json"

GOLD_TABLES = {
    "gold_churn_by_contract",
    "gold_churn_by_tenure_band",
    "gold_churn_by_payment_method",
    "gold_customer_risk_summary",
    "gold_executive_kpis",
}


def test_delta_layers_exist():
    """The local Delta run must produce Bronze, Silver, and all Gold tables."""
    assert (DELTA_ROOT / "bronze" / "customer_churn" / "_delta_log").is_dir()
    assert (DELTA_ROOT / "silver" / "customer_churn" / "_delta_log").is_dir()

    gold_root = DELTA_ROOT / "gold" / "customer_churn"
    actual_tables = {path.name for path in gold_root.iterdir() if path.is_dir()}
    assert actual_tables == GOLD_TABLES
    assert all((gold_root / table / "_delta_log").is_dir() for table in GOLD_TABLES)


def test_quality_report_has_no_failed_critical_checks():
    report = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))

    assert report["dataset"] == "bronze.customer_churn"
    assert report["row_count"] == 7043
    assert report["failed_critical_count"] == 0
    assert all(
        check["status"] == "PASS"
        for check in report["checks"]
        if check["severity"] == "critical"
    )


def test_quality_report_tracks_expected_source_columns():
    report = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))

    assert report["column_count"] == 25
    required_check = next(
        check for check in report["checks"] if check["name"] == "required_columns_present"
    )
    assert required_check["status"] == "PASS"

