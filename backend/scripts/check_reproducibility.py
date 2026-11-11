from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FIELDS = (
    "dataset",
    "generator_version",
    "profile",
    "seed",
    "row_counts",
    "expected_targets",
    "table_checksums",
    "seed_data_sha256",
    "ground_truth",
    "source_manifest_sha256",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two clean synthetic data generations and validation reports."
    )
    parser.add_argument("--first-manifest", type=Path, required=True)
    parser.add_argument("--second-manifest", type=Path, required=True)
    parser.add_argument("--first-validation", type=Path, required=True)
    parser.add_argument("--second-validation", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    first_manifest = load_json(args.first_manifest)
    second_manifest = load_json(args.second_manifest)
    first_validation = load_json(args.first_validation)
    second_validation = load_json(args.second_validation)

    differences = [
        field
        for field in FIELDS
        if first_manifest.get(field) != second_manifest.get(field)
    ]
    first_source = load_json(
        args.first_manifest.parent / first_manifest["source_manifest"]
    )
    second_source = load_json(
        args.second_manifest.parent / second_manifest["source_manifest"]
    )
    if first_source != second_source:
        differences.append("source_manifest")

    validation_equal = (
        first_validation.get("status") == second_validation.get("status")
        and first_validation.get("actual_row_counts")
        == second_validation.get("actual_row_counts")
        and first_validation.get("checks") == second_validation.get("checks")
    )
    if not validation_equal:
        differences.append("validation_results")

    report = {
        "dataset": "synthetic",
        "seed": first_manifest.get("seed"),
        "profiles_match": first_manifest.get("profile")
        == second_manifest.get("profile"),
        "manifests_match": not any(
            item != "validation_results" for item in differences
        ),
        "validation_results_match": validation_equal,
        "result": "passed" if not differences else "failed",
        "differences": differences,
        "compared_manifests": [
            str(args.first_manifest.resolve()),
            str(args.second_manifest.resolve()),
        ],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if not differences else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Reproducibility check failed: {exc}", file=sys.stderr)
        raise
