from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.core.errors import ServiceError
from app.models.domain import (
    AssessmentAttempt,
    CompletionRecord,
    Course,
    CredentialRule,
    CredentialRuleVersion,
    CredentialScope,
    Enrollment,
    Issuer,
    IssuerSigningKey,
    Learner,
    Role,
    RuleCourse,
    User,
)
from app.services.audit import record_event


# Allowance for a client clock that runs slightly ahead of the server clock. The
# eligibility evaluator and issuance apply no allowance: a completion counts only
# once the server clock has reached its completed_at value.
FUTURE_TIMESTAMP_TOLERANCE = timedelta(minutes=5)


def _require_aware(value: datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ServiceError(422, f"{field_name} must include a timezone.")


def _require_not_future(value: datetime | None, field_name: str) -> None:
    """Reject a timestamp that lies in the future. Call after _require_aware."""
    if value is not None and value > datetime.now(timezone.utc) + FUTURE_TIMESTAMP_TOLERANCE:
        raise ServiceError(422, f"{field_name} cannot be in the future.")


def _require_enforceable_criteria(criteria: dict) -> None:
    """Reject a rule that requires neither course completion nor a minimum score."""
    if criteria.get("requires_completion", True) is False and criteria.get("minimum_score") is None:
        raise ServiceError(
            422,
            "A credential rule must require course completion, a minimum score, or both.",
        )


def create_learner(
    db: Session, *, learner_id: str | None, display_name: str, user_id: UUID | None, actor_id: UUID
) -> Learner:
    if not display_name.strip():
        raise ServiceError(422, "Learner display name cannot be empty.")
    if user_id is not None and db.get(User, user_id) is None:
        raise ServiceError(404, "Linked user was not found.")
    if learner_id is None:
        now = datetime.now(timezone.utc)
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.execute(select(func.pg_advisory_xact_lock(func.hashtext("learner-id-sequence"))))
        max_number = db.scalar(
            select(func.max(cast(func.substr(Learner.learner_id, 5), Integer)))
        )
        if int(max_number or 0) >= 999_999:
            raise ServiceError(409, "Learner ID sequence is exhausted.")
        learner_id = f"LRN-{int(max_number or 0) + 1:06d}"
    if not re.fullmatch(r"LRN-[0-9]{6}", learner_id):
        raise ServiceError(422, "Learner ID must match LRN-000001.")
    learner = Learner(
        id=uuid4(), learner_id=learner_id, display_name=display_name.strip(), user_id=user_id
    )
    db.add(learner)
    record_event(
        db, event_type="learner.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="learner",
        target_reference=learner_id,
    )
    db.flush()
    return learner


def update_learner(
    db: Session, *, learner_id: UUID, changes: dict, actor_id: UUID
) -> Learner:
    learner = db.get(Learner, learner_id)
    if learner is None:
        raise ServiceError(404, "Learner was not found.")
    previous = {"display_name": learner.display_name, "archived_at": learner.archived_at}
    if "display_name" in changes:
        value = changes["display_name"]
        if value is None or not value.strip():
            raise ServiceError(422, "Learner display name cannot be empty.")
        learner.display_name = value.strip()
    if "archived" in changes:
        learner.archived_at = (
            datetime.now(timezone.utc) if changes["archived"] else None
        )
    record_event(
        db, event_type="learner.updated", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="learner",
        target_reference=learner.learner_id,
        event_data={
            "previous": {
                "display_name": previous["display_name"],
                "archived": previous["archived_at"] is not None,
            },
            "current": {
                "display_name": learner.display_name,
                "archived": learner.archived_at is not None,
            },
        },
    )
    db.flush()
    return learner


def create_course(db: Session, *, data: dict, actor_id: UUID) -> Course:
    data["course_code"] = data["course_code"].strip()
    data["title"] = data["title"].strip()
    if not data["course_code"] or not data["title"]:
        raise ServiceError(422, "Course code and title cannot be empty.")
    _require_aware(data["effective_from"], "effective_from")
    _require_aware(data["effective_to"], "effective_to")
    if data["effective_to"] and data["effective_from"] and data["effective_to"] <= data["effective_from"]:
        raise ServiceError(422, "Course effective_to must be later than effective_from.")
    if data["status"] not in {"active", "inactive", "archived"}:
        raise ServiceError(422, "Course status is invalid.")
    course = Course(id=uuid4(), **data)
    db.add(course)
    record_event(
        db, event_type="course.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="course",
        target_reference=course.course_code,
    )
    db.flush()
    return course


def update_course(
    db: Session, *, course_id: UUID, changes: dict, actor_id: UUID
) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise ServiceError(404, "Course was not found.")
    previous = {
        "title": course.title,
        "description": course.description,
        "status": course.status,
    }
    if "status" in changes:
        if changes["status"] not in {"active", "inactive", "archived"}:
            raise ServiceError(422, "Course status is invalid.")
        course.status = changes["status"]
    _require_aware(changes.get("effective_from"), "effective_from")
    _require_aware(changes.get("effective_to"), "effective_to")
    if "title" in changes and (changes["title"] is None or not changes["title"].strip()):
        raise ServiceError(422, "Course title cannot be empty.")
    for field in ("title", "description", "effective_from", "effective_to"):
        if field in changes:
            setattr(course, field, changes[field])
    if (
        course.effective_from
        and course.effective_to
        and course.effective_to <= course.effective_from
    ):
        raise ServiceError(422, "Course effective_to must be later than effective_from.")
    record_event(
        db, event_type="course.updated", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="course",
        target_reference=course.course_code,
        event_data={
            "previous": previous,
            "current": {
                "title": course.title,
                "description": course.description,
                "status": course.status,
            },
        },
    )
    db.flush()
    return course


def create_issuer(db: Session, *, issuer_code: str, name: str, actor_id: UUID) -> Issuer:
    issuer = Issuer(
        id=uuid4(), issuer_code=issuer_code.strip(), name=name.strip(), status="active"
    )
    if not issuer.issuer_code or not issuer.name:
        raise ServiceError(422, "Issuer code and name are required.")
    db.add(issuer)
    record_event(
        db, event_type="issuer.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="issuer",
        target_reference=issuer.issuer_code,
    )
    db.flush()
    return issuer


def update_issuer(
    db: Session, *, issuer_code: str, name: str | None, status: str | None,
    actor_id: UUID,
) -> Issuer:
    issuer = db.scalar(select(Issuer).where(Issuer.issuer_code == issuer_code))
    if issuer is None:
        raise ServiceError(404, "Issuer was not found.")
    if issuer.archived_at is not None:
        raise ServiceError(409, "Archived issuer profiles cannot be reactivated or edited.")
    previous = {"name": issuer.name, "status": issuer.status}
    if name is not None:
        if not name.strip():
            raise ServiceError(422, "Issuer name cannot be empty.")
        issuer.name = name.strip()
    if status is not None:
        if status not in {"active", "suspended", "archived"}:
            raise ServiceError(422, "Issuer status is invalid.")
        issuer.status = status
        if status == "archived":
            issuer.archived_at = datetime.now(timezone.utc)
    record_event(
        db, event_type="issuer.profile_updated", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="issuer",
        target_reference=issuer.issuer_code,
        event_data={
            "previous": previous,
            "current": {"name": issuer.name, "status": issuer.status},
        },
    )
    db.flush()
    return issuer


def register_signing_key(
    db: Session, *, issuer_code: str, key_id: str, public_key_base64: str,
    algorithm: str, valid_from: datetime, valid_until: datetime | None,
    actor_id: UUID, supersedes_key_id: UUID | None = None,
) -> IssuerSigningKey:
    issuer = db.scalar(
        select(Issuer).where(Issuer.issuer_code == issuer_code, Issuer.status == "active")
    )
    if issuer is None:
        raise ServiceError(404, "Active issuer was not found.")
    if algorithm != "Ed25519":
        raise ServiceError(422, "Only Ed25519 issuer keys are supported.")
    try:
        public_key = base64.b64decode(public_key_base64, validate=True)
    except ValueError as exc:
        raise ServiceError(422, "Public key must be valid base64.") from exc
    if len(public_key) != 32:
        raise ServiceError(422, "Ed25519 public keys must contain exactly 32 bytes.")
    _require_aware(valid_from, "valid_from")
    _require_aware(valid_until, "valid_until")
    if valid_until is not None and valid_until <= valid_from:
        raise ServiceError(422, "Key valid_until must be later than valid_from.")
    previous_key = None
    if supersedes_key_id is not None:
        previous_key = db.get(IssuerSigningKey, supersedes_key_id)
        if (
            previous_key is None
            or previous_key.issuer_id != issuer.id
            or previous_key.status != "active"
            or valid_from <= previous_key.valid_from
        ):
            raise ServiceError(
                422,
                "Rotation must reference a later key belonging to the same active issuer.",
            )
        previous_key.status = "retired"
        previous_key.valid_until = valid_from
    key = IssuerSigningKey(
        id=uuid4(),
        issuer_id=issuer.id,
        key_id=key_id,
        public_key=public_key,
        fingerprint=hashlib.sha256(public_key).digest(),
        algorithm=algorithm,
        key_purpose="credential_signing",
        valid_from=valid_from,
        valid_until=valid_until,
        status="active",
        supersedes_key_id=supersedes_key_id,
        registered_by_user_id=actor_id,
        approved_by_user_id=actor_id,
        registered_at=datetime.now(timezone.utc),
    )
    db.add(key)
    record_event(
        db, event_type="issuer.signing_key_registered", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="issuer",
        target_reference=issuer_code, event_data={"key_id": key_id},
    )
    db.flush()
    return key


def create_rule(
    db: Session, *, rule_code: str, name: str, description: str | None,
    course_id: UUID, criteria: dict, attempt_selection_policy: str | None,
    effective_from: datetime, actor_id: UUID,
) -> tuple[CredentialRule, CredentialRuleVersion, CredentialScope]:
    course = db.get(Course, course_id)
    if course is None or course.status != "active":
        raise ServiceError(404, "Active course was not found.")
    supported = {"requires_completion", "minimum_score", "score_scale", "attempt_selection_policy"}
    if set(criteria) - supported:
        raise ServiceError(422, "Rule criteria contain unsupported fields.")
    if not isinstance(criteria.get("requires_completion", True), bool):
        raise ServiceError(422, "requires_completion must be boolean.")
    _require_enforceable_criteria(criteria)
    threshold = criteria.get("minimum_score")
    if threshold is not None:
        try:
            threshold_number = Decimal(str(threshold))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ServiceError(422, "minimum_score must be numeric.") from exc
        if (
            not threshold_number.is_finite()
            or not Decimal(0) <= threshold_number <= Decimal(100)
        ):
            raise ServiceError(422, "minimum_score must be between 0 and 100.")
    policy = attempt_selection_policy or criteria.get("attempt_selection_policy")
    if policy not in {None, "latest_graded"}:
        raise ServiceError(422, "MVP supports only the latest_graded attempt policy.")
    if threshold is not None and criteria.get("score_scale", "0-100") != "0-100":
        raise ServiceError(422, "MVP score thresholds must use the 0-100 scale.")
    _require_aware(effective_from, "effective_from")
    rule = CredentialRule(
        id=uuid4(), rule_code=rule_code.strip(), name=name.strip(), description=description
    )
    if not rule.rule_code or not rule.name:
        raise ServiceError(422, "Rule code and name cannot be empty.")
    db.add(rule)
    db.flush()
    scope = db.scalar(
        select(CredentialScope).where(CredentialScope.course_id == course_id)
    )
    if scope is None:
        scope = CredentialScope(id=uuid4(), course_id=course_id)
        db.add(scope)
        db.flush()
    version = CredentialRuleVersion(
        id=uuid4(),
        rule_id=rule.id,
        version_number=1,
        credential_scope_id=scope.id,
        criteria={**criteria, "attempt_selection_policy": policy or "latest_graded"},
        attempt_selection_policy=policy or "latest_graded",
        effective_from=effective_from,
        status="active",
        created_by_user_id=actor_id,
    )
    db.add(version)
    db.flush()
    db.add(RuleCourse(rule_version_id=version.id, course_id=course_id))
    record_event(
        db, event_type="credential_rule.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="credential_rule",
        target_reference=rule_code, event_data={"version": version.version_number},
    )
    db.flush()
    return rule, version, scope


def create_rule_version(
    db: Session, *, rule_code: str, course_id: UUID, criteria: dict,
    attempt_selection_policy: str | None, effective_from: datetime, actor_id: UUID,
) -> tuple[CredentialRule, CredentialRuleVersion, CredentialScope]:
    rule = db.scalar(
        select(CredentialRule).where(
            CredentialRule.rule_code == rule_code,
            CredentialRule.archived_at.is_(None),
        )
    )
    if rule is None:
        raise ServiceError(404, "Credential rule was not found.")
    latest = db.scalar(
        select(CredentialRuleVersion)
        .where(CredentialRuleVersion.rule_id == rule.id)
        .order_by(CredentialRuleVersion.version_number.desc())
        .limit(1)
        .with_for_update()
    )
    if latest is None:
        raise ServiceError(409, "Credential rule has no prior version.")
    _require_aware(effective_from, "effective_from")
    if effective_from <= latest.effective_from:
        raise ServiceError(422, "New rule version must start after the previous version.")
    course = db.get(Course, course_id)
    if course is None or course.status != "active":
        raise ServiceError(404, "Active course was not found.")
    supported = {"requires_completion", "minimum_score", "score_scale", "attempt_selection_policy"}
    if set(criteria) - supported:
        raise ServiceError(422, "Rule criteria contain unsupported fields.")
    if not isinstance(criteria.get("requires_completion", True), bool):
        raise ServiceError(422, "requires_completion must be boolean.")
    _require_enforceable_criteria(criteria)
    threshold = criteria.get("minimum_score")
    if threshold is not None:
        try:
            threshold_number = Decimal(str(threshold))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ServiceError(422, "minimum_score must be numeric.") from exc
        if (
            not threshold_number.is_finite()
            or not Decimal(0) <= threshold_number <= Decimal(100)
        ):
            raise ServiceError(422, "minimum_score must be between 0 and 100.")
    policy = attempt_selection_policy or criteria.get("attempt_selection_policy") or "latest_graded"
    if policy != "latest_graded":
        raise ServiceError(422, "MVP supports only the latest_graded attempt policy.")
    if threshold is not None and criteria.get("score_scale", "0-100") != "0-100":
        raise ServiceError(422, "MVP score thresholds must use the 0-100 scale.")
    scope = db.scalar(
        select(CredentialScope).where(CredentialScope.course_id == course_id)
    )
    if scope is None:
        scope = CredentialScope(id=uuid4(), course_id=course_id)
        db.add(scope)
        db.flush()
    if latest.effective_to is None:
        latest.effective_to = effective_from
    elif latest.effective_to > effective_from:
        raise ServiceError(422, "New version cannot overlap the previous effective period.")
    version = CredentialRuleVersion(
        id=uuid4(),
        rule_id=rule.id,
        version_number=latest.version_number + 1,
        credential_scope_id=scope.id,
        criteria={**criteria, "attempt_selection_policy": policy},
        attempt_selection_policy=policy,
        effective_from=effective_from,
        status="active",
        created_by_user_id=actor_id,
    )
    db.add(version)
    db.flush()
    db.add(RuleCourse(rule_version_id=version.id, course_id=course_id))
    record_event(
        db, event_type="credential_rule.version_created",
        actor_user_id=actor_id, actor_reference=str(actor_id),
        target_type="credential_rule", target_reference=rule_code,
        event_data={"version": version.version_number},
    )
    db.flush()
    return rule, version, scope


def revoke_signing_key(
    db: Session, *, issuer_code: str, key_id: str, actor_id: UUID
) -> IssuerSigningKey:
    key = db.scalar(
        select(IssuerSigningKey)
        .join(Issuer, Issuer.id == IssuerSigningKey.issuer_id)
        .where(
            Issuer.issuer_code == issuer_code,
            IssuerSigningKey.key_id == key_id,
        )
        .with_for_update()
    )
    if key is None:
        raise ServiceError(404, "Issuer signing key was not found.")
    if key.status == "revoked":
        raise ServiceError(409, "Issuer signing key is already revoked.")
    key.status = "revoked"
    key.revoked_at = datetime.now(timezone.utc)
    record_event(
        db, event_type="issuer.signing_key_revoked", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="issuer",
        target_reference=issuer_code, reason_code="KEY_REVOKED",
        event_data={"key_id": key_id},
    )
    db.flush()
    return key


def create_enrollment(
    db: Session, *, learner_id: UUID, course_id: UUID, effective_from: datetime | None,
    actor_id: UUID,
) -> Enrollment:
    learner = db.get(Learner, learner_id)
    course = db.get(Course, course_id)
    if learner is None or learner.archived_at is not None:
        raise ServiceError(404, "Active learner was not found.")
    if course is None or course.status != "active":
        raise ServiceError(404, "Active course was not found.")
    _require_aware(effective_from, "effective_from")
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        lock_key = f"enrollment-{learner_id}-{course_id}"
        db.execute(select(func.pg_advisory_xact_lock(func.hashtext(lock_key))))
    existing = db.scalar(
        select(Enrollment.id).where(
            Enrollment.learner_id == learner_id,
            Enrollment.course_id == course_id,
            Enrollment.status != "cancelled",
        )
    )
    if existing is not None:
        raise ServiceError(409, "An active enrollment already exists for this learner and course.")
    enrollment = Enrollment(
        id=uuid4(), learner_id=learner_id, course_id=course_id,
        status="active", effective_from=effective_from,
        recorded_by_user_id=actor_id,
    )
    db.add(enrollment)
    record_event(
        db, event_type="enrollment.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="enrollment",
        target_reference=str(enrollment.id),
    )
    db.flush()
    return enrollment


def create_completion(
    db: Session, *, enrollment_id: UUID, status: str, started_at: datetime | None,
    completed_at: datetime | None, source_reference: str | None, actor_id: UUID,
) -> CompletionRecord:
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise ServiceError(404, "Enrollment was not found.")
    if status not in {"in_progress", "completed", "incomplete", "failed"}:
        raise ServiceError(422, "Completion status is invalid.")
    _require_aware(started_at, "started_at")
    _require_aware(completed_at, "completed_at")
    _require_not_future(completed_at, "completed_at")
    if status == "completed" and completed_at is None:
        raise ServiceError(422, "completed_at is required for completed records.")
    if status != "completed" and completed_at is not None:
        raise ServiceError(422, "completed_at is allowed only for completed records.")
    if started_at and completed_at and completed_at < started_at:
        raise ServiceError(422, "completed_at cannot precede started_at.")
    completion = CompletionRecord(
        id=uuid4(), learner_id=enrollment.learner_id, course_id=enrollment.course_id,
        enrollment_id=enrollment.id, status=status, started_at=started_at,
        completed_at=completed_at, recorded_at=datetime.now(timezone.utc),
        recorded_by_user_id=actor_id, source_reference=source_reference,
    )
    db.add(completion)
    record_event(
        db, event_type="completion.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="completion",
        target_reference=str(completion.id), event_data={"status": status},
    )
    db.flush()
    return completion


def update_completion_status(
    db: Session, *, completion_id: UUID, status: str, completed_at: datetime | None,
    actor_id: UUID,
) -> CompletionRecord:
    completion = db.get(CompletionRecord, completion_id)
    if completion is None:
        raise ServiceError(404, "Completion record was not found.")
    if status not in {"in_progress", "completed", "incomplete", "failed"}:
        raise ServiceError(422, "Completion status is invalid.")
    _require_aware(completed_at, "completed_at")
    _require_not_future(completed_at, "completed_at")
    if status == "completed" and completed_at is None:
        raise ServiceError(422, "completed_at is required for completed records.")
    if status != "completed" and completed_at is not None:
        raise ServiceError(422, "completed_at is allowed only for completed records.")
    if completion.started_at and completed_at and completed_at < completion.started_at:
        raise ServiceError(422, "completed_at cannot precede started_at.")
    previous_status = completion.status
    completion.status = status
    completion.completed_at = completed_at
    record_event(
        db, event_type="completion.status_updated", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="completion",
        target_reference=str(completion.id),
        event_data={"from": previous_status, "to": status},
    )
    db.flush()
    return completion


def create_assessment_attempt(
    db: Session, *, completion_record_id: UUID, assessment_key: str,
    score: Decimal | None, score_scale: str | None, result_code: str | None,
    status: str, submitted_at: datetime, graded_at: datetime | None,
    supersedes_attempt_id: UUID | None, actor_id: UUID,
) -> AssessmentAttempt:
    completion = db.scalar(
        select(CompletionRecord)
        .where(CompletionRecord.id == completion_record_id)
        .with_for_update()
    )
    if completion is None:
        raise ServiceError(404, "Completion record was not found.")
    if score is not None and not Decimal(0) <= score <= Decimal(100):
        raise ServiceError(422, "Score must be between 0 and 100.")
    if score is not None and score_scale != "0-100":
        raise ServiceError(422, "Scores must use the declared 0-100 scale.")
    if status not in {"submitted", "graded", "voided"}:
        raise ServiceError(422, "Assessment attempt status is invalid.")
    if status == "graded" and (score is None or graded_at is None):
        raise ServiceError(422, "Graded attempts require score and graded_at.")
    _require_aware(submitted_at, "submitted_at")
    _require_aware(graded_at, "graded_at")
    if graded_at and graded_at < submitted_at:
        raise ServiceError(422, "graded_at cannot precede submitted_at.")
    if supersedes_attempt_id is not None:
        prior = db.get(AssessmentAttempt, supersedes_attempt_id)
        if prior is None or prior.completion_record_id != completion.id:
            raise ServiceError(422, "Superseded attempt must belong to this completion.")
    max_number = db.scalar(
        select(func.max(AssessmentAttempt.attempt_number)).where(
            AssessmentAttempt.completion_record_id == completion.id,
            AssessmentAttempt.assessment_key == assessment_key,
        )
    )
    attempt = AssessmentAttempt(
        id=uuid4(),
        completion_record_id=completion.id,
        learner_id=completion.learner_id,
        assessment_key=assessment_key,
        attempt_number=int(max_number or 0) + 1,
        score=score,
        score_scale=score_scale,
        result_code=result_code,
        status=status,
        submitted_at=submitted_at,
        graded_at=graded_at,
        recorded_at=datetime.now(timezone.utc),
        recorded_by_user_id=actor_id,
        supersedes_attempt_id=supersedes_attempt_id,
    )
    db.add(attempt)
    record_event(
        db, event_type="assessment_attempt.created", actor_user_id=actor_id,
        actor_reference=str(actor_id), target_type="assessment_attempt",
        target_reference=str(attempt.id),
        event_data={"completion_id": str(completion.id), "attempt_number": attempt.attempt_number},
    )
    db.flush()
    return attempt
