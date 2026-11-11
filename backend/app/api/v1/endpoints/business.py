from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.core.errors import ServiceError
from app.core.roles import (
    AUDIT_READERS,
    COMPLETION_WRITERS,
    DATA_READERS,
    ISSUERS,
    LEARNER,
    MANAGERS,
    PLATFORM_ADMIN,
    SUPPORT,
)
from app.database.base import Base
from app.database.dependencies import get_db
from app.models.domain import (
    AssessmentAttempt,
    AuditEvent,
    CompletionRecord,
    Course,
    Credential,
    CredentialAward,
    CredentialRule,
    CredentialRuleVersion,
    CredentialScope,
    EligibilityDecision,
    EligibilityReason,
    Enrollment,
    Issuer,
    IssuerSigningKey,
    Learner,
    Revocation,
    Role,
    User,
    VerificationRequest,
)
from app.schemas.api import (
    AssessmentAttemptCreate,
    AssessmentAttemptResponse,
    AcademicAnalytics,
    AnalyticsBucket,
    AnalyticsOverview,
    AnalyticsRate,
    AuditEventResponse,
    CompletionCreate,
    CompletionResponse,
    CompletionStatusUpdate,
    CourseCreate,
    CourseResponse,
    CredentialResponse,
    EligibilityRequest,
    EligibilityResponse,
    EnrollmentCreate,
    EnrollmentResponse,
    IssuerCreate,
    IssuerResponse,
    IssuerUpdate,
    IssueRequest,
    LearnerCreate,
    LearnerResponse,
    LearnerUpdate,
    PaginatedResponse,
    PortableCredentialResponse,
    PortableVerificationRequest,
    ReportSummary,
    RevocationCreate,
    RevocationResponse,
    RuleCreate,
    RuleResponse,
    RuleVersionCreate,
    SigningKeyCreate,
    CourseUpdate,
    CredentialLifecycleAnalytics,
    DataQualityReport,
    DatasetCheck,
    DatasetRowCount,
    PerformanceReport,
    AnalyticsTimeBucket,
    VerificationAnalytics,
    VerificationResponse,
)
from app.services.audit import record_event
from app.services.credentials import (
    issue_credential,
    revoke_credential,
    verify_credential_id,
    verify_portable_payload,
)
from app.services.eligibility import evaluate_and_record
from app.services.management import (
    create_assessment_attempt,
    create_completion,
    create_course,
    create_enrollment,
    create_issuer,
    create_learner,
    create_rule,
    create_rule_version,
    register_signing_key,
    revoke_signing_key,
    update_course,
    update_issuer,
    update_learner,
    update_completion_status,
)

router = APIRouter()


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The requested change conflicts with an existing record or database constraint.",
        ) from exc


def _page(query: Any, db: Session, limit: int, offset: int) -> list[Any]:
    return db.scalars(query.limit(limit).offset(offset)).all()


def _credential_response(credential: Credential) -> dict[str, Any]:
    return {
        "id": credential.id,
        "credential_id": credential.credential_id,
        "learner_id": credential.learner_id,
        "issuer_id": credential.issuer_id,
        "rule_version_id": credential.rule_version_id,
        "issued_at": credential.issued_at,
        "payload_version": credential.payload_version,
        "sha256_digest": credential.sha256_digest.hex(),
        "signature_algorithm": credential.signature_algorithm,
        "signing_key_id": credential.signing_key_id,
        "replacement_of_credential_id": credential.replacement_of_credential_id,
    }


@router.get(
    "/learners",
    response_model=list[LearnerResponse],
    tags=["learners"],
    summary="List learners",
)
def list_learners(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[Learner]:
    return _page(select(Learner).order_by(Learner.learner_id), db, limit, offset)


@router.post(
    "/learners",
    response_model=LearnerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["learners"],
    summary="Create a learner",
)
def add_learner(
    payload: LearnerCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> Learner:
    try:
        learner = create_learner(
            db,
            learner_id=payload.learner_id,
            display_name=payload.display_name,
            user_id=payload.user_id,
            actor_id=actor.id,
        )
        _commit(db)
        return learner
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/learners/{learner_id}",
    response_model=LearnerResponse,
    tags=["learners"],
    summary="Retrieve a learner profile",
)
def get_learner(
    learner_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> Learner:
    learner = db.get(Learner, learner_id)
    if learner is None:
        raise HTTPException(404, "Learner was not found.")
    return learner


@router.patch(
    "/learners/{learner_id}",
    response_model=LearnerResponse,
    tags=["learners"],
    summary="Update a learner profile without changing its external identifier",
)
def patch_learner(
    learner_id: UUID,
    payload: LearnerUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> Learner:
    try:
        learner = update_learner(
            db, learner_id=learner_id,
            changes=payload.model_dump(exclude_unset=True), actor_id=actor.id,
        )
        _commit(db)
        return learner
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/learners/me/credentials",
    response_model=list[CredentialResponse],
    tags=["learners"],
    summary="List credentials belonging to the authenticated learner",
)
def own_credentials(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(LEARNER)),
) -> list[Credential]:
    learner = db.scalar(select(Learner).where(Learner.user_id == actor.id))
    if learner is None:
        raise HTTPException(404, "No learner profile is linked to this account.")
    credentials = db.scalars(
        select(Credential)
        .where(Credential.learner_id == learner.id)
        .order_by(Credential.issued_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [_credential_response(credential) for credential in credentials]


@router.get(
    "/courses",
    response_model=list[CourseResponse],
    tags=["courses"],
    summary="List courses",
)
def list_courses(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[Course]:
    return _page(select(Course).order_by(Course.course_code), db, limit, offset)


@router.post(
    "/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["courses"],
    summary="Create a course",
)
def add_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> Course:
    try:
        course = create_course(db, data=payload.model_dump(), actor_id=actor.id)
        _commit(db)
        return course
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch(
    "/courses/{course_id}",
    response_model=CourseResponse,
    tags=["courses"],
    summary="Update catalog metadata while retaining the course record",
)
def patch_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> Course:
    try:
        course = update_course(
            db, course_id=course_id,
            changes=payload.model_dump(exclude_unset=True), actor_id=actor.id,
        )
        _commit(db)
        return course
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/issuers",
    response_model=list[IssuerResponse],
    tags=["issuers"],
    summary="List credential issuers",
)
def list_issuers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[Issuer]:
    return _page(select(Issuer).order_by(Issuer.issuer_code), db, limit, offset)


@router.post(
    "/issuers",
    response_model=IssuerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["issuers"],
    summary="Create an issuer",
)
def add_issuer(
    payload: IssuerCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> Issuer:
    try:
        issuer = create_issuer(
            db, issuer_code=payload.issuer_code, name=payload.name, actor_id=actor.id
        )
        _commit(db)
        return issuer
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch(
    "/issuers/{issuer_code}",
    response_model=IssuerResponse,
    tags=["issuers"],
    summary="Update an issuer profile with an audit snapshot",
)
def patch_issuer(
    issuer_code: str,
    payload: IssuerUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> Issuer:
    try:
        issuer = update_issuer(
            db,
            issuer_code=issuer_code,
            name=payload.name,
            status=payload.status,
            actor_id=actor.id,
        )
        _commit(db)
        return issuer
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post(
    "/issuers/{issuer_code}/signing-keys",
    status_code=status.HTTP_201_CREATED,
    tags=["issuers"],
    summary="Register an issuer public signing key",
    description="Private key material is never accepted by this endpoint.",
)
def add_signing_key(
    issuer_code: str,
    payload: SigningKeyCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(PLATFORM_ADMIN)),
) -> dict[str, Any]:
    try:
        key = register_signing_key(
            db,
            issuer_code=issuer_code,
            key_id=payload.key_id,
            public_key_base64=payload.public_key_base64,
            algorithm=payload.algorithm,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            actor_id=actor.id,
            supersedes_key_id=payload.supersedes_key_id,
        )
        _commit(db)
        return {
            "id": str(key.id),
            "issuer_code": issuer_code,
            "key_id": key.key_id,
            "algorithm": key.algorithm,
            "fingerprint_sha256": key.fingerprint.hex(),
            "status": key.status,
        }
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post(
    "/issuers/{issuer_code}/signing-keys/{key_id}/revoke",
    tags=["issuers"],
    summary="Revoke an issuer public key while preserving its historical record",
)
def remove_signing_key_trust(
    issuer_code: str,
    key_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(PLATFORM_ADMIN)),
) -> dict[str, str]:
    try:
        key = revoke_signing_key(
            db, issuer_code=issuer_code, key_id=key_id, actor_id=actor.id
        )
        _commit(db)
        return {"issuer_code": issuer_code, "key_id": key.key_id, "status": key.status}
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/credential-rules",
    response_model=list[RuleResponse],
    tags=["credential-rules"],
    summary="List credential rule versions",
)
def list_rules(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(CredentialRule, CredentialRuleVersion)
        .join(CredentialRuleVersion, CredentialRuleVersion.rule_id == CredentialRule.id)
        .order_by(CredentialRule.rule_code, CredentialRuleVersion.version_number.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    output = []
    for rule, version in rows:
        from app.models.domain import CredentialScope

        scope = db.get(CredentialScope, version.credential_scope_id)
        course_id = scope.course_id if scope else None
        output.append(
            {
                "id": version.id,
                "rule_id": rule.id,
                "version_number": version.version_number,
                "credential_scope_id": version.credential_scope_id,
                "course_id": course_id,
                "rule_code": rule.rule_code,
                "name": rule.name,
                "criteria": version.criteria,
                "attempt_selection_policy": version.attempt_selection_policy,
                "effective_from": version.effective_from,
                "effective_to": version.effective_to,
                "status": version.status,
            }
        )
    return output


@router.post(
    "/credential-rules",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["credential-rules"],
    summary="Create a credential rule and its first immutable version",
)
def add_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> dict[str, Any]:
    try:
        rule, version, scope = create_rule(
            db,
            rule_code=payload.rule_code,
            name=payload.name,
            description=payload.description,
            course_id=payload.course_id,
            criteria=payload.criteria,
            attempt_selection_policy=payload.attempt_selection_policy,
            effective_from=payload.effective_from,
            actor_id=actor.id,
        )
        _commit(db)
        return {
            "id": version.id,
            "rule_id": rule.id,
            "version_number": version.version_number,
            "credential_scope_id": scope.id,
            "course_id": payload.course_id,
            "rule_code": rule.rule_code,
            "name": rule.name,
            "criteria": version.criteria,
            "attempt_selection_policy": version.attempt_selection_policy,
            "effective_from": version.effective_from,
            "effective_to": version.effective_to,
            "status": version.status,
        }
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post(
    "/credential-rules/{rule_code}/versions",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["credential-rules"],
    summary="Create a new immutable version of an existing credential rule",
)
def add_rule_version(
    rule_code: str,
    payload: RuleVersionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGERS)),
) -> dict[str, Any]:
    try:
        rule, version, scope = create_rule_version(
            db,
            rule_code=rule_code,
            course_id=payload.course_id,
            criteria=payload.criteria,
            attempt_selection_policy=payload.attempt_selection_policy,
            effective_from=payload.effective_from,
            actor_id=actor.id,
        )
        _commit(db)
        return {
            "id": version.id,
            "rule_id": rule.id,
            "version_number": version.version_number,
            "credential_scope_id": scope.id,
            "course_id": payload.course_id,
            "rule_code": rule.rule_code,
            "name": rule.name,
            "criteria": version.criteria,
            "attempt_selection_policy": version.attempt_selection_policy,
            "effective_from": version.effective_from,
            "effective_to": version.effective_to,
            "status": version.status,
        }
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/enrollments",
    response_model=list[EnrollmentResponse],
    tags=["enrollments"],
    summary="List enrollments",
)
def list_enrollments(
    learner_id: UUID | None = None,
    course_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[Enrollment]:
    query = select(Enrollment)
    if learner_id:
        query = query.where(Enrollment.learner_id == learner_id)
    if course_id:
        query = query.where(Enrollment.course_id == course_id)
    return _page(query.order_by(Enrollment.enrolled_at.desc()), db, limit, offset)


@router.post(
    "/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["enrollments"],
    summary="Enroll a learner in a course",
)
def add_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*COMPLETION_WRITERS)),
) -> Enrollment:
    try:
        enrollment = create_enrollment(
            db,
            learner_id=payload.learner_id,
            course_id=payload.course_id,
            effective_from=payload.effective_from,
            actor_id=actor.id,
        )
        _commit(db)
        return enrollment
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/completions",
    response_model=list[CompletionResponse],
    tags=["completions"],
    summary="List course completion records",
)
def list_completions(
    learner_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[CompletionRecord]:
    query = select(CompletionRecord)
    if learner_id:
        query = query.where(CompletionRecord.learner_id == learner_id)
    return _page(query.order_by(CompletionRecord.recorded_at.desc()), db, limit, offset)


@router.post(
    "/completions",
    response_model=CompletionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["completions"],
    summary="Record course completion status",
)
def add_completion(
    payload: CompletionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*COMPLETION_WRITERS)),
) -> CompletionRecord:
    try:
        completion = create_completion(
            db,
            enrollment_id=payload.enrollment_id,
            status=payload.status,
            started_at=payload.started_at,
            completed_at=payload.completed_at,
            source_reference=payload.source_reference,
            actor_id=actor.id,
        )
        _commit(db)
        return completion
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.patch(
    "/completions/{completion_id}",
    response_model=CompletionResponse,
    tags=["completions"],
    summary="Update a completion status while retaining assessment history",
)
def patch_completion(
    completion_id: UUID,
    payload: CompletionStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*COMPLETION_WRITERS)),
) -> CompletionRecord:
    try:
        completion = update_completion_status(
            db,
            completion_id=completion_id,
            status=payload.status,
            completed_at=payload.completed_at,
            actor_id=actor.id,
        )
        _commit(db)
        return completion
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/assessment-attempts",
    response_model=list[AssessmentAttemptResponse],
    tags=["assessment-attempts"],
    summary="List assessment attempts without collapsing retry history",
)
def list_attempts(
    completion_record_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[AssessmentAttempt]:
    query = select(AssessmentAttempt)
    if completion_record_id:
        query = query.where(
            AssessmentAttempt.completion_record_id == completion_record_id
        )
    return _page(query.order_by(AssessmentAttempt.submitted_at.desc()), db, limit, offset)


@router.post(
    "/assessment-attempts",
    response_model=AssessmentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["assessment-attempts"],
    summary="Record a new assessment attempt",
)
def add_attempt(
    payload: AssessmentAttemptCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*COMPLETION_WRITERS)),
) -> AssessmentAttempt:
    try:
        attempt = create_assessment_attempt(
            db,
            completion_record_id=payload.completion_record_id,
            assessment_key=payload.assessment_key,
            score=payload.score,
            score_scale=payload.score_scale,
            result_code=payload.result_code,
            status=payload.status,
            submitted_at=payload.submitted_at,
            graded_at=payload.graded_at,
            supersedes_attempt_id=payload.supersedes_attempt_id,
            actor_id=actor.id,
        )
        _commit(db)
        return attempt
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post(
    "/eligibility/evaluate",
    response_model=EligibilityResponse,
    tags=["eligibility"],
    summary="Evaluate current evidence and persist an immutable eligibility decision",
)
def evaluate_eligibility(
    payload: EligibilityRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*COMPLETION_WRITERS)),
) -> dict[str, Any]:
    learner = db.get(Learner, payload.learner_id)
    if learner is None or learner.archived_at is not None:
        raise HTTPException(404, "Active learner was not found.")
    try:
        decision, reason_codes, rule_code = evaluate_and_record(
            db,
            learner=learner,
            rule_code=payload.rule_code,
            evaluator_user_id=actor.id,
            evaluator_reference=str(actor.id),
        )
        record_event(
            db,
            event_type="eligibility.evaluated",
            actor_user_id=actor.id,
            actor_reference=str(actor.id),
            target_type="learner",
            target_reference=learner.learner_id,
            event_data={"decision_id": str(decision.id), "outcome": decision.outcome},
        )
        _commit(db)
        return {
            "decision_id": decision.id,
            "learner_id": learner.id,
            "rule_code": rule_code,
            "rule_version_id": decision.rule_version_id,
            "outcome": decision.outcome,
            "reason_codes": reason_codes,
            "evaluated_at": decision.evaluated_at,
        }
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/credentials",
    response_model=list[CredentialResponse],
    tags=["credentials"],
    summary="List credentials",
)
def list_credentials(
    learner_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> list[dict[str, Any]]:
    query = select(Credential)
    if learner_id:
        query = query.where(Credential.learner_id == learner_id)
    credentials = _page(query.order_by(Credential.issued_at.desc()), db, limit, offset)
    return [_credential_response(credential) for credential in credentials]


@router.get(
    "/credentials/{credential_id}",
    response_model=CredentialResponse,
    tags=["credentials"],
    summary="Retrieve credential metadata without exposing assessment evidence",
)
def get_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> dict[str, Any]:
    credential = db.scalar(
        select(Credential).where(Credential.credential_id == credential_id)
    )
    if credential is None:
        raise HTTPException(404, "Credential was not found.")
    return _credential_response(credential)


@router.post(
    "/credentials/issue",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["credentials"],
    summary="Evaluate current evidence and issue a signed credential atomically",
)
def issue(
    payload: IssueRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*ISSUERS)),
) -> dict[str, Any]:
    try:
        credential = issue_credential(
            db,
            learner_id=payload.learner_id,
            rule_code=payload.rule_code,
            actor_id=actor.id,
            actor_reference=str(actor.id),
            idempotency_key=idempotency_key,
        )
        _commit(db)
        return _credential_response(credential)
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/credentials/{credential_id}/portable",
    response_model=PortableCredentialResponse,
    tags=["credentials"],
    summary="Return the signed portable credential payload to an authorized caller",
)
def portable_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*DATA_READERS)),
) -> dict[str, Any]:
    credential = db.scalar(
        select(Credential).where(Credential.credential_id == credential_id)
    )
    if credential is None:
        raise HTTPException(404, "Credential was not found.")
    try:
        payload = json.loads(credential.canonical_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Stored credential payload is malformed.") from exc
    return {
        "payload": payload,
        "signature_base64": base64.b64encode(credential.signature).decode("ascii"),
    }


@router.get(
    "/credentials/{credential_id}/history",
    response_model=list[AuditEventResponse],
    tags=["credentials"],
    summary="Read credential issuance, verification, and revocation history",
)
def credential_history(
    credential_id: str,
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> list[AuditEvent]:
    credential = db.scalar(
        select(Credential).where(Credential.credential_id == credential_id)
    )
    if credential is None:
        raise HTTPException(404, "Credential was not found.")
    return db.scalars(
        select(AuditEvent)
        .where(AuditEvent.target_reference == credential_id)
        .order_by(AuditEvent.occurred_at)
        .limit(limit)
    ).all()


@router.post(
    "/verification/credential-id",
    response_model=VerificationResponse,
    tags=["verification"],
    summary="Verify a credential ID against the authoritative credential registry",
)
def verify_id(
    credential_id: str = Query(min_length=1, max_length=15),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = verify_credential_id(db, credential_id, "anonymous-verifier")
    _commit(db)
    return result


@router.post(
    "/verification/portable",
    response_model=VerificationResponse,
    tags=["verification"],
    summary="Verify a portable signed payload using the issuer public-key registry",
)
def verify_portable(
    payload: PortableVerificationRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = verify_portable_payload(
        db, payload.payload, payload.signature_base64, "anonymous-verifier"
    )
    _commit(db)
    return result


@router.post(
    "/revocations/{credential_id}",
    response_model=RevocationResponse,
    tags=["revocations"],
    summary="Revoke a credential without deleting its record",
)
def revoke(
    credential_id: str,
    payload: RevocationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*ISSUERS)),
) -> Revocation:
    try:
        revocation = revoke_credential(
            db,
            credential_id=credential_id,
            reason_code=payload.reason_code,
            reason_detail=payload.reason_detail,
            actor_id=actor.id,
            actor_reference=str(actor.id),
        )
        _commit(db)
        return revocation
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get(
    "/revocations",
    response_model=list[RevocationResponse],
    tags=["revocations"],
    summary="List immutable revocation records",
)
def list_revocations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> list[Revocation]:
    return _page(
        select(Revocation).order_by(Revocation.recorded_at.desc()), db, limit, offset
    )


@router.get(
    "/verification/requests",
    tags=["verification"],
    summary="Read verification request history without learner details",
)
def list_verification_requests(
    outcome: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> list[dict[str, Any]]:
    query = select(VerificationRequest)
    if outcome:
        query = query.where(VerificationRequest.overall_result == outcome)
    records = _page(
        query.order_by(VerificationRequest.requested_at.desc()), db, limit, offset
    )
    return [
        {
            "verification_id": row.verification_id,
            "mode": row.mode,
            "submitted_credential_id": row.submitted_credential_id,
            "integrity_result": row.integrity_result,
            "issuer_trust_result": row.issuer_trust_result,
            "lifecycle_result": row.lifecycle_result,
            "overall_result": row.overall_result,
            "requested_at": row.requested_at,
            "completed_at": row.completed_at,
        }
        for row in records
    ]


@router.get(
    "/audit",
    response_model=list[AuditEventResponse],
    tags=["audit"],
    summary="Read append-only audit events",
)
def list_audit(
    target_reference: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> list[AuditEvent]:
    query = select(AuditEvent)
    if target_reference:
        query = query.where(AuditEvent.target_reference == target_reference)
    return _page(query.order_by(AuditEvent.occurred_at.desc()), db, limit, offset)


@router.get(
    "/reports/summary",
    response_model=ReportSummary,
    tags=["reports"],
    summary="Summarize credential, revocation, and verification volumes",
)
def report_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> ReportSummary:
    total_credentials = db.scalar(select(func.count()).select_from(Credential)) or 0
    total_revocations = db.scalar(select(func.count()).select_from(Revocation)) or 0
    total_verifications = (
        db.scalar(select(func.count()).select_from(VerificationRequest)) or 0
    )
    revoked_ids = select(Revocation.credential_id).where(
        Revocation.effective_at <= datetime.now(timezone.utc)
    )
    revoked_credentials = db.scalar(
        select(func.count()).select_from(Credential).where(Credential.id.in_(revoked_ids))
    ) or 0
    return ReportSummary(
        total_credentials=total_credentials,
        total_revocations=total_revocations,
        total_verifications=total_verifications,
        credentials_by_status={
            "revoked": revoked_credentials,
            "active": total_credentials - revoked_credentials,
        },
    )


@router.get(
    "/reports/issuance",
    tags=["reports"],
    summary="Count credential issuance by UTC year",
)
def issuance_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> dict[str, Any]:
    rows = db.execute(
        select(
            func.date_part("year", Credential.issued_at).label("year"),
            func.count().label("count"),
        ).group_by("year").order_by("year")
    ).all()
    return {"by_year": {str(int(row.year)): row.count for row in rows}}


@router.get(
    "/reports/revocations",
    tags=["reports"],
    summary="Summarize revocations by reason code",
)
def revocation_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> dict[str, Any]:
    rows = db.execute(
        select(Revocation.reason_code, func.count())
        .group_by(Revocation.reason_code)
        .order_by(Revocation.reason_code)
    ).all()
    return {"by_reason": {row[0]: row[1] for row in rows}}


@router.get(
    "/reports/verification",
    tags=["reports"],
    summary="Summarize verification outcomes and modes",
)
def verification_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> dict[str, Any]:
    rows = db.execute(
        select(
            VerificationRequest.mode,
            VerificationRequest.overall_result,
            func.count(),
        )
        .group_by(VerificationRequest.mode, VerificationRequest.overall_result)
        .order_by(VerificationRequest.mode, VerificationRequest.overall_result)
    ).all()
    return {
        "groups": [
            {"mode": row[0], "outcome": row[1], "count": row[2]} for row in rows
        ]
    }


def _count(db: Session, statement: Any) -> int:
    return int(db.scalar(statement) or 0)


def _rate(numerator: int, denominator: int, definition: str) -> AnalyticsRate:
    return AnalyticsRate(
        percent=round(numerator * 100 / denominator, 2) if denominator else None,
        numerator=numerator,
        denominator=denominator,
        definition=definition,
    )


def _date_bounds(
    date_from: date | None, date_to: date | None
) -> tuple[datetime | None, datetime | None]:
    if date_from and date_to and date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to must be on or after date_from.")
    if date_from and date_to and (date_to - date_from).days > 3660:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 10 years.")
    start = (
        datetime.combine(date_from, time.min, tzinfo=timezone.utc) if date_from else None
    )
    end = (
        datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        if date_to
        else None
    )
    return start, end


def _within_dates(
    column: Any, start: datetime | None, end: datetime | None
) -> list[Any]:
    conditions = []
    if start is not None:
        conditions.append(column >= start)
    if end is not None:
        conditions.append(column < end)
    return conditions


def _month_bucket(column: Any) -> Any:
    utc_value = column.op("AT TIME ZONE")("UTC")
    return func.to_char(func.date_trunc("month", utc_value), "YYYY-MM")


@router.get(
    "/reports/overview",
    response_model=AnalyticsOverview,
    tags=["reports"],
    summary="Return database-backed academic and credential lifecycle KPIs",
)
def analytics_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> AnalyticsOverview:
    as_of = datetime.now(timezone.utc)
    learners = _count(db, select(func.count()).select_from(Learner))
    courses = _count(db, select(func.count()).select_from(Course))
    enrollments = _count(db, select(func.count()).select_from(Enrollment))
    completed = _count(
        db,
        select(func.count())
        .select_from(CompletionRecord)
        .where(CompletionRecord.status == "completed"),
    )
    eligible_learners = _count(
        db,
        select(func.count(func.distinct(EligibilityDecision.learner_id)))
        .select_from(EligibilityDecision)
        .where(EligibilityDecision.outcome == "eligible"),
    )
    eligible_slots = (
        select(
            EligibilityDecision.learner_id,
            EligibilityDecision.credential_scope_id,
        )
        .where(EligibilityDecision.outcome == "eligible")
        .distinct()
        .subquery()
    )
    issued_slots = (
        select(Credential.learner_id, Credential.credential_scope_id)
        .join(
            EligibilityDecision,
            EligibilityDecision.id == Credential.eligibility_decision_id,
        )
        .where(EligibilityDecision.outcome == "eligible")
        .distinct()
        .subquery()
    )
    issuance_numerator = _count(
        db,
        select(func.count())
        .select_from(
            issued_slots.join(
                eligible_slots,
                and_(
                    issued_slots.c.learner_id == eligible_slots.c.learner_id,
                    issued_slots.c.credential_scope_id
                    == eligible_slots.c.credential_scope_id,
                ),
            )
        ),
    )
    total_credentials = _count(db, select(func.count()).select_from(Credential))
    revoked_ids = select(Revocation.credential_id).where(
        Revocation.effective_at <= as_of
    )
    revoked = _count(
        db,
        select(func.count())
        .select_from(Credential)
        .where(Credential.id.in_(revoked_ids)),
    )
    verification_total = _count(
        db, select(func.count()).select_from(VerificationRequest)
    )
    valid_verifications = _count(
        db,
        select(func.count())
        .select_from(VerificationRequest)
        .where(func.upper(VerificationRequest.overall_result) == "VALID"),
    )
    completed_enrollments = _count(
        db,
        select(func.count(func.distinct(CompletionRecord.enrollment_id)))
        .select_from(CompletionRecord)
        .where(
            CompletionRecord.status == "completed",
            CompletionRecord.enrollment_id.is_not(None),
        ),
    )
    return AnalyticsOverview(
        as_of=as_of,
        total_learners=learners,
        total_courses=courses,
        total_enrollments=enrollments,
        total_completed_records=completed,
        total_eligible_learners=eligible_learners,
        total_credentials_issued=total_credentials,
        total_revoked_credentials=revoked,
        total_verification_requests=verification_total,
        credential_issuance_rate=_rate(
            issuance_numerator,
            _count(
                db,
                select(func.count()).select_from(eligible_slots),
            ),
            "Distinct issued learner/course credential slots divided by all distinct "
            "learner/course slots with an eligible decision (all time).",
        ),
        revocation_rate=_rate(
            revoked,
            total_credentials,
            "Credentials with a revocation effective as of the report timestamp "
            "divided by all issued credentials (all time).",
        ),
        verification_success_rate=_rate(
            valid_verifications,
            verification_total,
            "Verification requests whose overall result is VALID divided by all "
            "verification requests (all time).",
        ),
        completion_rate=_rate(
            completed_enrollments,
            enrollments,
            "Distinct enrollments with a completed completion record divided by all "
            "enrollments (all time).",
        ),
    )


@router.get(
    "/reports/credential-lifecycle",
    response_model=CredentialLifecycleAnalytics,
    tags=["reports"],
    summary="Aggregate credential issuance, revocation, and eligibility trends",
)
def credential_lifecycle_analytics(
    date_from: date | None = None,
    date_to: date | None = None,
    course_id: UUID | None = None,
    credential_status: str | None = Query(
        None, pattern="^(active|revoked)$"
    ),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> CredentialLifecycleAnalytics:
    start, end = _date_bounds(date_from, date_to)
    as_of = datetime.now(timezone.utc)
    credential_query = select(Credential).where(
        *_within_dates(Credential.issued_at, start, end)
    )
    if course_id is not None:
        credential_query = credential_query.join(
            CredentialScope,
            CredentialScope.id == Credential.credential_scope_id,
        ).where(CredentialScope.course_id == course_id)
    effective_revocations = select(Revocation.credential_id).where(
        Revocation.effective_at <= as_of
    )
    if credential_status == "active":
        credential_query = credential_query.where(
            Credential.id.not_in(effective_revocations)
        )
    elif credential_status == "revoked":
        credential_query = credential_query.where(
            Credential.id.in_(effective_revocations)
        )
    credential_rows = credential_query.subquery()
    issued_count = _count(
        db, select(func.count()).select_from(credential_rows)
    )
    revoked_count = _count(
        db,
        select(func.count())
        .select_from(credential_rows)
        .where(credential_rows.c.id.in_(effective_revocations)),
    )
    status_counts = []
    for key, count in (
        ("active", issued_count - revoked_count),
        ("revoked", revoked_count),
    ):
        if count:
            status_counts.append(AnalyticsBucket(key=key, count=count))

    issue_bucket = _month_bucket(credential_rows.c.issued_at)
    issuance_rows = db.execute(
        select(issue_bucket, func.count())
        .select_from(credential_rows)
        .group_by(issue_bucket)
        .order_by(issue_bucket)
    ).all()
    credential_ids = select(credential_rows.c.id)
    revocation_conditions = [
        Revocation.credential_id.in_(credential_ids),
        *_within_dates(Revocation.effective_at, start, end),
    ]
    revocation_bucket = _month_bucket(Revocation.effective_at)
    revocation_rows = db.execute(
        select(revocation_bucket, func.count())
        .where(*revocation_conditions)
        .group_by(revocation_bucket)
        .order_by(revocation_bucket)
    ).all()

    eligibility_query = select(
        EligibilityDecision.outcome, func.count()
    ).select_from(EligibilityDecision)
    eligibility_conditions = _within_dates(EligibilityDecision.evaluated_at, start, end)
    if course_id is not None:
        eligibility_query = eligibility_query.join(
            CredentialScope,
            CredentialScope.id == EligibilityDecision.credential_scope_id,
        ).where(CredentialScope.course_id == course_id)
    eligibility_rows = db.execute(
        eligibility_query.where(*eligibility_conditions)
        .group_by(EligibilityDecision.outcome)
        .order_by(EligibilityDecision.outcome)
    ).all()
    return CredentialLifecycleAnalytics(
        as_of=as_of,
        credential_status=[
            AnalyticsBucket(key=key, count=count) for key, count in status_counts
        ],
        issuance_over_time=[
            AnalyticsTimeBucket(period=str(row[0]), count=int(row[1]))
            for row in issuance_rows
        ],
        revocations_over_time=[
            AnalyticsTimeBucket(period=str(row[0]), count=int(row[1]))
            for row in revocation_rows
        ],
        eligibility_outcomes=[
            AnalyticsBucket(key=str(row[0]), count=int(row[1]))
            for row in eligibility_rows
        ],
    )


@router.get(
    "/reports/verification-analytics",
    response_model=VerificationAnalytics,
    tags=["reports"],
    summary="Aggregate verification results and trends",
)
def verification_analytics(
    date_from: date | None = None,
    date_to: date | None = None,
    outcome: str | None = Query(None, min_length=1, max_length=32),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> VerificationAnalytics:
    start, end = _date_bounds(date_from, date_to)
    conditions = _within_dates(VerificationRequest.requested_at, start, end)
    if outcome is not None:
        conditions.append(VerificationRequest.overall_result == outcome)
    grouped = (
        select(
            VerificationRequest.overall_result,
            func.count(),
        )
        .where(*conditions)
        .group_by(VerificationRequest.overall_result)
        .order_by(VerificationRequest.overall_result)
    )
    outcome_rows = db.execute(grouped).all()
    mode_rows = db.execute(
        select(VerificationRequest.mode, func.count())
        .where(*conditions)
        .group_by(VerificationRequest.mode)
        .order_by(VerificationRequest.mode)
    ).all()
    verification_bucket = _month_bucket(VerificationRequest.requested_at)
    time_rows = db.execute(
        select(
            verification_bucket,
            VerificationRequest.overall_result,
            func.count(),
        )
        .where(*conditions)
        .group_by(verification_bucket, VerificationRequest.overall_result)
        .order_by(verification_bucket, VerificationRequest.overall_result)
    ).all()
    total = sum(int(row[1]) for row in outcome_rows)
    return VerificationAnalytics(
        as_of=datetime.now(timezone.utc),
        total_requests=total,
        outcome_counts=[
            AnalyticsBucket(key=str(row[0]), count=int(row[1]))
            for row in outcome_rows
        ],
        mode_counts=[
            AnalyticsBucket(key=str(row[0]), count=int(row[1])) for row in mode_rows
        ],
        outcomes_over_time=[
            AnalyticsTimeBucket(
                period=str(row[0]), outcome=str(row[1]), count=int(row[2])
            )
            for row in time_rows
        ],
    )


@router.get(
    "/reports/academic-analytics",
    response_model=AcademicAnalytics,
    tags=["reports"],
    summary="Aggregate enrollments, completions, assessment scores, and eligibility",
)
def academic_analytics(
    date_from: date | None = None,
    date_to: date | None = None,
    course_id: UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> AcademicAnalytics:
    start, end = _date_bounds(date_from, date_to)
    enrollment_counts = (
        select(
            Enrollment.course_id.label("course_id"),
            func.count(func.distinct(Enrollment.learner_id)).label("learner_count"),
        )
        .where(*_within_dates(Enrollment.enrolled_at, start, end))
        .group_by(Enrollment.course_id)
        .subquery()
    )
    completion_counts = (
        select(
            CompletionRecord.course_id.label("course_id"),
            func.sum(
                case((CompletionRecord.status == "completed", 1), else_=0)
            ).label("completed_count"),
        )
        .where(*_within_dates(CompletionRecord.recorded_at, start, end))
        .group_by(CompletionRecord.course_id)
        .subquery()
    )
    courses_query = (
        select(
            Course.id,
            Course.course_code,
            Course.title,
            func.coalesce(enrollment_counts.c.learner_count, 0).label(
                "enrolled_learners"
            ),
            func.coalesce(completion_counts.c.completed_count, 0).label(
                "completed_records"
            ),
        )
        .outerjoin(enrollment_counts, enrollment_counts.c.course_id == Course.id)
        .outerjoin(completion_counts, completion_counts.c.course_id == Course.id)
    )
    if course_id is not None:
        courses_query = courses_query.where(Course.id == course_id)
    course_rows = db.execute(
        courses_query.order_by(
            func.coalesce(enrollment_counts.c.learner_count, 0).desc(),
            Course.course_code,
        ).limit(limit)
    ).all()

    score = AssessmentAttempt.score
    score_range = case(
        (score < 0, "below 0"),
        (score < 60, "0-59"),
        (score < 70, "60-69"),
        (score < 80, "70-79"),
        (score < 90, "80-89"),
        (score <= 100, "90-100"),
        else_="over 100",
    )
    score_order = case(
        (score < 0, 0),
        (score < 60, 1),
        (score < 70, 2),
        (score < 80, 3),
        (score < 90, 4),
        (score <= 100, 5),
        else_=6,
    )
    score_query = select(
        AssessmentAttempt.score_scale,
        score_range.label("score_range"),
        func.count(),
    ).where(
        AssessmentAttempt.score.is_not(None),
        AssessmentAttempt.status == "graded",
        *_within_dates(AssessmentAttempt.graded_at, start, end),
    )
    if course_id is not None:
        score_query = score_query.join(
            CompletionRecord,
            CompletionRecord.id == AssessmentAttempt.completion_record_id,
        ).where(CompletionRecord.course_id == course_id)
    score_rows = db.execute(
        score_query.group_by(AssessmentAttempt.score_scale, score_range, score_order)
        .order_by(AssessmentAttempt.score_scale, score_order)
    ).all()

    eligibility_query = select(
        EligibilityDecision.outcome, func.count()
    ).select_from(EligibilityDecision)
    if course_id is not None:
        eligibility_query = eligibility_query.join(
            CredentialScope,
            CredentialScope.id == EligibilityDecision.credential_scope_id,
        ).where(CredentialScope.course_id == course_id)
    eligibility_rows = db.execute(
        eligibility_query.where(
            *_within_dates(EligibilityDecision.evaluated_at, start, end)
        )
        .group_by(EligibilityDecision.outcome)
        .order_by(EligibilityDecision.outcome)
    ).all()
    return AcademicAnalytics(
        as_of=datetime.now(timezone.utc),
        course_distribution=[
            {
                "course_id": row[0],
                "course_code": row[1],
                "title": row[2],
                "enrolled_learners": int(row[3]),
                "completed_records": int(row[4]),
            }
            for row in course_rows
        ],
        assessment_score_distribution=[
            {
                "score_scale": str(row[0] or "unspecified"),
                "range": str(row[1]),
                "count": int(row[2]),
            }
            for row in score_rows
        ],
        eligibility_outcomes=[
            AnalyticsBucket(key=str(row[0]), count=int(row[1]))
            for row in eligibility_rows
        ],
    )


def _read_report(path: str | None, label: str) -> dict[str, Any] | None:
    if not path:
        return None
    report_path = Path(path)
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503, detail=f"Configured {label} report is unavailable."
        ) from exc


def _report_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@router.get(
    "/reports/data-quality",
    response_model=DataQualityReport,
    tags=["reports"],
    summary="Compare live database counts with imported dataset and validation reports",
)
def data_quality_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> DataQualityReport:
    manifest = _read_report(settings.full_dataset_manifest_path, "dataset manifest")
    import_report = _read_report(
        settings.full_dataset_import_report_path, "dataset import"
    )
    validation_report = _read_report(
        settings.full_dataset_validation_report_path, "dataset validation"
    )
    verification_report = _read_report(
        settings.full_dataset_verification_report_path, "database verification"
    )
    if manifest is None:
        return DataQualityReport(
            status="not_configured",
            seed=None,
            generation_timestamp=None,
            dataset_sha256=None,
            total_expected_rows=None,
            total_imported_rows=None,
            missing_reference_count=None,
            last_successful_validation_at=None,
            row_counts=[],
            checks=[],
            warnings=[
                "Configure the full-dataset report paths to show import and validation status."
            ],
        )
    if import_report is None or validation_report is None or verification_report is None:
        return DataQualityReport(
            status="not_configured",
            seed=int(manifest.get("seed", 0)) or None,
            generation_timestamp=_report_datetime(manifest.get("generated_at")),
            dataset_sha256=manifest.get("seed_data_sha256"),
            total_expected_rows=sum(manifest.get("row_counts", {}).values()),
            total_imported_rows=None,
            missing_reference_count=None,
            last_successful_validation_at=None,
            row_counts=[],
            checks=[],
            warnings=[
                "Import, database-verification, and validation report paths must all be configured."
            ],
        )

    expected_counts = manifest.get("row_counts", {})
    imported_counts = import_report.get("imported_row_counts", {})
    validation_counts = validation_report.get("actual_row_counts", {})
    excluded = {"users", "roles", "user_roles", "idempotency_records"}
    table_names = sorted(set(expected_counts) - excluded)
    current_columns = [
        select(func.count()).select_from(Base.metadata.tables[name]).scalar_subquery().label(name)
        for name in table_names
        if name in Base.metadata.tables
    ]
    current_values = db.execute(select(*current_columns)).mappings().one() if current_columns else {}
    row_counts = []
    for name in table_names:
        expected = int(expected_counts[name])
        imported = imported_counts.get(name)
        current = int(current_values[name])
        imported_value = int(imported) if imported is not None else None
        row_counts.append(
            DatasetRowCount(
                table=name,
                expected=expected,
                imported=imported_value,
                current=current,
                matches=(
                    imported_value == expected
                    and current >= imported_value
                    if imported_value is not None
                    else None
                ),
            )
        )

    manifest_counts_match = all(row.matches is True for row in row_counts)
    validations = validation_report.get("checks", [])
    validation_checks = [
        DatasetCheck(
            name=str(item.get("name", "unknown")),
            passed=bool(item.get("passed")),
            details=item.get("details"),
        )
        for item in validations
    ]
    checks = [
        DatasetCheck(
            name="imported_counts_match_manifest_and_live_rows_are_retained",
            passed=manifest_counts_match,
            details=(
                "The import snapshot is compared with the manifest; live counts may grow "
                "as application activity adds records. Authentication/bootstrap tables "
                "are excluded."
            ),
        ),
        DatasetCheck(
            name="import_completed",
            passed=import_report.get("status") == "passed",
            details=str(import_report.get("status", "unknown")),
        ),
        DatasetCheck(
            name="database_verification_passed",
            passed=verification_report.get("status") == "passed",
            details=str(verification_report.get("status", "unknown")),
        ),
        *validation_checks,
    ]
    warnings = []
    warnings.extend(import_report.get("source_file_checksum_mismatches", []))
    warnings.extend(verification_report.get("source_file_checksum_mismatches", []))
    status_value = (
        "passed"
        if import_report.get("status") == "passed"
        and verification_report.get("status") == "passed"
        and validation_report.get("status") == "passed"
        and manifest_counts_match
        else "failed"
    )
    last_validation = (
        _report_datetime(validation_report.get("completed_at"))
        if validation_report.get("status") == "passed"
        else None
    )
    return DataQualityReport(
        status=status_value,
        seed=manifest.get("seed"),
        generation_timestamp=_report_datetime(manifest.get("generated_at")),
        dataset_sha256=manifest.get("seed_data_sha256"),
        total_expected_rows=sum(expected_counts.get(name, 0) for name in table_names),
        total_imported_rows=import_report.get("total_imported"),
        missing_reference_count=verification_report.get("missing_reference_count"),
        last_successful_validation_at=last_validation,
        row_counts=row_counts,
        checks=checks,
        warnings=warnings,
    )


@router.get(
    "/reports/performance",
    response_model=PerformanceReport,
    tags=["reports"],
    summary="Return measured API benchmark results or an explicit not-measured state",
)
def performance_report(
    _: User = Depends(require_roles(*AUDIT_READERS)),
) -> PerformanceReport:
    report = _read_report(settings.api_performance_report_path, "API performance")
    if report is None:
        return PerformanceReport(
            status="not_measured",
            measured=False,
            average_response_ms=None,
            median_response_ms=None,
            p95_response_ms=None,
            maximum_response_ms=None,
            slowest_endpoint=None,
            total_tested_requests=None,
            successful_request_percent=None,
            last_tested_at=None,
            status_distribution=None,
        )
    return PerformanceReport(
        status=str(report.get("status", "unknown")),
        measured=True,
        average_response_ms=report.get("average_response_ms"),
        median_response_ms=report.get("median_response_ms"),
        p95_response_ms=report.get("p95_response_ms"),
        maximum_response_ms=report.get("maximum_response_ms"),
        slowest_endpoint=report.get("slowest_endpoint"),
        total_tested_requests=report.get("total_tested_requests"),
        successful_request_percent=report.get("successful_request_percent"),
        last_tested_at=_report_datetime(report.get("completed_at")),
        status_distribution=report.get("status_distribution"),
    )
