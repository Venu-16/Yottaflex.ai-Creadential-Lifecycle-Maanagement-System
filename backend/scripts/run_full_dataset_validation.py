from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = Path(__file__).with_name("validate_seed_data.py")
DEFAULT_MANIFEST = REPOSITORY_ROOT / "data" / "generated" / "manifest.json"
DEFAULT_GROUND_TRUTH = REPOSITORY_ROOT / "data" / "ground_truth"
DEFAULT_REPORT = (
    REPOSITORY_ROOT / "data" / "validation" / "full_dataset_validation_report.json"
)

if __package__:
    from .full_dataset_common import full_dataset_database_url
else:
    from full_dataset_common import full_dataset_database_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the existing synthetic-data validator and timestamp its report."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--ground-truth-dir", type=Path, default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = full_dataset_database_url(require_confirmation=False)
    manifest_path = args.manifest.resolve()
    ground_truth_dir = args.ground_truth_dir.resolve()
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--manifest",
            str(manifest_path),
            "--ground-truth-dir",
            str(ground_truth_dir),
            "--report",
            str(report_path),
        ],
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "SYNTHETIC_DATABASE_URL": database_url},
        check=False,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["started_at"] = started_at.isoformat()
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report["duration_seconds"] = round(time.perf_counter() - started, 3)
    report_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report.get("status", "unknown"),
                "report": str(report_path),
                "completed_at": report["completed_at"],
                "duration_seconds": report["duration_seconds"],
                "failed_checks": [
                    item["name"]
                    for item in report.get("checks", [])
                    if not item.get("passed")
                ],
            },
            sort_keys=True,
            indent=2,
        )
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
