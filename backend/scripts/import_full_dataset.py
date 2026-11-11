from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, LargeBinary, Numeric
from sqlalchemy.engine import Engine
from sqlalchemy.types import JSON, Uuid

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

BATCH_SIZE = 1000
DEFAULT_REPORT = REPOSITORY_ROOT / "data" / "validation" / "full_dataset_import_report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the verified full synthetic JSONL export into an isolated PostgreSQL database."
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def parse_record(table: Any, record: dict[str, Any]) -> dict[str, Any]:
    expected_columns = set(table.columns.keys())
    if set(record) != expected_columns:
        missing = sorted(expected_columns - set(record))
        extra = sorted(set(record) - expected_columns)
        raise ValueError(
            f"Column mismatch for {table.name}; missing={missing}, extra={extra}"
        )
    converted: dict[str, Any] = {}
    for column in table.columns:
        value = record[column.name]
        if value is None or isinstance(column.type, JSON):
            converted[column.name] = value
        elif isinstance(column.type, Uuid):
            converted[column.name] = UUID(value)
        elif isinstance(column.type, DateTime):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if column.type.timezone and parsed.utcoffset() is None:
                raise ValueError(f"Timezone missing in {table.name}.{column.name}")
            converted[column.name] = parsed
        elif isinstance(column.type, Numeric):
            converted[column.name] = Decimal(value)
        elif isinstance(column.type, LargeBinary):
            if not isinstance(value, dict) or set(value) != {"$base64"}:
                raise ValueError(f"Invalid exported binary value in {table.name}.{column.name}")
            converted[column.name] = base64.b64decode(value["$base64"], validate=True)
        else:
            converted[column.name] = value
    return converted


def validate_export(dataset_path: Path, manifest: dict[str, Any], metadata: Any) -> None:
    expected_counts = manifest["row_counts"]
    if set(expected_counts) != set(metadata.tables):
        raise ValueError("Manifest table set does not match current SQLAlchemy metadata.")
    counts = {name: 0 for name in expected_counts}
    checksums = {name: hashlib.sha256() for name in expected_counts}
    seen_tables: set[str] = set()
    active_table: str | None = None

    with gzip.open(dataset_path, "rb") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            try:
                item = json.loads(raw_line)
                if item.get("dataset") != "synthetic":
                    raise ValueError("record dataset marker is not synthetic")
                table_name = item.get("table")
                if table_name not in metadata.tables:
                    raise ValueError(f"unknown table {table_name!r}")
                if table_name != active_table:
                    if table_name in seen_tables:
                        raise ValueError(f"table {table_name!r} appears in multiple groups")
                    seen_tables.add(table_name)
                    active_table = table_name
                    print(f"Preflight: reading {table_name} ...", flush=True)
                parse_record(metadata.tables[table_name], item["record"])
                counts[table_name] += 1
                checksums[table_name].update(raw_line)
            except Exception as exc:
                raise ValueError(f"Invalid export at line {line_number}: {exc}") from exc

    actual_checksums = {name: digest.hexdigest() for name, digest in checksums.items()}
    if counts != expected_counts:
        raise ValueError(f"Export row counts differ from manifest: {counts!r}")
    if actual_checksums != manifest.get("table_checksums"):
        raise ValueError("Per-table export checksums do not match the manifest.")
    print(f"Preflight passed: {sum(counts.values()):,} records in {len(counts)} tables.", flush=True)


def _insert_batch(connection: Any, table: Any, batch: list[dict[str, Any]]) -> None:
    if batch:
        connection.execute(table.insert(), batch)
        batch.clear()


def import_records(engine: Engine, dataset_path: Path, metadata: Any, expected_counts: dict[str, int]) -> dict[str, int]:
    imported = {name: 0 for name in expected_counts}
    active_table: str | None = None
    batch: list[dict[str, Any]] = []

    with engine.begin() as connection:
        for name, table in metadata.tables.items():
            if connection.execute(table.select().limit(1)).first() is not None:
                raise RuntimeError(
                    f"Refusing import: application table {name!r} is not empty."
                )
        with gzip.open(dataset_path, "rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                try:
                    item = json.loads(raw_line)
                    table_name = item["table"]
                    if table_name != active_table:
                        if active_table is not None:
                            _insert_batch(connection, metadata.tables[active_table], batch)
                            print(
                                f"Imported {active_table}: {imported[active_table]:,} rows",
                                flush=True,
                            )
                        active_table = table_name
                    table = metadata.tables[table_name]
                    batch.append(parse_record(table, item["record"]))
                    imported[table_name] += 1
                    if len(batch) >= BATCH_SIZE:
                        _insert_batch(connection, table, batch)
                except Exception as exc:
                    raise ValueError(f"Import failed at export line {line_number}: {exc}") from exc
        if active_table is not None:
            _insert_batch(connection, metadata.tables[active_table], batch)
            print(f"Imported {active_table}: {imported[active_table]:,} rows", flush=True)

        actual_counts = table_row_counts_from_connection(connection, metadata)
        if actual_counts != expected_counts:
            raise RuntimeError(
                f"Post-import count reconciliation failed: expected={expected_counts!r}; "
                f"actual={actual_counts!r}"
            )
    return imported


def table_row_counts_from_connection(connection: Any, metadata: Any) -> dict[str, int]:
    from sqlalchemy import func, select

    return {
        name: int(
            connection.execute(select(func.count()).select_from(table)).scalar_one()
        )
        for name, table in sorted(metadata.tables.items())
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    report: dict[str, Any] = {
        "dataset": "synthetic",
        "status": "failed",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(args.manifest),
        "dataset_file": str(args.dataset),
    }
    engine: Engine | None = None
    try:
        full_dataset_database_url(require_confirmation=True)
        manifest, source_manifest = load_and_validate_manifest(args.manifest, args.dataset)
        metadata = model_metadata()
        if set(manifest["row_counts"]) != set(metadata.tables):
            raise ValueError("Manifest table set does not match current SQLAlchemy metadata.")
        validate_export(args.dataset, manifest, metadata)

        from sqlalchemy import create_engine

        engine = create_engine(
            full_dataset_database_url(require_confirmation=True),
            pool_pre_ping=True,
            future=True,
        )
        require_migrated_schema(engine, set(metadata.tables))
        imported = import_records(engine, args.dataset, metadata, manifest["row_counts"])
        report.update(
            {
                "status": "passed",
                "seed": manifest["seed"],
                "profile": manifest["profile"],
                "generator_version": manifest["generator_version"],
                "dataset_sha256": manifest["seed_data_sha256"],
                "source_manifest_sha256": manifest["source_manifest_sha256"],
                "imported_row_counts": imported,
                "expected_row_counts": manifest["row_counts"],
                "total_imported": sum(imported.values()),
                "source_provenance": source_manifest["provenance"],
                "source_file_checksum_mismatches": source_manifest[
                    "source_file_checksum_mismatches"
                ],
            }
        )
        return_code = 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(f"Full dataset import failed: {report['error']}", file=sys.stderr)
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
