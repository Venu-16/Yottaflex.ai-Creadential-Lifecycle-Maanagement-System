from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError

if __package__:
    from .seed_data_common import (
        REPOSITORY_ROOT,
        SEED,
        file_sha256,
        make_engine,
        model_metadata,
        stable_id,
    )
    from .generate_seed_data import verify_anomaly_fixtures
else:
    from seed_data_common import (
        REPOSITORY_ROOT,
        SEED,
        file_sha256,
        make_engine,
        model_metadata,
        stable_id,
    )
    from generate_seed_data import verify_anomaly_fixtures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate generated synthetic seed data and its separate ground truth."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "generated" / "manifest.json",
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "ground_truth",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPOSITORY_ROOT
        / "data"
        / "validation"
        / "validation_summary.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    ground_truth_dir = args.ground_truth_dir.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata = model_metadata()
    engine = make_engine()
    results: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    def check(name: str, passed: bool, details: str = "") -> None:
        results.append(
            {"name": name, "passed": bool(passed), "details": details}
        )

    try:
        with engine.connect() as connection:
            for table_name, table in sorted(metadata.tables.items()):
                count = connection.execute(
                    select(func.count()).select_from(table)
                ).scalar_one()
                counts[table_name] = int(count)
            expected_counts = manifest.get("row_counts", {})
            check(
                "row_counts_match_manifest",
                counts == expected_counts,
                f"expected table counts from manifest; actual={counts}",
            )
            target_map = {
                "learners": "learners",
                "courses": "courses",
                "credential_rules": "credential_rules",
                "issuers": "issuers",
                "credentials": "credentials",
                "verification_requests": "verification_requests",
            }
            target_checks = True
            target_messages = []
            for target_name, table_name in target_map.items():
                expected = int(manifest["expected_targets"][target_name])
                actual = counts[table_name]
                target_checks = target_checks and actual == expected
                target_messages.append(f"{table_name}={actual}/{expected}")
            check(
                "required_entity_target_counts",
                target_checks,
                ", ".join(target_messages),
            )
            eligible_decision_count = connection.execute(
                select(func.count())
                .select_from(metadata.tables["eligibility_decisions"])
                .where(metadata.tables["eligibility_decisions"].c.outcome == "eligible")
            ).scalar_one()
            revocation_target = (manifest["expected_targets"]["credentials"] + 19) // 20
            expected_profile_changes = (
                manifest["expected_targets"]["issuers"] + 1
            ) // 2
            expected_audit_events = (
                manifest["expected_targets"]["credentials"]
                + revocation_target
                + expected_profile_changes
            )
            arithmetic_ok = (
                counts["enrollments"]
                == counts["completion_records"]
                == counts["eligibility_decisions"]
                == counts["eligibility_reasons"]
                and counts["credentials"] == counts["credential_awards"]
                and counts["credentials"] == eligible_decision_count
                and counts["revocations"] == revocation_target
                and counts["audit_events"] == expected_audit_events
                and counts["assessment_attempts"] >= counts["completion_records"]
                and counts["eligibility_evidence"] >= counts["eligibility_decisions"]
            )
            check(
                "arithmetic_reconciliation",
                arithmetic_ok,
                f"eligible_decisions={eligible_decision_count}; "
                f"expected_revocations={revocation_target}; "
                f"expected_audit_events={expected_audit_events}",
            )

            pk_checks: list[str] = []
            for table in metadata.sorted_tables:
                pk_columns = list(table.primary_key.columns)
                duplicates = connection.execute(
                    select(*pk_columns)
                    .group_by(*pk_columns)
                    .having(func.count() > 1)
                    .limit(1)
                ).first()
                if duplicates is not None:
                    pk_checks.append(table.name)
            check(
                "primary_key_uniqueness",
                not pk_checks,
                "duplicate primary keys: " + (", ".join(pk_checks) or "none"),
            )

            unique_failures: list[str] = []
            for table in metadata.sorted_tables:
                unique_keys: list[tuple[str, tuple[Any, ...], Any]] = []
                for constraint in table.constraints:
                    if constraint.__class__.__name__ == "UniqueConstraint":
                        unique_keys.append(
                            (
                                constraint.name or "unique_constraint",
                                tuple(constraint.columns),
                                None,
                            )
                        )
                for index in table.indexes:
                    if index.unique:
                        predicate = index.dialect_options["postgresql"].get("where")
                        unique_keys.append(
                            (
                                index.name or "unique_index",
                                tuple(index.columns),
                                predicate,
                            )
                        )
                for key_name, columns, predicate in unique_keys:
                    query = (
                        select(*columns)
                        .where(and_(*(column.is_not(None) for column in columns)))
                        .group_by(*columns)
                        .having(func.count() > 1)
                        .limit(1)
                    )
                    if predicate is not None:
                        query = query.where(predicate)
                    if connection.execute(query).first() is not None:
                        unique_failures.append(f"{table.name}.{key_name}")
            check(
                "unique_constraints_and_indexes",
                not unique_failures,
                "duplicates: " + (", ".join(unique_failures) or "none"),
            )

            fk_failures: list[str] = []
            for table in metadata.sorted_tables:
                for constraint in table.foreign_key_constraints:
                    elements = list(constraint.elements)
                    parent_table = elements[0].column.table
                    parent = parent_table.alias(f"parent_{table.name}_{constraint.name}")
                    conditions = [
                        table.c[element.parent.name] == parent.c[element.column.name]
                        for element in elements
                    ]
                    non_null = [
                        table.c[element.parent.name].is_not(None)
                        for element in elements
                    ]
                    orphan = connection.execute(
                        select(func.count())
                        .select_from(table.outerjoin(parent, and_(*conditions)))
                        .where(
                            and_(
                                *non_null,
                                parent.c[elements[0].column.name].is_(None),
                            )
                        )
                    ).scalar_one()
                    if orphan:
                        fk_failures.append(
                            f"{table.name}.{constraint.name}={orphan}"
                        )
            check(
                "foreign_key_integrity",
                not fk_failures,
                "; ".join(fk_failures) if fk_failures else "no orphan references",
            )

            business_id_patterns = {
                "learners": ("learner_id", re.compile(r"^LRN-\d{6}$")),
                "credentials": ("credential_id", re.compile(r"^CRD-2026-\d{6}$")),
                "verification_requests": (
                    "verification_id",
                    re.compile(r"^VER-2026-\d{6}$"),
                ),
            }
            identifier_failures: list[str] = []
            for table_name, (column_name, pattern) in business_id_patterns.items():
                table = metadata.tables[table_name]
                values = connection.execute(select(table.c[column_name])).scalars()
                for value in values:
                    if not pattern.fullmatch(value):
                        identifier_failures.append(f"{table_name}:{value}")
                        break
                distinct_count = connection.execute(
                    select(func.count(func.distinct(table.c[column_name])))
                ).scalar_one()
                if distinct_count != counts[table_name]:
                    identifier_failures.append(f"{table_name}:duplicate business IDs")
            check(
                "business_identifier_formats_and_uniqueness",
                not identifier_failures,
                "; ".join(identifier_failures) if identifier_failures else "valid",
            )

            enum_specs = {
                "courses.status": ("courses", "status", {"active", "inactive", "archived"}),
                "enrollments.status": ("enrollments", "status", {"active", "completed"}),
                "completion_records.status": (
                    "completion_records",
                    "status",
                    {"completed", "in_progress", "failed"},
                ),
                "assessment_attempts.status": (
                    "assessment_attempts",
                    "status",
                    {"submitted", "graded", "void"},
                ),
                "credential_rule_versions.status": (
                    "credential_rule_versions",
                    "status",
                    {"draft", "active", "retired"},
                ),
                "eligibility_decisions.outcome": (
                    "eligibility_decisions",
                    "outcome",
                    {"eligible", "ineligible", "needs_review"},
                ),
                "issuers.status": ("issuers", "status", {"active", "inactive", "archived"}),
                "issuer_signing_keys.status": (
                    "issuer_signing_keys",
                    "status",
                    {"pending", "active", "retired", "revoked", "compromised"},
                ),
                "verification_requests.mode": (
                    "verification_requests",
                    "mode",
                    {"credential_id", "portable_payload"},
                ),
                "verification_requests.integrity_result": (
                    "verification_requests",
                    "integrity_result",
                    {"valid", "invalid", "unavailable"},
                ),
                "verification_requests.issuer_trust_result": (
                    "verification_requests",
                    "issuer_trust_result",
                    {"trusted", "untrusted", "unknown", "unavailable"},
                ),
                "verification_requests.lifecycle_result": (
                    "verification_requests",
                    "lifecycle_result",
                    {"active", "revoked", "unknown", "unavailable"},
                ),
                "verification_requests.overall_result": (
                    "verification_requests",
                    "overall_result",
                    {"valid", "invalid", "revoked", "indeterminate", "not_found"},
                ),
            }
            enum_failures: list[str] = []
            for label, (table_name, column_name, allowed) in enum_specs.items():
                table = metadata.tables[table_name]
                invalid = connection.execute(
                    select(table.c[column_name])
                    .where(~table.c[column_name].in_(allowed))
                    .limit(1)
                ).scalar_one_or_none()
                if invalid is not None:
                    enum_failures.append(f"{label}={invalid}")
            check(
                "allowed_enum_values",
                not enum_failures,
                "; ".join(enum_failures) if enum_failures else "valid",
            )

            completion = metadata.tables["completion_records"]
            invalid_completion_dates = connection.execute(
                select(func.count())
                .select_from(completion)
                .where(
                    completion.c.completed_at.is_not(None),
                    completion.c.started_at.is_not(None),
                    completion.c.completed_at < completion.c.started_at,
                )
            ).scalar_one()
            attempt = metadata.tables["assessment_attempts"]
            invalid_attempt_dates = connection.execute(
                select(func.count())
                .select_from(attempt)
                .where(
                    attempt.c.graded_at.is_not(None),
                    attempt.c.graded_at < attempt.c.submitted_at,
                )
            ).scalar_one()
            invalid_verification_dates = connection.execute(
                select(func.count())
                .select_from(metadata.tables["verification_requests"])
                .where(
                    metadata.tables["verification_requests"].c.completed_at.is_not(None),
                    metadata.tables["verification_requests"].c.completed_at
                    < metadata.tables["verification_requests"].c.requested_at,
                )
            ).scalar_one()
            check(
                "date_ordering",
                invalid_completion_dates == 0
                and invalid_attempt_dates == 0
                and invalid_verification_dates == 0,
                f"completion={invalid_completion_dates}; attempts={invalid_attempt_dates}; "
                f"verification={invalid_verification_dates}",
            )

            award = metadata.tables["credential_awards"]
            award_duplicates = connection.execute(
                select(award.c.learner_id, award.c.credential_scope_id)
                .group_by(award.c.learner_id, award.c.credential_scope_id)
                .having(func.count() > 1)
                .limit(1)
            ).first()
            check(
                "credential_award_uniqueness",
                award_duplicates is None,
                "one award slot per learner and credential scope",
            )

            credential = metadata.tables["credentials"]
            decision = metadata.tables["eligibility_decisions"]
            evidence = metadata.tables["eligibility_evidence"]
            invalid_issuances = connection.execute(
                select(func.count())
                .select_from(
                    credential.join(
                        decision,
                        credential.c.eligibility_decision_id == decision.c.id,
                    )
                    .outerjoin(
                        evidence,
                        and_(
                            evidence.c.eligibility_decision_id == decision.c.id,
                            evidence.c.completion_record_id.is_not(None),
                        ),
                    )
                    .outerjoin(
                        completion,
                        evidence.c.completion_record_id == completion.c.id,
                    )
                )
                .where(
                    or_(
                        decision.c.outcome != "eligible",
                        evidence.c.completion_record_id.is_(None),
                        completion.c.id.is_(None),
                        completion.c.status != "completed",
                        completion.c.completed_at.is_(None),
                        completion.c.completed_at > credential.c.issued_at,
                    )
                )
            ).scalar_one()
            ineligible_issuances = connection.execute(
                select(func.count())
                .select_from(
                    credential.join(
                        decision,
                        credential.c.eligibility_decision_id == decision.c.id,
                    )
                )
                .where(decision.c.outcome != "eligible")
            ).scalar_one()
            check(
                "credential_issuance_eligibility_and_completion_order",
                invalid_issuances == 0 and ineligible_issuances == 0,
                f"invalid_issuances={invalid_issuances}; ineligible={ineligible_issuances}",
            )

            snapshot_failures: list[str] = []
            for row in connection.execute(
                select(
                    decision.c.id,
                    decision.c.evidence_snapshot,
                    decision.c.input_snapshot_digest,
                )
            ):
                if hashlib.sha256(
                    json.dumps(
                        row.evidence_snapshot,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).digest() != row.input_snapshot_digest:
                    snapshot_failures.append(str(row.id))
                    if len(snapshot_failures) >= 5:
                        break
            for row in connection.execute(
                select(
                    evidence.c.id,
                    evidence.c.evidence_snapshot,
                    evidence.c.evidence_digest,
                )
            ):
                if hashlib.sha256(
                    json.dumps(
                        row.evidence_snapshot,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).digest() != row.evidence_digest:
                    snapshot_failures.append(str(row.id))
                    if len(snapshot_failures) >= 5:
                        break
            check(
                "eligibility_evidence_snapshot_digests",
                not snapshot_failures,
                "digest mismatches: " + (", ".join(snapshot_failures) or "none"),
            )

            version = metadata.tables["credential_rule_versions"]
            completion_evidence = evidence.alias("completion_evidence")
            selected_evidence = evidence.alias("selected_evidence")
            selected_attempt = attempt.alias("selected_attempt")
            decision_rows = connection.execute(
                select(
                    decision.c.id,
                    decision.c.outcome,
                    version.c.criteria,
                    completion.c.status,
                    selected_attempt.c.score,
                )
                .select_from(
                    decision.join(
                        version, decision.c.rule_version_id == version.c.id
                    )
                    .join(
                        completion_evidence,
                        and_(
                            completion_evidence.c.eligibility_decision_id
                            == decision.c.id,
                            completion_evidence.c.completion_record_id.is_not(None),
                        ),
                    )
                    .join(
                        completion,
                        completion_evidence.c.completion_record_id == completion.c.id,
                    )
                    .outerjoin(
                        selected_evidence,
                        and_(
                            selected_evidence.c.eligibility_decision_id == decision.c.id,
                            selected_evidence.c.assessment_attempt_id.is_not(None),
                        ),
                    )
                    .outerjoin(
                        selected_attempt,
                        selected_evidence.c.assessment_attempt_id == selected_attempt.c.id,
                    )
                )
            )
            evaluation_mismatches: list[str] = []
            for row in decision_rows:
                criteria = row.criteria
                minimum_score = criteria.get("minimum_score")
                if not isinstance(minimum_score, (int, float)):
                    evaluation_mismatches.append(f"{row.id}: invalid rule threshold")
                else:
                    expected_outcome = (
                        "eligible"
                        if row.status == "completed"
                        and row.score is not None
                        and row.score >= minimum_score
                        else "ineligible"
                    )
                    if row.outcome != expected_outcome:
                        evaluation_mismatches.append(str(row.id))
                if len(evaluation_mismatches) >= 5:
                    break
            check(
                "eligibility_outcomes_derived_from_source_evidence",
                not evaluation_mismatches,
                "mismatches: "
                + (", ".join(evaluation_mismatches) or "none"),
            )

            repeated_attempt_groups = connection.execute(
                select(
                    attempt.c.completion_record_id,
                    attempt.c.assessment_key,
                )
                .group_by(
                    attempt.c.completion_record_id,
                    attempt.c.assessment_key,
                )
                .having(func.count() > 1)
                .limit(1)
            ).first()
            check(
                "assessment_attempt_history",
                repeated_attempt_groups is not None,
                "at least one completion retains multiple distinct attempts",
            )

            invalid_scores = connection.execute(
                select(func.count())
                .select_from(attempt)
                .where(
                    attempt.c.score.is_not(None),
                    or_(
                        attempt.c.score < 0,
                        and_(
                            attempt.c.score_scale == "0-100",
                            attempt.c.score > 100,
                        ),
                    ),
                )
            ).scalar_one()
            check(
                "assessment_score_boundaries",
                invalid_scores == 0,
                f"invalid scores={invalid_scores}",
            )

            key_table = metadata.tables["issuer_signing_keys"]
            key_rows = connection.execute(
                select(
                    key_table.c.id,
                    key_table.c.public_key,
                    key_table.c.fingerprint,
                    key_table.c.valid_from,
                    key_table.c.valid_until,
                )
            ).all()
            keys = {
                row.id: Ed25519PublicKey.from_public_bytes(row.public_key)
                for row in key_rows
            }
            key_fingerprint_errors = [
                str(row.id)
                for row in key_rows
                if hashlib.sha256(row.public_key).digest() != row.fingerprint
            ]
            check(
                "issuer_key_public_material_fingerprints",
                not key_fingerprint_errors,
                "fingerprint mismatches: "
                + (", ".join(key_fingerprint_errors) or "none"),
            )
            signature_failures = []
            for row in connection.execute(
                select(
                    credential.c.credential_id,
                    credential.c.canonical_payload,
                    credential.c.sha256_digest,
                    credential.c.signature,
                    credential.c.signing_key_id,
                )
            ):
                digest_matches = hashlib.sha256(row.canonical_payload).digest() == row.sha256_digest
                signature_valid = True
                try:
                    keys[row.signing_key_id].verify(
                        row.signature, row.canonical_payload
                    )
                except InvalidSignature:
                    signature_valid = False
                if not digest_matches or not signature_valid:
                    signature_failures.append(row.credential_id)
                    if len(signature_failures) >= 5:
                        break
            check(
                "credential_digest_and_ed25519_signatures",
                not signature_failures,
                "invalid credentials: " + (", ".join(signature_failures) or "none"),
            )

            revocation = metadata.tables["revocations"]
            invalid_revocations = connection.execute(
                select(func.count())
                .select_from(
                    revocation.join(
                        credential, revocation.c.credential_id == credential.c.id
                    )
                )
                .where(revocation.c.effective_at < credential.c.issued_at)
            ).scalar_one()
            check(
                "revocation_consistency",
                invalid_revocations == 0,
                f"revocations before issuance={invalid_revocations}",
            )

            verification = metadata.tables["verification_requests"]
            expected_lifecycle = case(
                (
                    and_(
                        revocation.c.id.is_not(None),
                        revocation.c.effective_at <= verification.c.requested_at,
                    ),
                    "revoked",
                ),
                else_="active",
            )
            verification_errors = connection.execute(
                select(func.count())
                .select_from(
                    verification.join(
                        credential,
                        verification.c.credential_id_fk == credential.c.id,
                    ).outerjoin(
                        revocation,
                        revocation.c.credential_id == credential.c.id,
                    )
                )
                .where(
                    or_(
                        verification.c.lifecycle_result != expected_lifecycle,
                        verification.c.overall_result
                        != case(
                            (
                                expected_lifecycle == "revoked",
                                "revoked",
                            ),
                            else_="valid",
                        ),
                        verification.c.integrity_result != "valid",
                        verification.c.issuer_trust_result != "trusted",
                        and_(
                            verification.c.mode == "portable_payload",
                            verification.c.input_digest != credential.c.sha256_digest,
                        ),
                    )
                )
            ).scalar_one()
            check(
                "verification_lifecycle_outcomes",
                verification_errors == 0,
                f"verification lifecycle mismatches={verification_errors}",
            )

        seed_data_path = manifest_path.parent / manifest["seed_data_file"]
        check(
            "seed_data_file_checksum",
            file_sha256(seed_data_path) == manifest["seed_data_sha256"],
            seed_data_path.name,
        )
        export_digests: dict[str, Any] = defaultdict(hashlib.sha256)
        with gzip.open(seed_data_path, "rb") as stream:
            for line in stream:
                item = json.loads(line)
                export_digests[item["table"]].update(line)
        computed_checksums = {
            table_name: export_digests[table_name].hexdigest()
            for table_name in manifest["table_checksums"]
        }
        check(
            "deterministic_table_export_checksums",
            computed_checksums == manifest["table_checksums"],
            "table checksum manifest matches exported rows",
        )

        ground_truth_csv = ground_truth_dir / "ground_truth.csv"
        ground_truth_json = ground_truth_dir / "ground_truth.json"
        fixture_path = ground_truth_dir / "anomaly_fixtures.json"
        ground_truth_checks = manifest["ground_truth"]
        check(
            "ground_truth_separate_and_checksummed",
            file_sha256(ground_truth_csv) == ground_truth_checks["csv_sha256"]
            and file_sha256(ground_truth_json) == ground_truth_checks["json_sha256"]
            and file_sha256(fixture_path)
            == ground_truth_checks["anomaly_fixtures_sha256"],
            "ground truth and fixtures are outside operational tables",
        )
        source_manifest_path = manifest_path.parent / manifest["source_manifest"]
        check(
            "source_manifest_checksum",
            file_sha256(source_manifest_path)
            == manifest["source_manifest_sha256"],
            source_manifest_path.name,
        )
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_hash_failures = []
        for relative_path, expected_hash in source_manifest.get(
            "source_files", {}
        ).items():
            source_path = REPOSITORY_ROOT / Path(relative_path)
            if not source_path.is_file() or file_sha256(source_path) != expected_hash:
                source_hash_failures.append(relative_path)
        check(
            "synthetic_only_provenance",
            source_manifest.get("external_datasets") == []
            and source_manifest.get("dataset") == "synthetic",
            "no external datasets are used",
        )
        check(
            "source_file_hashes_match",
            not source_hash_failures,
            "mismatches: " + (", ".join(source_hash_failures) or "none"),
        )
        with ground_truth_json.open("r", encoding="utf-8") as stream:
            ground_truth_document = json.load(stream)
        with ground_truth_csv.open("r", newline="", encoding="utf-8") as stream:
            ground_truth_row_count = sum(1 for _ in csv.DictReader(stream))
        json_label_count = len(ground_truth_document.get("record_labels", []))
        expected_label_count = int(ground_truth_checks["labels"])
        check(
            "ground_truth_json_csv_reconciliation",
            ground_truth_document.get("dataset") == "synthetic"
            and json_label_count == ground_truth_row_count == expected_label_count,
            f"json={json_label_count}; csv={ground_truth_row_count}; "
            f"manifest={expected_label_count}",
        )
        fixtures_document = json.loads(fixture_path.read_text(encoding="utf-8"))
        fixture_results = verify_anomaly_fixtures(fixtures_document["fixtures"])
        required_fixtures = {
            "ineligible_issuance_attempt",
            "credential_issued_before_completion",
            "duplicate_credential_id_attempt",
            "revoked_credential_verifies_as_active",
            "altered_payload_hash_not_detected",
            "invalid_signature",
        }
        check(
            "isolated_anomaly_fixtures",
            fixtures_document["production_database_mutated"] is False
            and required_fixtures <= set(fixture_results)
            and all(fixture_results.values())
            and all(
                fixture["production_database_write"] is False
                for fixture in fixtures_document["fixtures"]
            ),
            json.dumps(fixture_results, sort_keys=True),
        )
        with ground_truth_csv.open("r", newline="", encoding="utf-8") as stream:
            labels = {row["label"] for row in csv.DictReader(stream)}
        required_labels = {
            "normal_credential",
            "normal_revoked_credential",
            "ineligible_issuance_attempt",
            "duplicate_credential_id_attempt",
            "revoked_credential_verifies_as_active",
            "altered_payload_hash_not_detected",
            "invalid_signature",
        }
        check(
            "ground_truth_label_coverage",
            required_labels <= labels,
            "missing labels: "
            + ", ".join(sorted(required_labels - labels)),
        )

        duplicate_fixture = next(
            fixture
            for fixture in fixtures_document["fixtures"]
            if fixture["scenario"] == "duplicate_credential_id_attempt"
        )
        duplicate_id = duplicate_fixture["candidate"]["credential_id"]
        credentials = metadata.tables["credentials"]
        decisions = metadata.tables["eligibility_decisions"]
        duplicate_probe_constraint = None
        with engine.begin() as connection:
            original_credential = connection.execute(
                select(credentials)
                .where(credentials.c.credential_id == duplicate_id)
                .limit(1)
            ).mappings().one()
            original_decision = connection.execute(
                select(decisions)
                .where(
                    decisions.c.id
                    == original_credential["eligibility_decision_id"]
                )
            ).mappings().one()
            probe_decision_id = stable_id("duplicate-id-probe-decision")
            probe_decision = dict(original_decision)
            probe_decision["id"] = probe_decision_id
            probe_decision["evaluated_at"] = (
                original_decision["evaluated_at"] + timedelta(seconds=1)
            )
            probe_decision["supersedes_decision_id"] = None
            candidate = dict(original_credential)
            candidate["id"] = stable_id("duplicate-id-probe-credential")
            candidate["eligibility_decision_id"] = probe_decision_id
            candidate["replacement_of_credential_id"] = original_credential["id"]
            savepoint = connection.begin_nested()
            try:
                connection.execute(decisions.insert(), probe_decision)
                connection.execute(credentials.insert(), candidate)
            except IntegrityError as exc:
                diagnostic = getattr(exc.orig, "diag", None)
                duplicate_probe_constraint = getattr(
                    diagnostic, "constraint_name", None
                )
                if savepoint.is_active:
                    savepoint.rollback()
            else:
                savepoint.rollback()
        check(
            "duplicate_credential_id_constraint_fixture",
            duplicate_probe_constraint == "uq_credentials_external_id",
            "savepoint rejected duplicate external ID using production constraint; "
            f"constraint={duplicate_probe_constraint}",
        )
        check(
            "fixed_seed",
            manifest.get("seed") == SEED,
            f"seed={manifest.get('seed')}",
        )

        summary = {
            "dataset": "synthetic",
            "seed": manifest.get("seed"),
            "profile": manifest.get("profile"),
            "status": "passed" if all(item["passed"] for item in results) else "failed",
            "actual_row_counts": counts,
            "checks": results,
            "failed_checks": [
                item["name"] for item in results if not item["passed"]
            ],
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, sort_keys=True, indent=2))
        return 0 if summary["status"] == "passed" else 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Seed validation failed: {exc}", file=sys.stderr)
        raise
