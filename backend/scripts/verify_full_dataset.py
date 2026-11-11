from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.engine import Engine, create_engine

if __package__:
    from .full_dataset_common import (
        DATASET_PATH,
        MANIFEST_PATH,
        REPOSITORY_ROOT,
        full_dataset_database_url,
        load_and_validate_manifest,
        require_migrated_schema,
        table_row_counts,
    )
    from .seed_data_common import model_metadata
else:
    from full_dataset_common import (
        DATASET_PATH,
        MANIFEST_PATH,
        REPOSITORY_ROOT,
        full_dataset_database_url,
        load_and_validate_manifest,
        require_migrated_schema,
        table_row_counts,
    )
    from seed_data_common import model_metadata

DEFAULT_REPORT = (
    REPOSITORY_ROOT / "data" / "validation" / "full_dataset_database_verification.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only count and foreign-key verification of the full dataset database."
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def foreign_key_violations(engine: Engine, metadata: Any) -> dict[str, int]:
    violations: dict[str, int] = {}
    with engine.connect() as connection:
        for table in metadata.sorted_tables:
            for constraint in table.foreign_key_constraints:
                elements = list(constraint.elements)
                parent = elements[0].column.table
                non_null = [table.c[element.parent.name].is_not(None) for element in elements]
                matches = and_(
                    *(
                        table.c[element.parent.name] == parent.c[element.column.name]
                        for element in elements
                    )
                )
                parent_exists = select(1).select_from(parent).where(matches).exists()
                count = int(
                    connection.execute(
                        select(func.count())
                        .select_from(table)
                        .where(and_(*non_null), ~parent_exists)
                    ).scalar_one()
                )
                if count:
                    violations[f"{table.name}.{constraint.name}"] = count
    return violations


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    engine: Engine | None = None
    report: dict[str, Any] = {
        "dataset": "synthetic",
        "status": "failed",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        url = full_dataset_database_url(require_confirmation=False)
        manifest, source_manifest = load_and_validate_manifest(args.manifest, args.dataset)
        metadata = model_metadata()
        engine = create_engine(url, pool_pre_ping=True, future=True)
        require_migrated_schema(engine, set(metadata.tables))

        actual = table_row_counts(engine, metadata)
        expected = manifest["row_counts"]
        counts_match = actual == expected
        fk_errors = foreign_key_violations(engine, metadata)
        checks = {
            "manifest_counts_match": counts_match,
            "foreign_key_integrity": not fk_errors,
            "source_dataset_checksum_valid": True,
            "schema_matches_migration": True,
        }
        report.update(
            {
                "status": "passed" if all(checks.values()) else "failed",
                "seed": manifest["seed"],
                "dataset_sha256": manifest["seed_data_sha256"],
                "expected_row_counts": expected,
                "actual_row_counts": actual,
                "total_expected": sum(expected.values()),
                "total_actual": sum(actual.values()),
                "checks": checks,
                "foreign_key_violations": fk_errors,
                "missing_reference_count": sum(fk_errors.values()),
                "source_file_checksum_mismatches": source_manifest[
                    "source_file_checksum_mismatches"
                ],
            }
        )
        return_code = 0 if all(checks.values()) else 1
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(f"Full dataset verification failed: {report['error']}", file=sys.stderr)
        return_code = 1
    finally:
        if engine is not None:
            engine.dispose()
        report["duration_seconds"] = round(time.perf_counter() - started, 3)
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        write_report(args.report, report)
        print(json.dumps(report, sort_keys=True, indent=2), flush=True)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
