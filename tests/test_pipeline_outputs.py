"""Fresh-clone regression tests for checked-in pipeline evidence."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_REPORT = PROJECT_ROOT / "reports" / "data_quality" / "customer_churn_bronze_quality.json"


def test_quality_report_has_no_failed_critical_checks():
    report = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))

    assert report["dataset"] == "bronze.customer_churn"
    assert report["row_count"] > 0
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
