from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import sys
import time
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

if __package__:
    from .seed_data_common import (
        GENERATOR_VERSION,
        REPOSITORY_ROOT,
        SEED,
        canonical_json,
        ensure_database_empty,
        file_sha256,
        make_engine,
        model_metadata,
        reset_database,
        sha256,
        stable_id,
        to_json_value,
    )
else:
    from seed_data_common import (
        GENERATOR_VERSION,
        REPOSITORY_ROOT,
        SEED,
        canonical_json,
        ensure_database_empty,
        file_sha256,
        make_engine,
        model_metadata,
        reset_database,
        sha256,
        stable_id,
        to_json_value,
    )

UTC = timezone.utc
BASE_DATE = datetime(2025, 1, 1, tzinfo=UTC)
ISSUE_DATE = datetime(2026, 1, 1, tzinfo=UTC)
VERIFICATION_DATE = datetime(2026, 10, 1, tzinfo=UTC)
BATCH_SIZE = 1000
FIRST_NAMES = (
    "Aarav", "Aditi", "Ananya", "Arjun", "Dev", "Diya", "Ishaan", "Kabir",
    "Kavya", "Meera", "Neel", "Nisha", "Priya", "Rohan", "Sana", "Vikram",
    "Zoya", "Maya", "Ira", "Vihaan",
)
LAST_NAMES = (
    "Shah", "Patel", "Rao", "Mehta", "Nair", "Kapoor", "Iyer", "Joshi",
    "Khan", "Das", "Sen", "Malhotra", "Reddy", "Gupta", "Menon", "Verma",
    "Bose", "Kulkarni", "Sethi", "Pillai",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic credential lifecycle data."
    )
    parser.add_argument(
        "--profile",
        choices=("starter", "full"),
        default="full",
        help="Dataset size. The full profile meets original minimum volumes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "generated",
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "ground_truth",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the explicitly designated synthetic database before generation.",
    )
    return parser.parse_args()


def profile_sizes(profile: str) -> dict[str, int]:
    if profile == "full":
        return {
            "learners": 20_000,
            "courses": 1_000,
            "rules": 100,
            "issuers": 10,
            "credentials": 10_000,
            "verification_requests": 5_000,
        }
    return {
        "learners": 1_000,
        "courses": 100,
        "rules": 10,
        "issuers": 3,
        "credentials": 500,
        "verification_requests": 250,
    }


def identifier(name: str, *parts: object) -> UUID:
    return stable_id(name, *parts)


def utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def offset_days(value: datetime, days: int) -> datetime:
    return utc(value + timedelta(days=days))


def seed_keypair(issuer_index: int) -> tuple[Ed25519PrivateKey, bytes]:
    material = hashlib.sha256(
        f"credential-management-synthetic-ed25519:{SEED}:{issuer_index}".encode()
    ).digest()
    private_key = Ed25519PrivateKey.from_private_bytes(material)
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key, public_key


def normalize_row(table: Any, values: dict[str, Any]) -> dict[str, Any]:
    unknown = set(values) - set(table.columns.keys())
    if unknown:
        raise ValueError(f"Unknown columns for {table.name}: {sorted(unknown)}")
    row: dict[str, Any] = {}
    for column in table.columns:
        if column.name in values:
            row[column.name] = values[column.name]
        elif column.nullable:
            row[column.name] = None
        elif column.default is not None or column.server_default is not None:
            raise ValueError(
                f"Generator must explicitly supply defaulted column "
                f"{table.name}.{column.name} for deterministic output."
            )
        else:
            raise ValueError(f"Missing required column {table.name}.{column.name}")
    return row


class GroundTruthWriter:
    def __init__(self, csv_path: Path, json_path: Path) -> None:
        self.csv_path = csv_path
        self.json_path = json_path
        self.csv_stream = io.StringIO(newline="")
        self.csv_writer = csv.DictWriter(
            self.csv_stream,
            fieldnames=(
                "record_type",
                "record_id",
                "label",
                "expected_outcome",
                "related_id",
                "details",
            ),
            lineterminator="\n",
        )
        self.csv_writer.writeheader()
        self.json_stream = io.StringIO(newline="\n")
        self.json_stream.write(
            '{"dataset":"synthetic","seed":20261022,"record_labels":['
        )
        self.first = True
        self.count = 0

    def write(self, entry: dict[str, Any]) -> None:
        normalized = {key: to_json_value(value) for key, value in entry.items()}
        if not self.first:
            self.json_stream.write(",")
        self.json_stream.write(
            json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        self.first = False
        self.csv_writer.writerow(
            {
                **normalized,
                "details": json.dumps(
                    normalized.get("details", {}),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
            }
        )
        self.count += 1

    def close(self) -> None:
        self.json_stream.write("]}\n")
        self.json_path.write_text(self.json_stream.getvalue(), encoding="utf-8")
        self.csv_path.write_text(self.csv_stream.getvalue(), encoding="utf-8", newline="")
        self.json_stream.close()
        self.csv_stream.close()


class DatasetWriter:
    def __init__(self, path: Path, metadata: Any, connection: Any) -> None:
        self.path = path
        self.raw_stream = io.BytesIO()
        self.stream = gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=self.raw_stream,
            mtime=0,
            compresslevel=6,
        )
        self.metadata = metadata
        self.connection = connection
        self.counts: dict[str, int] = {}
        self.checksums: dict[str, str] = {}

    def emit(self, table_name: str, rows: Iterable[dict[str, Any]]) -> int:
        table = self.metadata.tables[table_name]
        batch: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        count = 0
        for values in rows:
            row = normalize_row(table, values)
            exported = {
                column.name: to_json_value(row[column.name]) for column in table.columns
            }
            line = canonical_json(
                {"dataset": "synthetic", "table": table_name, "record": exported}
            ) + b"\n"
            self.stream.write(line)
            digest.update(line)
            batch.append(row)
            count += 1
            if len(batch) >= BATCH_SIZE:
                self.connection.execute(table.insert(), batch)
                batch.clear()
        if batch:
            self.connection.execute(table.insert(), batch)
        self.counts[table_name] = count
        self.checksums[table_name] = digest.hexdigest()
        return count

    def close(self) -> None:
        self.stream.close()
        self.path.write_bytes(self.raw_stream.getvalue())
        self.raw_stream.close()


def make_learner_row(index: int, created_at: datetime) -> dict[str, Any]:
    name = f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[(index // 2) % len(LAST_NAMES)]}"
    return {
        "id": identifier("learner", index),
        "learner_id": f"LRN-{index + 1:06d}",
        "display_name": name,
        "user_id": None,
        "archived_at": None,
        "created_at": created_at,
    }


def make_course_row(index: int) -> dict[str, Any]:
    return {
        "id": identifier("course", index),
        "course_code": f"CRS-{index + 1:04d}",
        "title": f"Synthetic Course {index + 1:04d}",
        "description": "Synthetic course record for deterministic lifecycle testing.",
        "status": "active",
        "effective_from": datetime(2024, 1, 1, tzinfo=UTC),
        "effective_to": None,
        "created_at": offset_days(BASE_DATE, index % 120),
    }


def course_indices(learner_index: int, size: dict[str, int]) -> list[int]:
    target_course = learner_index % size["courses"]
    values = {((learner_index * 37 + offset * 113) % size["courses"]) for offset in range(5)}
    if learner_index < size["credentials"]:
        values.add(target_course)
    return sorted(values)


def is_credential_target(learner_index: int, course_index: int, sizes: dict[str, int]) -> bool:
    return (
        learner_index < sizes["credentials"]
        and course_index == learner_index % sizes["courses"]
    )


def completion_state(learner_index: int, course_index: int, sizes: dict[str, int]) -> str:
    if is_credential_target(learner_index, course_index, sizes):
        return "completed"
    roll = stable_id("completion-status", learner_index, course_index).int % 100
    completion_rate = 50 + (course_index % 5) * 5
    if roll < completion_rate:
        return "completed"
    if roll < completion_rate + 18:
        return "in_progress"
    return "failed"


def attempt_count_for(learner_index: int, course_index: int, sizes: dict[str, int]) -> int:
    if is_credential_target(learner_index, course_index, sizes):
        return 1
    return (
        2
        if stable_id("attempt-count", learner_index, course_index).int % 100 < 28
        else 1
    )


def evaluated_at_for(
    learner_index: int, course_index: int, sizes: dict[str, int]
) -> datetime:
    if is_credential_target(learner_index, course_index, sizes):
        return (
            ISSUE_DATE
            + timedelta(days=(learner_index * 13) % 179)
            - timedelta(hours=1)
        )
    return ISSUE_DATE + timedelta(days=(learner_index + course_index) % 179)


def score_for_attempt(
    learner_index: int,
    course_index: int,
    attempt_number: int,
    sizes: dict[str, int],
) -> Decimal:
    threshold = 60 + course_index % 21
    if is_credential_target(learner_index, course_index, sizes):
        return Decimal("90.0000")
    score = stable_id(
        "assessment-score", learner_index, course_index, attempt_number
    ).int % threshold
    return Decimal(f"{score}.0000")


def make_enrollment_rows(
    sizes: dict[str, int]
) -> Iterable[dict[str, Any]]:
    for learner_index in range(sizes["learners"]):
        for course_index in course_indices(learner_index, sizes):
            status = (
                "completed"
                if completion_state(learner_index, course_index, sizes) == "completed"
                else "active"
            )
            enrolled_at = offset_days(
                BASE_DATE, (learner_index * 7 + course_index * 3) % 300
            )
            yield {
                "id": identifier("enrollment", learner_index, course_index),
                "learner_id": identifier("learner", learner_index),
                "course_id": identifier("course", course_index),
                "status": status,
                "enrolled_at": enrolled_at,
                "effective_from": enrolled_at,
                "effective_to": None,
                "recorded_by_user_id": None,
                "created_at": enrolled_at,
            }


def make_completion_rows(
    sizes: dict[str, int]
) -> Iterable[dict[str, Any]]:
    for learner_index in range(sizes["learners"]):
        for course_index in course_indices(learner_index, sizes):
            status = completion_state(learner_index, course_index, sizes)
            enrollment_at = offset_days(
                BASE_DATE, (learner_index * 7 + course_index * 3) % 300
            )
            if status == "completed":
                completed_at = enrollment_at + timedelta(days=10)
            else:
                completed_at = None
            yield {
                "id": identifier("completion", learner_index, course_index),
                "learner_id": identifier("learner", learner_index),
                "course_id": identifier("course", course_index),
                "enrollment_id": identifier("enrollment", learner_index, course_index),
                "status": status,
                "started_at": enrollment_at,
                "completed_at": completed_at,
                "recorded_at": enrollment_at + timedelta(days=11),
                "recorded_by_user_id": None,
                "source_reference": f"synthetic:completion:{learner_index}:{course_index}",
            }


def make_attempt_rows(
    sizes: dict[str, int]
) -> Iterable[dict[str, Any]]:
    for learner_index in range(sizes["learners"]):
        for course_index in course_indices(learner_index, sizes):
            completion_status = completion_state(learner_index, course_index, sizes)
            attempt_count = attempt_count_for(learner_index, course_index, sizes)
            enrollment_at = offset_days(
                BASE_DATE, (learner_index * 7 + course_index * 3) % 300
            )
            for attempt_number in range(1, attempt_count + 1):
                submitted_at = enrollment_at + timedelta(days=attempt_number)
                if completion_status == "in_progress":
                    status = "submitted"
                    score = None
                    result_code = "PENDING"
                    graded_at = None
                else:
                    status = "graded"
                    score = score_for_attempt(
                        learner_index, course_index, attempt_number, sizes
                    )
                    threshold = 60 + course_index % 21
                    result_code = "PASS" if score >= threshold else "FAIL"
                    graded_at = submitted_at + timedelta(hours=12)
                yield {
                    "id": identifier(
                        "attempt", learner_index, course_index, attempt_number
                    ),
                    "completion_record_id": identifier(
                        "completion", learner_index, course_index
                    ),
                    "learner_id": identifier("learner", learner_index),
                    "assessment_key": "FINAL",
                    "attempt_number": attempt_number,
                    "score": score,
                    "score_scale": "0-100" if score is not None else None,
                    "result_code": result_code,
                    "status": status,
                    "submitted_at": submitted_at,
                    "graded_at": graded_at,
                    "recorded_at": submitted_at + timedelta(hours=13),
                    "recorded_by_user_id": None,
                    "supersedes_attempt_id": None,
                }


def make_decisions(
    sizes: dict[str, int],
    ground_truth: GroundTruthWriter,
) -> Iterable[dict[str, Any]]:
    for learner_index in range(sizes["learners"]):
        for course_index in course_indices(learner_index, sizes):
            completion_id = identifier("completion", learner_index, course_index)
            attempt_count = attempt_count_for(learner_index, course_index, sizes)
            state = completion_state(learner_index, course_index, sizes)
            selected_attempt_id = (
                identifier("attempt", learner_index, course_index, attempt_count)
                if state != "in_progress"
                else None
            )
            enrollment_at = offset_days(
                BASE_DATE, (learner_index * 7 + course_index * 3) % 300
            )
            completed = state == "completed"
            if completed:
                completion_status = state
                completed_at = enrollment_at + timedelta(days=10)
            else:
                completion_status = state
                completed_at = None
            threshold = 60 + course_index % 21
            score = (
                score_for_attempt(
                    learner_index, course_index, attempt_count, sizes
                )
                if selected_attempt_id is not None
                else None
            )
            meets_rule = (
                completed
                and score is not None
                and score >= threshold
            )
            outcome = "eligible" if meets_rule else "ineligible"
            policy = "latest_graded"
            evaluated_at = evaluated_at_for(learner_index, course_index, sizes)
            version_id = identifier("rule-version", course_index)
            scope_id = identifier("credential-scope", course_index)
            learner_id = identifier("learner", learner_index)
            snapshot = {
                "synthetic": True,
                "learner_id": str(learner_id),
                "completion": {
                    "id": str(completion_id),
                    "status": completion_status,
                    "completed_at": completed_at.isoformat() if completed_at else None,
                },
                "assessment": {
                    "selected_attempt_id": (
                        str(selected_attempt_id) if selected_attempt_id else None
                    ),
                    "score": str(score) if score is not None else None,
                    "score_scale": "0-100",
                    "attempt_selection_policy": policy,
                },
                "rule": {
                    "version_id": str(version_id),
                    "credential_scope_id": str(scope_id),
                    "minimum_score": threshold,
                    "requires_completion": True,
                },
            }
            encoded = canonical_json(snapshot)
            decision_id = identifier("decision", learner_index, course_index)
            reason_code = (
                "REQUIREMENTS_MET"
                if meets_rule
                else "COURSE_INCOMPLETE"
                if not completed
                else "ASSESSMENT_BELOW_THRESHOLD"
            )
            ground_truth.write(
                {
                    "record_type": "eligibility_decision",
                    "record_id": str(decision_id),
                    "label": "normal_eligible" if meets_rule else "normal_ineligible",
                    "expected_outcome": outcome,
                    "related_id": str(identifier("credential", learner_index))
                    if meets_rule
                    else "",
                    "details": {
                        "learner_id": str(learner_id),
                        "course_id": str(identifier("course", course_index)),
                        "reason_code": reason_code,
                    },
                }
            )
            yield {
                "id": decision_id,
                "learner_id": learner_id,
                "rule_version_id": version_id,
                "credential_scope_id": scope_id,
                "evaluated_at": evaluated_at,
                "outcome": outcome,
                "evaluator_type": "service",
                "evaluator_user_id": None,
                "evaluator_reference": "synthetic-seed-generator",
                "evaluator_version": "synthetic-rules-v1",
                "attempt_selection_policy": policy,
                "evidence_snapshot": snapshot,
                "input_snapshot_digest": sha256(encoded),
                "supersedes_decision_id": None,
            }


def make_evidence_and_reason_rows(
    sizes: dict[str, int], ground_truth: GroundTruthWriter
) -> tuple[Iterable[dict[str, Any]], Iterable[dict[str, Any]]]:
    def evidence_rows() -> Iterable[dict[str, Any]]:
        for learner_index in range(sizes["learners"]):
            for course_index in course_indices(learner_index, sizes):
                attempt_count = attempt_count_for(learner_index, course_index, sizes)
                learner_id = identifier("learner", learner_index)
                decision_id = identifier("decision", learner_index, course_index)
                completion_id = identifier("completion", learner_index, course_index)
                course_id = identifier("course", course_index)
                state = completion_state(learner_index, course_index, sizes)
                completed = state == "completed"
                enrollment_at = offset_days(
                    BASE_DATE, (learner_index * 7 + course_index * 3) % 300
                )
                completion_snapshot = {
                    "id": str(completion_id),
                    "course_id": str(course_id),
                    "status": state,
                    "completed_at": (
                        (enrollment_at + timedelta(days=10)).isoformat() if completed else None
                    ),
                }
                completion_bytes = canonical_json(completion_snapshot)
                yield {
                    "id": identifier("evidence-completion", learner_index, course_index),
                    "eligibility_decision_id": decision_id,
                    "learner_id": learner_id,
                    "completion_record_id": completion_id,
                    "assessment_attempt_id": None,
                    "selection_role": "completion",
                    "evidence_snapshot": completion_snapshot,
                    "evidence_digest": sha256(completion_bytes),
                    "captured_at": evaluated_at_for(
                        learner_index, course_index, sizes
                    ),
                }
                if state == "in_progress":
                    continue
                attempt_id = identifier("attempt", learner_index, course_index, attempt_count)
                score = score_for_attempt(
                    learner_index, course_index, attempt_count, sizes
                )
                attempt_snapshot = {
                    "id": str(attempt_id),
                    "attempt_number": attempt_count,
                    "score": str(score),
                    "score_scale": "0-100",
                    "selection_policy": "latest_graded",
                }
                attempt_bytes = canonical_json(attempt_snapshot)
                yield {
                    "id": identifier("evidence-attempt", learner_index, course_index),
                    "eligibility_decision_id": decision_id,
                    "learner_id": learner_id,
                    "completion_record_id": None,
                    "assessment_attempt_id": attempt_id,
                    "selection_role": "selected_attempt",
                    "evidence_snapshot": attempt_snapshot,
                    "evidence_digest": sha256(attempt_bytes),
                    "captured_at": evaluated_at_for(
                        learner_index, course_index, sizes
                    ),
                }

    def reason_rows() -> Iterable[dict[str, Any]]:
        for learner_index in range(sizes["learners"]):
            for course_index in course_indices(learner_index, sizes):
                target = is_credential_target(learner_index, course_index, sizes)
                reason_code = "REQUIREMENTS_MET" if target else "ASSESSMENT_BELOW_THRESHOLD"
                if not target:
                    if completion_state(learner_index, course_index, sizes) != "completed":
                        reason_code = "COURSE_INCOMPLETE"
                decision_id = identifier("decision", learner_index, course_index)
                eligible = target
                ground_truth.write(
                    {
                        "record_type": "eligibility_reason",
                        "record_id": str(identifier("reason", learner_index, course_index)),
                        "label": "normal_eligible_reason" if eligible else "normal_ineligible_reason",
                        "expected_outcome": reason_code,
                        "related_id": str(decision_id),
                        "details": {},
                    }
                )
                yield {
                    "id": identifier("reason", learner_index, course_index),
                    "eligibility_decision_id": decision_id,
                    "reason_code": reason_code,
                    "message": "Synthetic rule evaluation result.",
                    "details": {"synthetic": True},
                    "created_at": evaluated_at_for(
                        learner_index, course_index, sizes
                    ),
                }

    return evidence_rows(), reason_rows()


def make_anomaly_fixtures(
    credential: dict[str, Any],
    revoked_credential: dict[str, Any],
    public_key: bytes,
    ineligible_decision_id: UUID,
) -> list[dict[str, Any]]:
    payload = credential["canonical_payload"]
    altered_payload = bytearray(payload)
    altered_payload[-2] = ord("X") if altered_payload[-2] != ord("X") else ord("Y")
    invalid_signature = bytearray(credential["signature"])
    invalid_signature[0] ^= 0x01
    completion_at = datetime.fromisoformat(
        credential["payload"]["completion"]["completed_at"]
    )
    return [
        {
            "scenario": "ineligible_issuance_attempt",
            "synthetic": True,
            "baseline_record_id": str(ineligible_decision_id),
            "candidate": {
                "decision_id": str(ineligible_decision_id),
                "decision_outcome": "ineligible",
                "proposed_credential_id": "CRD-2026-999999",
            },
            "expected_detection": "issuance requires an eligible decision",
            "production_database_write": False,
        },
        {
            "scenario": "credential_issued_before_completion",
            "synthetic": True,
            "baseline_record_id": str(credential["id"]),
            "candidate": {
                "credential_id": credential["credential_id"],
                "completed_at": completion_at.isoformat(),
                "issued_at": (completion_at - timedelta(days=1)).isoformat(),
            },
            "expected_detection": "issued_at precedes completed_at",
            "production_database_write": False,
        },
        {
            "scenario": "duplicate_credential_id_attempt",
            "synthetic": True,
            "baseline_record_id": str(credential["id"]),
            "candidate": {
                "credential_id": credential["credential_id"],
                "candidate_internal_id": str(identifier("anomaly-duplicate-credential")),
            },
            "expected_detection": "unique credential_id constraint collision",
            "production_database_write": False,
        },
        {
            "scenario": "revoked_credential_verifies_as_active",
            "synthetic": True,
            "baseline_record_id": str(revoked_credential["id"]),
            "candidate": {
                "credential_id": revoked_credential["credential_id"],
                "effective_at": revoked_credential["effective_at"].isoformat(),
                "requested_at": VERIFICATION_DATE.isoformat(),
                "faulty_lifecycle_result": "active",
            },
            "expected_detection": "expected lifecycle is revoked",
            "production_database_write": False,
        },
        {
            "scenario": "altered_payload_hash_not_detected",
            "synthetic": True,
            "baseline_record_id": str(credential["id"]),
            "candidate": {
                "payload_base64": base64.b64encode(bytes(altered_payload)).decode("ascii"),
                "stored_sha256_base64": base64.b64encode(credential["sha256_digest"]).decode(
                    "ascii"
                ),
                "faulty_integrity_result": "valid",
            },
            "expected_detection": "SHA-256 of altered payload differs from stored digest",
            "production_database_write": False,
        },
        {
            "scenario": "invalid_signature",
            "synthetic": True,
            "baseline_record_id": str(credential["id"]),
            "candidate": {
                "payload_base64": base64.b64encode(payload).decode("ascii"),
                "signature_base64": base64.b64encode(bytes(invalid_signature)).decode("ascii"),
                "public_key_base64": base64.b64encode(public_key).decode("ascii"),
            },
            "expected_detection": "Ed25519 verification rejects the mutated signature",
            "production_database_write": False,
        },
    ]


def verify_anomaly_fixtures(fixtures: list[dict[str, Any]]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    by_name = {fixture["scenario"]: fixture for fixture in fixtures}
    ineligible = by_name["ineligible_issuance_attempt"]["candidate"]
    results["ineligible_issuance_attempt"] = (
        ineligible["decision_outcome"] != "eligible"
    )
    issued = by_name["credential_issued_before_completion"]["candidate"]
    results["credential_issued_before_completion"] = (
        datetime.fromisoformat(issued["issued_at"])
        < datetime.fromisoformat(issued["completed_at"])
    )
    duplicate = by_name["duplicate_credential_id_attempt"]["candidate"]
    results["duplicate_credential_id_attempt"] = bool(duplicate["credential_id"])
    revoked = by_name["revoked_credential_verifies_as_active"]["candidate"]
    results["revoked_credential_verifies_as_active"] = (
        datetime.fromisoformat(revoked["effective_at"])
        <= datetime.fromisoformat(revoked["requested_at"])
        and revoked["faulty_lifecycle_result"] == "active"
    )
    altered = by_name["altered_payload_hash_not_detected"]["candidate"]
    results["altered_payload_hash_not_detected"] = (
        hashlib.sha256(base64.b64decode(altered["payload_base64"])).digest()
        != base64.b64decode(altered["stored_sha256_base64"])
        and altered["faulty_integrity_result"] == "valid"
    )
    invalid = by_name["invalid_signature"]["candidate"]
    public_key_bytes = base64.b64decode(invalid["public_key_base64"])
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(
            base64.b64decode(invalid["signature_base64"]),
            base64.b64decode(invalid["payload_base64"]),
        )
    except InvalidSignature:
        results["invalid_signature"] = True
    else:
        results["invalid_signature"] = False
    return results


def build_source_manifest() -> dict[str, Any]:
    source_files = (
        REPOSITORY_ROOT / "backend" / "scripts" / "generate_seed_data.py",
        REPOSITORY_ROOT / "backend" / "scripts" / "seed_data_common.py",
        REPOSITORY_ROOT / "backend" / "scripts" / "validate_seed_data.py",
        REPOSITORY_ROOT / "backend" / "scripts" / "check_reproducibility.py",
        REPOSITORY_ROOT / "backend" / "app" / "models" / "domain.py",
        REPOSITORY_ROOT
        / "backend"
        / "migrations"
        / "versions"
        / "af6e5dad6637_create_credential_domain_schema.py",
        REPOSITORY_ROOT / "docs" / "original-problem-statement.md",
    )
    return {
        "dataset": "synthetic",
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "external_datasets": [],
        "source_files": {
            str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): file_sha256(path)
            for path in source_files
            if path.exists()
        },
        "provenance": "Generated by this repository; no external data sources used.",
    }


def main() -> int:
    started = time.perf_counter()
    args = parse_args()
    sizes = profile_sizes(args.profile)
    args.output_dir = args.output_dir.resolve()
    args.ground_truth_dir = args.ground_truth_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.ground_truth_dir.mkdir(parents=True, exist_ok=True)

    engine = make_engine()
    try:
        if args.reset:
            reset_database(engine)
        ensure_database_empty(engine)
        with tempfile.TemporaryDirectory(
            prefix=".seed-data-stage-",
            dir=str(args.output_dir.parent),
        ) as temp_name:
            stage_root = Path(temp_name)
            staged_generated = stage_root / "generated"
            staged_ground_truth = stage_root / "ground_truth"
            staged_generated.mkdir()
            staged_ground_truth.mkdir()
            metadata = model_metadata()
            dataset = DatasetWriter(
                staged_generated / "seed_data.jsonl.gz",
                metadata,
                None,
            )
            ground_truth = GroundTruthWriter(
                staged_ground_truth / "ground_truth.csv",
                staged_ground_truth / "ground_truth.json",
            )
            counts: dict[str, int] = {}
            table_checksums: dict[str, str] = {}
            keys: dict[int, tuple[Ed25519PrivateKey, bytes]] = {}
            issuer_change_dates: dict[int, datetime] = {}
            issuer_names: dict[int, tuple[str, str]] = {}
            first_credential: dict[str, Any] | None = None
            first_revocation: dict[str, Any] | None = None

            with engine.begin() as connection:
                dataset.connection = connection
                empty_tables = (
                    "users",
                    "roles",
                    "user_roles",
                    "idempotency_records",
                )
                for table_name in empty_tables:
                    counts[table_name] = dataset.emit(table_name, ())
                    table_checksums[table_name] = dataset.checksums[table_name]

                for table_name, rows in (
                    (
                        "courses",
                        (
                            make_course_row(index)
                            for index in range(sizes["courses"])
                        ),
                    ),
                    (
                        "credential_rules",
                        (
                            {
                                "id": identifier("credential-rule", index),
                                "rule_code": f"RULE-{index + 1:04d}",
                                "name": f"Synthetic eligibility rule {index + 1:04d}",
                                "description": "Synthetic, versioned course completion rule.",
                                "archived_at": None,
                                "created_at": offset_days(BASE_DATE, index % 60),
                            }
                            for index in range(sizes["rules"])
                        ),
                    ),
                    (
                        "issuers",
                        (
                            {
                                "id": identifier("issuer", index),
                                "issuer_code": f"ISS-{index + 1:03d}",
                                "name": f"Synthetic Issuer {index + 1:03d}"
                                + (
                                    " Global Institute"
                                    if index % 2 == 0
                                    else " Academy"
                                ),
                                "status": "active",
                                "archived_at": None,
                                "created_at": BASE_DATE,
                            }
                            for index in range(sizes["issuers"])
                        ),
                    ),
                    (
                        "learners",
                        (
                            make_learner_row(index, BASE_DATE)
                            for index in range(sizes["learners"])
                        ),
                    ),
                ):
                    counts[table_name] = dataset.emit(table_name, rows)
                    table_checksums[table_name] = dataset.checksums[table_name]

                counts["credential_scopes"] = dataset.emit(
                    "credential_scopes",
                    (
                        {
                            "id": identifier("credential-scope", index),
                            "course_id": identifier("course", index),
                            "created_at": BASE_DATE,
                        }
                        for index in range(sizes["courses"])
                    ),
                )
                table_checksums["credential_scopes"] = dataset.checksums[
                    "credential_scopes"
                ]

                for issuer_index in range(sizes["issuers"]):
                    keys[issuer_index] = seed_keypair(issuer_index)
                    if issuer_index % 2 == 0:
                        issuer_change_dates[issuer_index] = ISSUE_DATE + timedelta(
                            days=90 + issuer_index
                        )
                    old_name = f"Synthetic Issuer {issuer_index + 1:03d}" + (
                        " Institute" if issuer_index % 2 == 0 else " Academy"
                    )
                    new_name = (
                        f"Synthetic Issuer {issuer_index + 1:03d} "
                        + (
                            "Global Institute"
                            if issuer_index % 2 == 0
                            else "Academy"
                        )
                    )
                    issuer_names[issuer_index] = (old_name, new_name)

                counts["issuer_signing_keys"] = dataset.emit(
                    "issuer_signing_keys",
                    (
                        {
                            "id": identifier("issuer-key", index),
                            "issuer_id": identifier("issuer", index),
                            "key_id": f"synthetic-ed25519-{index + 1:03d}",
                            "public_key": keys[index][1],
                            "fingerprint": sha256(keys[index][1]),
                            "algorithm": "Ed25519",
                            "key_purpose": "credential_signing",
                            "valid_from": datetime(2025, 1, 1, tzinfo=UTC),
                            "valid_until": None,
                            "status": "active",
                            "supersedes_key_id": None,
                            "registered_by_user_id": None,
                            "approved_by_user_id": None,
                            "registered_at": BASE_DATE,
                            "revoked_at": None,
                        }
                        for index in range(sizes["issuers"])
                    ),
                )
                table_checksums["issuer_signing_keys"] = dataset.checksums[
                    "issuer_signing_keys"
                ]

                counts["credential_rule_versions"] = dataset.emit(
                    "credential_rule_versions",
                    (
                        {
                            "id": identifier("rule-version", course_index),
                            "rule_id": identifier(
                                "credential-rule",
                                course_index % sizes["rules"],
                            ),
                            "version_number": course_index // sizes["rules"] + 1,
                            "credential_scope_id": identifier(
                                "credential-scope", course_index
                            ),
                            "criteria": {
                                "requires_completion": True,
                                "minimum_score": 60 + course_index % 21,
                                "score_scale": "0-100",
                                "attempt_selection_policy": "latest_graded",
                            },
                            "attempt_selection_policy": "latest_graded",
                            "effective_from": datetime(2025, 1, 1, tzinfo=UTC),
                            "effective_to": None,
                            "status": "active",
                            "created_by_user_id": None,
                            "created_at": BASE_DATE,
                        }
                        for course_index in range(sizes["courses"])
                    ),
                )
                table_checksums["credential_rule_versions"] = dataset.checksums[
                    "credential_rule_versions"
                ]
                counts["rule_courses"] = dataset.emit(
                    "rule_courses",
                    (
                        {
                            "rule_version_id": identifier(
                                "rule-version", course_index
                            ),
                            "course_id": identifier("course", course_index),
                            "created_at": BASE_DATE,
                        }
                        for course_index in range(sizes["courses"])
                    ),
                )
                table_checksums["rule_courses"] = dataset.checksums["rule_courses"]

                counts["enrollments"] = dataset.emit(
                    "enrollments", make_enrollment_rows(sizes)
                )
                table_checksums["enrollments"] = dataset.checksums["enrollments"]

                counts["completion_records"] = dataset.emit(
                    "completion_records",
                    make_completion_rows(sizes),
                )
                table_checksums["completion_records"] = dataset.checksums[
                    "completion_records"
                ]

                counts["assessment_attempts"] = dataset.emit(
                    "assessment_attempts",
                    make_attempt_rows(sizes),
                )
                table_checksums["assessment_attempts"] = dataset.checksums[
                    "assessment_attempts"
                ]

                counts["eligibility_decisions"] = dataset.emit(
                    "eligibility_decisions",
                    make_decisions(sizes, ground_truth),
                )
                table_checksums["eligibility_decisions"] = dataset.checksums[
                    "eligibility_decisions"
                ]
                evidence_rows, reason_rows = make_evidence_and_reason_rows(
                    sizes, ground_truth
                )
                counts["eligibility_reasons"] = dataset.emit(
                    "eligibility_reasons", reason_rows
                )
                table_checksums["eligibility_reasons"] = dataset.checksums[
                    "eligibility_reasons"
                ]
                counts["eligibility_evidence"] = dataset.emit(
                    "eligibility_evidence", evidence_rows
                )
                table_checksums["eligibility_evidence"] = dataset.checksums[
                    "eligibility_evidence"
                ]

                counts["credential_awards"] = dataset.emit(
                    "credential_awards",
                    (
                        {
                            "id": identifier("award", index),
                            "learner_id": identifier("learner", index),
                            "credential_scope_id": identifier(
                                "credential-scope", index % sizes["courses"]
                            ),
                            "created_at": ISSUE_DATE,
                        }
                        for index in range(sizes["credentials"])
                    ),
                )
                table_checksums["credential_awards"] = dataset.checksums[
                    "credential_awards"
                ]

                credential_digests: dict[int, bytes] = {}

                def credential_rows() -> Iterable[dict[str, Any]]:
                    nonlocal first_credential
                    for index in range(sizes["credentials"]):
                        learner_index = index
                        course_index = index % sizes["courses"]
                        issuer_index = index % sizes["issuers"]
                        issue_time = ISSUE_DATE + timedelta(days=(index * 13) % 179)
                        old_name, new_name = issuer_names[issuer_index]
                        change_time = issuer_change_dates.get(issuer_index)
                        issuer_name = (
                            old_name
                            if change_time is not None and issue_time < change_time
                            else new_name
                        )
                        payload = {
                            "credential_id": f"CRD-2026-{index + 1:06d}",
                            "synthetic": True,
                            "learner_id": f"LRN-{learner_index + 1:06d}",
                            "course_code": f"CRS-{course_index + 1:04d}",
                            "issuer": {
                                "issuer_code": f"ISS-{issuer_index + 1:03d}",
                                "issuer_name": issuer_name,
                            },
                            "rule_version": str(identifier("rule-version", course_index)),
                            "completion": {
                                "completed_at": (
                                    offset_days(
                                        BASE_DATE,
                                        (
                                            learner_index * 7
                                            + course_index * 3
                                        )
                                        % 300
                                        + 10,
                                    ).isoformat()
                                ),
                                "score": "90.0000",
                            },
                            "issued_at": issue_time.isoformat(),
                            "payload_version": "credential-v1",
                        }
                        payload_bytes = canonical_json(payload)
                        digest = sha256(payload_bytes)
                        credential_digests[index] = digest
                        private_key = keys[issuer_index][0]
                        signature = private_key.sign(payload_bytes)
                        row = {
                            "id": identifier("credential", index),
                            "credential_id": payload["credential_id"],
                            "award_id": identifier("award", learner_index),
                            "learner_id": identifier("learner", learner_index),
                            "credential_scope_id": identifier(
                                "credential-scope", course_index
                            ),
                            "issuer_id": identifier("issuer", issuer_index),
                            "rule_version_id": identifier(
                                "rule-version", course_index
                            ),
                            "eligibility_decision_id": identifier(
                                "decision", learner_index, course_index
                            ),
                            "replacement_of_credential_id": None,
                            "issued_at": issue_time,
                            "payload_version": "credential-v1",
                            "canonical_payload": payload_bytes,
                            "sha256_digest": digest,
                            "signature": signature,
                            "signature_algorithm": "Ed25519",
                            "signing_key_id": identifier("issuer-key", issuer_index),
                        }
                        ground_truth.write(
                            {
                                "record_type": "credential",
                                "record_id": payload["credential_id"],
                                "label": "normal_credential",
                                "expected_outcome": "authentic",
                                "related_id": str(row["eligibility_decision_id"]),
                                "details": {
                                    "synthetic": True,
                                    "issued_at": issue_time.isoformat(),
                                },
                            }
                        )
                        if index == 0:
                            first_credential = {
                                **row,
                                "payload": payload,
                            }
                        yield row

                counts["credentials"] = dataset.emit("credentials", credential_rows())
                table_checksums["credentials"] = dataset.checksums["credentials"]

                def revocation_rows() -> Iterable[dict[str, Any]]:
                    nonlocal first_revocation
                    for index in range(0, sizes["credentials"], 20):
                        issue_time = ISSUE_DATE + timedelta(days=(index * 13) % 179)
                        effective_at = issue_time + timedelta(days=60)
                        row = {
                            "id": identifier("revocation", index),
                            "credential_id": identifier("credential", index),
                            "reason_code": "SYNTHETIC_QUALITY_REVIEW",
                            "reason_detail": "Synthetic terminal revocation fixture.",
                            "recorded_by_user_id": None,
                            "actor_reference": "synthetic-seed-generator",
                            "effective_at": effective_at,
                            "recorded_at": effective_at + timedelta(minutes=5),
                            "correlation_id": identifier("revocation-correlation", index),
                        }
                        if first_revocation is None:
                            first_revocation = {
                                "id": identifier("credential", index),
                                "credential_id": f"CRD-2026-{index + 1:06d}",
                                "effective_at": effective_at,
                            }
                        ground_truth.write(
                            {
                                "record_type": "revoked_credential",
                                "record_id": f"CRD-2026-{index + 1:06d}",
                                "label": "normal_revoked_credential",
                                "expected_outcome": "revoked",
                                "related_id": str(row["id"]),
                                "details": {
                                    "effective_at": effective_at.isoformat()
                                },
                            }
                        )
                        yield row

                counts["revocations"] = dataset.emit("revocations", revocation_rows())
                table_checksums["revocations"] = dataset.checksums["revocations"]

                def verification_rows() -> Iterable[dict[str, Any]]:
                    for index in range(sizes["verification_requests"]):
                        credential_index = (index * 37) % sizes["credentials"]
                        issuer_index = credential_index % sizes["issuers"]
                        revoked = credential_index % 20 == 0
                        mode = "credential_id" if index % 2 == 0 else "portable_payload"
                        request_time = VERIFICATION_DATE + timedelta(seconds=index)
                        lifecycle = "revoked" if revoked else "active"
                        overall = "revoked" if revoked else "valid"
                        verification_id = f"VER-2026-{index + 1:06d}"
                        ground_truth.write(
                            {
                                "record_type": "verification_request",
                                "record_id": verification_id,
                                "label": (
                                    "normal_verification_revoked"
                                    if revoked
                                    else "normal_verification_active"
                                ),
                                "expected_outcome": overall,
                                "related_id": f"CRD-2026-{credential_index + 1:06d}",
                                "details": {
                                    "mode": mode,
                                    "integrity": "valid",
                                    "issuer_trust": "trusted",
                                    "lifecycle": lifecycle,
                                },
                            }
                        )
                        yield {
                            "id": identifier("verification", index),
                            "verification_id": verification_id,
                            "mode": mode,
                            "submitted_credential_id": (
                                f"CRD-2026-{credential_index + 1:06d}"
                                if mode == "credential_id"
                                else None
                            ),
                            "credential_id_fk": identifier(
                                "credential", credential_index
                            ),
                            "resolved_issuer_id": identifier("issuer", issuer_index),
                            "resolved_signing_key_id": identifier(
                                "issuer-key", issuer_index
                            ),
                            "input_digest": (
                                credential_digests[credential_index]
                                if mode == "portable_payload"
                                else None
                            ),
                            "integrity_result": "valid",
                            "issuer_trust_result": "trusted",
                            "lifecycle_result": lifecycle,
                            "overall_result": overall,
                            "requester_user_id": None,
                            "requester_reference": "synthetic-third-party-verifier",
                            "requested_at": request_time,
                            "completed_at": request_time + timedelta(seconds=1),
                            "correlation_id": identifier("verification-correlation", index),
                        }

                counts["verification_requests"] = dataset.emit(
                    "verification_requests", verification_rows()
                )
                table_checksums["verification_requests"] = dataset.checksums[
                    "verification_requests"
                ]

                def audit_rows() -> Iterable[dict[str, Any]]:
                    for issuer_index, changed_at in sorted(issuer_change_dates.items()):
                        old_name, new_name = issuer_names[issuer_index]
                        yield {
                            "id": identifier("audit-issuer-profile", issuer_index),
                            "event_type": "issuer.profile_updated",
                            "outcome": "success",
                            "actor_user_id": None,
                            "actor_reference": "synthetic-seed-generator",
                            "target_type": "issuer",
                            "target_reference": f"ISS-{issuer_index + 1:03d}",
                            "occurred_at": changed_at,
                            "correlation_id": identifier("issuer-change-correlation", issuer_index),
                            "reason_code": "SYNTHETIC_PROFILE_CHANGE",
                            "event_data": {
                                "synthetic": True,
                                "before": {"name": old_name},
                                "after": {"name": new_name},
                            },
                        }
                    for index in range(sizes["credentials"]):
                        issue_time = ISSUE_DATE + timedelta(days=(index * 13) % 179)
                        yield {
                            "id": identifier("audit-credential-issued", index),
                            "event_type": "credential.issued",
                            "outcome": "success",
                            "actor_user_id": None,
                            "actor_reference": "synthetic-seed-generator",
                            "target_type": "credential",
                            "target_reference": f"CRD-2026-{index + 1:06d}",
                            "occurred_at": issue_time,
                            "correlation_id": identifier("credential-correlation", index),
                            "reason_code": "ELIGIBLE",
                            "event_data": {
                                "synthetic": True,
                                "decision_id": str(
                                    identifier("decision", index, index % sizes["courses"])
                                ),
                            },
                        }
                    for index in range(0, sizes["credentials"], 20):
                        effective_at = ISSUE_DATE + timedelta(
                            days=(index * 13) % 179 + 60
                        )
                        yield {
                            "id": identifier("audit-revocation", index),
                            "event_type": "credential.revoked",
                            "outcome": "success",
                            "actor_user_id": None,
                            "actor_reference": "synthetic-seed-generator",
                            "target_type": "credential",
                            "target_reference": f"CRD-2026-{index + 1:06d}",
                            "occurred_at": effective_at + timedelta(minutes=5),
                            "correlation_id": identifier("revocation-correlation", index),
                            "reason_code": "SYNTHETIC_QUALITY_REVIEW",
                            "event_data": {"synthetic": True},
                        }

                counts["audit_events"] = dataset.emit("audit_events", audit_rows())
                table_checksums["audit_events"] = dataset.checksums["audit_events"]
            if first_credential is None or first_revocation is None:
                raise RuntimeError("The selected dataset profile must generate credentials.")
            first_ineligible_course = next(
                course_index
                for course_index in course_indices(0, sizes)
                if course_index != 0
            )
            fixtures = make_anomaly_fixtures(
                first_credential,
                first_revocation,
                keys[0][1],
                identifier("decision", 0, first_ineligible_course),
            )
            fixture_results = verify_anomaly_fixtures(fixtures)
            if not all(fixture_results.values()):
                raise RuntimeError(f"Anomaly fixture validation failed: {fixture_results}")
            fixture_path = staged_ground_truth / "anomaly_fixtures.json"
            fixture_path.write_text(
                json.dumps(
                    {
                        "dataset": "synthetic",
                        "production_database_mutated": False,
                        "fixtures": fixtures,
                        "fixture_checks": fixture_results,
                    },
                    sort_keys=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            # Fixtures are kept in ground truth and never inserted into operational tables.
            for fixture in fixtures:
                ground_truth.write(
                    {
                        "record_type": "anomaly_fixture",
                        "record_id": fixture["scenario"],
                        "label": fixture["scenario"],
                        "expected_outcome": fixture["expected_detection"],
                        "related_id": fixture["baseline_record_id"],
                        "details": fixture["candidate"],
                    }
                )
            ground_truth.close()
            dataset.close()
            gt_json = staged_ground_truth / "ground_truth.json"

            seed_data_path = staged_generated / "seed_data.jsonl.gz"
            table_checksums = dataset.checksums
            source_manifest = build_source_manifest()
            source_manifest_path = staged_generated / "source_manifest.json"
            source_manifest_path.write_text(
                json.dumps(source_manifest, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            manifest = {
                "dataset": "synthetic",
                "generator_version": GENERATOR_VERSION,
                "profile": args.profile,
                "seed": SEED,
                "row_counts": counts,
                "expected_targets": {
                    "learners": sizes["learners"],
                    "courses": sizes["courses"],
                    "credential_rules": sizes["rules"],
                    "issuers": sizes["issuers"],
                    "credentials": sizes["credentials"],
                    "verification_requests": sizes["verification_requests"],
                },
                "table_checksums": table_checksums,
                "seed_data_file": "seed_data.jsonl.gz",
                "seed_data_sha256": file_sha256(seed_data_path),
                "ground_truth": {
                    "csv_sha256": file_sha256(
                        staged_ground_truth / "ground_truth.csv"
                    ),
                    "json_sha256": file_sha256(gt_json),
                    "anomaly_fixtures_sha256": file_sha256(fixture_path),
                    "labels": ground_truth.count,
                    "fixture_checks": fixture_results,
                },
                "source_manifest": "source_manifest.json",
                "source_manifest_sha256": file_sha256(source_manifest_path),
            }
            (staged_generated / "manifest.json").write_text(
                json.dumps(manifest, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            for source, target in (
                (staged_generated, args.output_dir),
                (staged_ground_truth, args.ground_truth_dir),
            ):
                target.mkdir(parents=True, exist_ok=True)
                for staged_file in source.iterdir():
                    os.replace(staged_file, target / staged_file.name)

        print(
            json.dumps(
                {
                    "profile": args.profile,
                    "seed": SEED,
                    "row_counts": counts,
                    "runtime_seconds": round(time.perf_counter() - started, 3),
                    "manifest": str(args.output_dir / "manifest.json"),
                    "ground_truth": str(args.ground_truth_dir),
                },
                sort_keys=True,
                indent=2,
            )
        )
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Seed generation failed: {exc}", file=sys.stderr)
        raise
