from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.database.base import Base

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class UUIDPrimaryKey:
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "users"

    principal_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Role(UUIDPrimaryKey, Base):
    __tablename__ = "roles"

    role_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserRole(UUIDPrimaryKey, Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name="ck_user_roles_revocation_after_grant",
        ),
        Index(
            "uq_user_roles_active_user_role",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    granted_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class Learner(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "learners"

    learner_id: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), unique=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "learner_id ~ '^LRN-[0-9]{6}$'", name="ck_learners_external_id_format"
        ),
        CheckConstraint("length(trim(display_name)) > 0", name="ck_learners_name_nonempty"),
    )


class Course(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_courses_effective_period",
        ),
    )

    course_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CredentialScope(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "credential_scopes"

    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, unique=True
    )


class CredentialRule(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "credential_rules"

    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CredentialRuleVersion(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "credential_rule_versions"
    __table_args__ = (
        UniqueConstraint("rule_id", "version_number", name="uq_rule_versions_number"),
        UniqueConstraint("id", "credential_scope_id", name="uq_rule_versions_id_scope"),
        CheckConstraint("version_number > 0", name="ck_rule_versions_positive_number"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_rule_versions_effective_period",
        ),
        CheckConstraint(
            "jsonb_typeof(criteria) = 'object'", name="ck_rule_versions_criteria_object"
        ).ddl_if(dialect="postgresql"),
    )

    rule_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credential_rules.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    credential_scope_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("credential_scopes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    attempt_selection_policy: Mapped[str | None] = mapped_column(String(24))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class RuleCourse(Base):
    __tablename__ = "rule_courses"

    rule_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("credential_rule_versions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Enrollment(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("id", "learner_id", "course_id", name="uq_enrollments_context"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_enrollments_effective_period",
        ),
    )

    learner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learners.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class CompletionRecord(UUIDPrimaryKey, Base):
    __tablename__ = "completion_records"
    __table_args__ = (
        UniqueConstraint("id", "learner_id", name="uq_completions_id_learner"),
        UniqueConstraint("enrollment_id", name="uq_completions_enrollment"),
        ForeignKeyConstraint(
            ["enrollment_id", "learner_id", "course_id"],
            ["enrollments.id", "enrollments.learner_id", "enrollments.course_id"],
            name="fk_completions_enrollment_context",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="ck_completions_time_order",
        ),
        CheckConstraint(
            "enrollment_id IS NOT NULL OR (learner_id IS NOT NULL AND course_id IS NOT NULL)",
            name="ck_completions_parent_context",
        ),
    )

    learner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learners.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    enrollment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    source_reference: Mapped[str | None] = mapped_column(String(200))


class AssessmentAttempt(UUIDPrimaryKey, Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        UniqueConstraint(
            "completion_record_id",
            "assessment_key",
            "attempt_number",
            name="uq_attempts_sequence",
        ),
        UniqueConstraint("id", "completion_record_id", name="uq_attempts_completion_context"),
        UniqueConstraint("id", "learner_id", name="uq_attempts_id_learner"),
        ForeignKeyConstraint(
            ["completion_record_id", "learner_id"],
            ["completion_records.id", "completion_records.learner_id"],
            name="fk_attempts_completion_learner",
            ondelete="RESTRICT",
        ),
        CheckConstraint("attempt_number > 0", name="ck_attempts_positive_number"),
        CheckConstraint(
            "graded_at IS NULL OR graded_at >= submitted_at", name="ck_attempts_time_order"
        ),
        CheckConstraint(
            "score IS NULL OR score_scale IS NOT NULL", name="ck_attempts_score_scale"
        ),
        ForeignKeyConstraint(
            ["supersedes_attempt_id", "completion_record_id"],
            ["assessment_attempts.id", "assessment_attempts.completion_record_id"],
            name="fk_attempts_superseded_same_completion",
            ondelete="RESTRICT",
        ),
    )

    completion_record_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("completion_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    learner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    assessment_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    score_scale: Mapped[str | None] = mapped_column(String(40))
    result_code: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="submitted")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    supersedes_attempt_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))


class EligibilityDecision(UUIDPrimaryKey, Base):
    __tablename__ = "eligibility_decisions"
    __table_args__ = (
        UniqueConstraint("id", "learner_id", name="uq_decisions_id_learner"),
        UniqueConstraint(
            "id", "learner_id", "rule_version_id", "credential_scope_id",
            name="uq_decisions_issuance_context",
        ),
        ForeignKeyConstraint(
            ["rule_version_id", "credential_scope_id"],
            ["credential_rule_versions.id", "credential_rule_versions.credential_scope_id"],
            name="fk_decisions_rule_scope",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "outcome IN ('eligible', 'ineligible', 'needs_review')",
            name="ck_decisions_outcome",
        ),
        CheckConstraint(
            "evaluator_type IN ('user', 'service')", name="ck_decisions_evaluator_type"
        ),
        CheckConstraint(
            "input_snapshot_digest IS NULL OR octet_length(input_snapshot_digest) = 32",
            name="ck_decisions_digest_length",
        ).ddl_if(dialect="postgresql"),
    )

    learner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learners.id", ondelete="RESTRICT"), nullable=False
    )
    rule_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    credential_scope_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    evaluator_type: Mapped[str] = mapped_column(String(24), nullable=False)
    evaluator_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    evaluator_reference: Mapped[str | None] = mapped_column(String(200))
    evaluator_version: Mapped[str] = mapped_column(String(40), nullable=False)
    attempt_selection_policy: Mapped[str | None] = mapped_column(String(24))
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    input_snapshot_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    supersedes_decision_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("eligibility_decisions.id", ondelete="RESTRICT")
    )


class EligibilityReason(UUIDPrimaryKey, Base):
    __tablename__ = "eligibility_reasons"

    eligibility_decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eligibility_decisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EligibilityEvidence(UUIDPrimaryKey, Base):
    __tablename__ = "eligibility_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["eligibility_decision_id", "learner_id"],
            ["eligibility_decisions.id", "eligibility_decisions.learner_id"],
            name="fk_evidence_decision_learner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["completion_record_id", "learner_id"],
            ["completion_records.id", "completion_records.learner_id"],
            name="fk_evidence_completion_learner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["assessment_attempt_id", "learner_id"],
            ["assessment_attempts.id", "assessment_attempts.learner_id"],
            name="fk_evidence_attempt_learner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(completion_record_id IS NOT NULL AND assessment_attempt_id IS NULL) OR "
            "(completion_record_id IS NULL AND assessment_attempt_id IS NOT NULL)",
            name="ck_evidence_exactly_one_source",
        ),
    )

    eligibility_decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    learner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    completion_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("completion_records.id", ondelete="RESTRICT")
    )
    assessment_attempt_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("assessment_attempts.id", ondelete="RESTRICT")
    )
    selection_role: Mapped[str] = mapped_column(String(24), nullable=False)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    evidence_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Issuer(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "issuers"

    issuer_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IssuerSigningKey(UUIDPrimaryKey, Base):
    __tablename__ = "issuer_signing_keys"
    __table_args__ = (
        UniqueConstraint("issuer_id", "key_id", name="uq_issuer_keys_issuer_key"),
        UniqueConstraint("issuer_id", "fingerprint", name="uq_issuer_keys_fingerprint"),
        UniqueConstraint("id", "issuer_id", name="uq_issuer_keys_id_issuer"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from", name="ck_issuer_keys_validity"
        ),
        CheckConstraint(
            "algorithm = 'Ed25519'", name="ck_issuer_keys_algorithm"
        ),
        CheckConstraint(
            "octet_length(public_key) = 32 AND octet_length(fingerprint) = 32",
            name="ck_issuer_keys_public_material_length",
        ).ddl_if(dialect="postgresql"),
        ForeignKeyConstraint(
            ["supersedes_key_id", "issuer_id"],
            ["issuer_signing_keys.id", "issuer_signing_keys.issuer_id"],
            name="fk_issuer_keys_rotation_same_issuer",
            ondelete="RESTRICT",
        ),
    )

    issuer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issuers.id", ondelete="RESTRICT"), nullable=False
    )
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    fingerprint: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(40), nullable=False)
    key_purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="credential_signing")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    supersedes_key_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    registered_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CredentialAward(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "credential_awards"
    __table_args__ = (
        UniqueConstraint("learner_id", "credential_scope_id", name="uq_awards_learner_scope"),
        UniqueConstraint("id", "learner_id", "credential_scope_id", name="uq_awards_context"),
    )

    learner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learners.id", ondelete="RESTRICT"), nullable=False
    )
    credential_scope_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("credential_scopes.id", ondelete="RESTRICT"),
        nullable=False,
    )


class Credential(UUIDPrimaryKey, Base):
    __tablename__ = "credentials"
    __table_args__ = (
        UniqueConstraint("credential_id", name="uq_credentials_external_id"),
        UniqueConstraint("id", "award_id", name="uq_credentials_id_award"),
        UniqueConstraint("eligibility_decision_id", name="uq_credentials_decision"),
        ForeignKeyConstraint(
            ["award_id", "learner_id", "credential_scope_id"],
            ["credential_awards.id", "credential_awards.learner_id",
             "credential_awards.credential_scope_id"],
            name="fk_credentials_award_context",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["eligibility_decision_id", "learner_id", "rule_version_id",
             "credential_scope_id"],
            ["eligibility_decisions.id", "eligibility_decisions.learner_id",
             "eligibility_decisions.rule_version_id",
             "eligibility_decisions.credential_scope_id"],
            name="fk_credentials_decision_context",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["signing_key_id", "issuer_id"],
            ["issuer_signing_keys.id", "issuer_signing_keys.issuer_id"],
            name="fk_credentials_signing_key_issuer",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["replacement_of_credential_id", "award_id"],
            ["credentials.id", "credentials.award_id"],
            name="fk_credentials_replacement_same_award",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("replacement_of_credential_id", name="uq_credentials_one_successor"),
        CheckConstraint(
            "credential_id ~ '^CRD-[0-9]{4}-[0-9]{6}$'",
            name="ck_credentials_external_id_format",
        ),
        CheckConstraint(
            "octet_length(sha256_digest) = 32", name="ck_credentials_digest_length"
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "signature_algorithm = 'Ed25519' AND octet_length(signature) = 64",
            name="ck_credentials_signature_format",
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "signature IS NOT NULL AND signature_algorithm IS NOT NULL AND signing_key_id IS NOT NULL",
            name="ck_credentials_signature_fields",
        ),
        CheckConstraint(
            "replacement_of_credential_id IS NOT NULL OR eligibility_decision_id IS NOT NULL",
            name="ck_credentials_decision_required",
        ),
        Index(
            "uq_credentials_one_root_per_award",
            "award_id",
            unique=True,
            postgresql_where=text("replacement_of_credential_id IS NULL"),
        ),
        Index("ix_credentials_learner_scope", "learner_id", "credential_scope_id"),
        Index("ix_credentials_issuer_id", "issuer_id"),
    )

    credential_id: Mapped[str] = mapped_column(String(15), nullable=False)
    award_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    learner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    credential_scope_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    issuer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issuers.id", ondelete="RESTRICT"), nullable=False
    )
    rule_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credential_rule_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    eligibility_decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    replacement_of_credential_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload_version: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    signature: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(String(40), nullable=False)
    signing_key_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)


class VerificationRequest(UUIDPrimaryKey, Base):
    __tablename__ = "verification_requests"
    __table_args__ = (
        CheckConstraint(
            "verification_id ~ '^VER-[0-9]{4}-[0-9]{6}$'",
            name="ck_verifications_external_id_format",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= requested_at",
            name="ck_verifications_time_order",
        ),
        CheckConstraint(
            "input_digest IS NULL OR octet_length(input_digest) = 32",
            name="ck_verifications_digest_length",
        ).ddl_if(dialect="postgresql"),
        Index("ix_verifications_credential_requested", "credential_id_fk", "requested_at"),
    )

    verification_id: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    mode: Mapped[str] = mapped_column(String(24), nullable=False)
    submitted_credential_id: Mapped[str | None] = mapped_column(String(15))
    credential_id_fk: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credentials.id", ondelete="RESTRICT")
    )
    resolved_issuer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issuers.id", ondelete="RESTRICT")
    )
    resolved_signing_key_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issuer_signing_keys.id", ondelete="RESTRICT")
    )
    input_digest: Mapped[bytes | None] = mapped_column(LargeBinary(32))
    integrity_result: Mapped[str] = mapped_column(String(24), nullable=False)
    issuer_trust_result: Mapped[str] = mapped_column(String(24), nullable=False)
    lifecycle_result: Mapped[str] = mapped_column(String(24), nullable=False)
    overall_result: Mapped[str] = mapped_column(String(32), nullable=False)
    requester_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    requester_reference: Mapped[str | None] = mapped_column(String(200))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))


class Revocation(UUIDPrimaryKey, Base):
    __tablename__ = "revocations"
    __table_args__ = (
        UniqueConstraint("credential_id", name="uq_revocations_credential"),
    )

    credential_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credentials.id", ondelete="RESTRICT"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_detail: Mapped[str | None] = mapped_column(Text)
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    actor_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))


class IdempotencyRecord(UUIDPrimaryKey, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "principal_key", "operation", "idempotency_key_digest",
            name="uq_idempotency_scope_key",
        ),
        CheckConstraint("expires_at > created_at", name="ck_idempotency_expiry"),
        CheckConstraint(
            "octet_length(idempotency_key_digest) = 32 AND "
            "octet_length(request_fingerprint) = 32",
            name="ck_idempotency_digest_lengths",
        ).ddl_if(dialect="postgresql"),
    )

    principal_key: Mapped[str] = mapped_column(String(200), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    request_fingerprint: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    credential_id_fk: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credentials.id", ondelete="RESTRICT")
    )
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="in_progress")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEvent(UUIDPrimaryKey, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_target_time", "target_type", "target_reference", "occurred_at"),
        Index("ix_audit_events_correlation", "correlation_id"),
        Index("ix_audit_events_occurred", "occurred_at"),
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    actor_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_reference: Mapped[str | None] = mapped_column(String(200))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    event_data: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
