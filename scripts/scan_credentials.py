"""Fail when tracked repository files contain high-confidence credential patterns."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BINARY_SUFFIXES = {".crc", ".gif", ".ico", ".jpeg", ".jpg", ".parquet", ".pdf", ".png"}
PATTERNS = {
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "Databricks token": re.compile(rb"dapi[A-Za-z0-9]{20,}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Slack token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return [PROJECT_ROOT / path.decode() for path in result.stdout.split(b"\0") if path]


def main() -> int:
    findings: list[tuple[str, str]] = []
    for path in tracked_files():
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        content = path.read_bytes()
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append((str(path.relative_to(PROJECT_ROOT)), label))

    if findings:
        for path, label in findings:
            print(f"Credential pattern detected: {path} ({label})")
        return 1

    print("Credential scan passed for tracked text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
