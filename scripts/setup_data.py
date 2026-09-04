"""Safely prepare sample or public IBM churn data for the local pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

from generate_sample_data import COLUMNS


IBM_URL = (
    "https://raw.githubusercontent.com/IBM/watsonx-ai-samples/"
    "5ffbf8a1d77036dd2bcaa84aed8b1f342b174583/"
    "cpd4.5/data/customer_churn/WA_FnUseC_TelcoCustomerChurn.csv"
)
IBM_SHA256 = "3d5c233415c1b42bdea7172c73e620819f507f0a8294bc2337a1d8a8877feef0"
IBM_ROW_COUNT = 7043


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_csv(path: Path, expected_rows: int | None, synthetic: bool) -> int:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError("CSV columns do not match the expected 21-column Telco schema.")
        rows = list(reader)

    if not rows:
        raise ValueError("CSV contains no data rows.")
    if expected_rows is not None and len(rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, found {len(rows)}.")
    if synthetic and any(not row["customerID"].startswith("SYNTH-") for row in rows):
        raise ValueError("Synthetic sample contains a non-synthetic customer identifier.")
    return len(rows)


def prepare(source: str, destination: Path, force: bool) -> tuple[int, str]:
    if destination.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {destination}. Pass --force only when replacement is intended."
        )

    project_root = Path(__file__).resolve().parents[1]
    sample = project_root / "data" / "samples" / "telco_customer_churn_synthetic.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix="telco-churn-", suffix=".csv", dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)

        if source == "sample":
            shutil.copyfile(sample, temporary)
            row_count = validate_csv(temporary, expected_rows=None, synthetic=True)
            source_description = "committed fictional sample"
        else:
            request = urllib.request.Request(IBM_URL, headers={"User-Agent": "telecom-pipeline-setup/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)

            actual_hash = sha256(temporary)
            if actual_hash != IBM_SHA256:
                raise ValueError(
                    "IBM download checksum mismatch. The source may have changed; the file was not installed."
                )
            row_count = validate_csv(temporary, expected_rows=IBM_ROW_COUNT, synthetic=False)
            source_description = f"IBM public sample ({IBM_URL})"

        os.replace(temporary, destination)
        temporary = None
        return row_count, source_description
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("sample", "ibm"), default="sample")
    parser.add_argument(
        "--destination",
        type=Path,
        default=project_root / "data" / "raw" / "customer_churn" / "telco_customer_churn.csv",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        rows, source_description = prepare(args.source, args.destination.resolve(), args.force)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Installed {rows} rows from {source_description}")
    print(f"Destination: {args.destination.resolve()}")


if __name__ == "__main__":
    main()
