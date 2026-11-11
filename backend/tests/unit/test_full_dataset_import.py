from __future__ import annotations

import gzip
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import LargeBinary, Numeric

from app.database.base import Base
import app.models
from scripts.full_dataset_common import full_dataset_database_url
from scripts.import_full_dataset import parse_record, validate_export
from scripts.seed_data_common import canonical_json


def _small_export(path: Path) -> tuple[dict[str, object], bytes]:
    table = Base.metadata.tables["learners"]
    record = {column.name: None for column in table.columns}
    record.update(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "learner_id": "LRN-000001",
            "display_name": "Test Learner",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    line = canonical_json(
        {"dataset": "synthetic", "table": "learners", "record": record}
    ) + b"\n"
    with gzip.open(path, "wb") as stream:
        stream.write(line)
    row_counts = {name: 0 for name in Base.metadata.tables}
    row_counts["learners"] = 1
    table_checksums = {
        name: hashlib.sha256().hexdigest() for name in Base.metadata.tables
    }
    table_checksums["learners"] = hashlib.sha256(line).hexdigest()
    return {
        "row_counts": row_counts,
        "table_checksums": table_checksums,
    }, line


def test_importer_restores_native_sqlalchemy_values() -> None:
    learner = Base.metadata.tables["learners"]
    record = {column.name: None for column in learner.columns}
    record.update(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "learner_id": "LRN-000001",
            "display_name": "Test Learner",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    decoded = parse_record(learner, record)
    assert decoded["id"] == UUID(record["id"])
    assert decoded["created_at"] == datetime(2026, 1, 1, tzinfo=timezone.utc)

    credential = Base.metadata.tables["credentials"]
    binary_record = {column.name: None for column in credential.columns}
    for column in credential.columns:
        if isinstance(column.type, LargeBinary):
            binary_record[column.name] = {"$base64": "AAECAw=="}
        elif column.name != "replacement_of_credential_id":
            binary_record[column.name] = "00000000-0000-0000-0000-000000000001"
    binary_record.update(
        {
            "credential_id": "CRD-2026-000001",
            "issued_at": "2026-01-01T00:00:00+00:00",
            "payload_version": "v1",
            "signature_algorithm": "Ed25519",
        }
    )
    decoded_credential = parse_record(credential, binary_record)
    assert decoded_credential["canonical_payload"] == b"\x00\x01\x02\x03"
    assert decoded_credential["sha256_digest"] == b"\x00\x01\x02\x03"
    assert decoded_credential["id"] == UUID("00000000-0000-0000-0000-000000000001")

    attempts = Base.metadata.tables["assessment_attempts"]
    numeric_column = next(
        column for column in attempts.columns if isinstance(column.type, Numeric)
    )
    attempt_record = {column.name: None for column in attempts.columns}
    attempt_record[numeric_column.name] = "76.2500"
    assert parse_record(attempts, attempt_record)[numeric_column.name] == Decimal("76.2500")


def test_export_preflight_reconciles_counts_and_checksums(tmp_path: Path) -> None:
    path = tmp_path / "small.jsonl.gz"
    manifest, _ = _small_export(path)
    validate_export(path, manifest, Base.metadata)


def test_export_preflight_rejects_count_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "small.jsonl.gz"
    manifest, _ = _small_export(path)
    manifest["row_counts"]["learners"] = 2
    with pytest.raises(ValueError, match="row counts"):
        validate_export(path, manifest, Base.metadata)


def test_import_requires_exact_disposable_database_and_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FULL_DATASET_DATABASE_URL",
        "postgresql+psycopg://user:password@127.0.0.1:55438/credential_fullscale_integration",
    )
    monkeypatch.delenv("CONFIRM_FULL_DATASET_IMPORT", raising=False)
    with pytest.raises(RuntimeError, match="CONFIRM_FULL_DATASET_IMPORT"):
        full_dataset_database_url(require_confirmation=True)
    monkeypatch.setenv("CONFIRM_FULL_DATASET_IMPORT", "YES")
    assert "credential_fullscale_integration" in full_dataset_database_url(
        require_confirmation=True
    )

    monkeypatch.setenv(
        "FULL_DATASET_DATABASE_URL",
        "postgresql+psycopg://user:password@127.0.0.1:5432/credential_management",
    )
    with pytest.raises(RuntimeError, match="Refusing database"):
        full_dataset_database_url(require_confirmation=False)
