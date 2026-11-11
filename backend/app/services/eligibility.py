from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ServiceError
from app.models.domain import (
    AssessmentAttempt,
    CompletionRecord,
    CredentialRule,
    CredentialRuleVersion,
    Course,
    EligibilityDecision,
    EligibilityEvidence,
    EligibilityReason,
    Enrollment,
    Learner,
    RuleCourse,
)

EVALUATOR_VERSION = "credential-eligibility-v1"

# Reason codes that mean the rule itself cannot be evaluated safely. They send the
# decision to manual review instead of producing an eligible or ineligible outcome.
REVIEW_REASON_CODES = frozenset(
    {"UNSUPPORTED_ATTEMPT_SELECTION_POLICY", "RULE_HAS_NO_REQUIREMENTS"}
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def evaluate_and_record(
    db: Session,
    *,
    learner: Learner,
    rule_code: str,
    evaluator_user_id: UUID | None,
    evaluator_reference: str,
) -> tuple[EligibilityDecision, list[str], str]:
    now = datetime.now(timezone.utc)
    rule = db.scalar(
        select(CredentialRule).where(
            CredentialRule.rule_code == rule_code,
            CredentialRule.archived_at.is_(None),
        )
    )
    if rule is None:
        raise ServiceError(404, "Credential rule was not found.")
    version = db.scalar(
        select(CredentialRuleVersion)
        .where(
            CredentialRuleVersion.rule_id == rule.id,
            CredentialRuleVersion.status == "active",
            CredentialRuleVersion.effective_from <= now,
            (CredentialRuleVersion.effective_to.is_(None))
            | (CredentialRuleVersion.effective_to > now),
        )
        .order_by(CredentialRuleVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        raise ServiceError(409, "No effective active version exists for this rule.")
    scope_course_ids = db.scalars(
        select(RuleCourse.course_id).where(RuleCourse.rule_version_id == version.id)
    ).all()
    if not scope_course_ids:
        raise ServiceError(409, "The active rule version has no course requirements.")
    course = db.get(Course, scope_course_ids[0])
    if course is None:
        raise ServiceError(409, "The rule version references unavailable course data.")

    criteria = version.criteria
    policy = version.attempt_selection_policy or criteria.get(
        "attempt_selection_policy", "latest_graded"
    )
    minimum_score_value = criteria.get("minimum_score")
    try:
        minimum_score = (
            Decimal(str(minimum_score_value))
            if minimum_score_value is not None
            else None
        )
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ServiceError(409, "Rule contains an invalid minimum_score value.") from exc
    if minimum_score is not None and (
        not minimum_score.is_finite()
        or not Decimal("0") <= minimum_score <= Decimal("100")
    ):
        raise ServiceError(409, "Rule minimum_score must be between 0 and 100.")
    requires_completion = criteria.get("requires_completion", True)

    enrollments = db.scalars(
        select(Enrollment)
        .where(
            Enrollment.learner_id == learner.id,
            Enrollment.course_id == course.id,
            Enrollment.status != "cancelled",
        )
        .order_by(Enrollment.enrolled_at.desc(), Enrollment.id.desc())
    ).all()
    completions: list[CompletionRecord] = []
    for enrollment in enrollments:
        completions.extend(
            db.scalars(
                select(CompletionRecord)
                .where(CompletionRecord.enrollment_id == enrollment.id)
                .order_by(CompletionRecord.recorded_at.desc())
            ).all()
        )
    completion = completions[0] if completions else None
    reasons: list[str] = []
    evidence_rows: list[dict[str, Any]] = []
    selected_attempt: AssessmentAttempt | None = None

    # A rule that requires neither completion nor a score has nothing to evaluate.
    # Such rules are rejected when created; a stored one is never auto-approved.
    if not requires_completion and minimum_score is None:
        reasons.append("RULE_HAS_NO_REQUIREMENTS")
    # Evidence only counts when the learner holds a non-cancelled enrollment in the
    # course that the rule covers.
    if not enrollments:
        reasons.append("MISSING_ENROLLMENT")

    completion_is_recorded_complete = (
        completion is not None
        and completion.status == "completed"
        and completion.completed_at is not None
    )
    # A completion dated after the evaluation time has not happened yet.
    completion_is_usable = (
        completion_is_recorded_complete and completion.completed_at <= now
    )
    if requires_completion:
        if completion is None:
            reasons.append("MISSING_COMPLETION")
        elif not completion_is_recorded_complete:
            reasons.append("COURSE_INCOMPLETE")
        elif not completion_is_usable:
            reasons.append("COMPLETION_DATE_IN_FUTURE")
    # Usable completion evidence is always captured, including for score-only rules,
    # because issuance requires a completion dated on or before the issue time.
    if completion_is_usable:
        evidence_rows.append(
            {
                "completion_record_id": str(completion.id),
                "status": completion.status,
                "completed_at": completion.completed_at.isoformat(),
                "course_id": str(completion.course_id),
            }
        )
    if policy != "latest_graded":
        reasons.append("UNSUPPORTED_ATTEMPT_SELECTION_POLICY")
    elif minimum_score is not None:
        if completion is None:
            reasons.append("MISSING_ASSESSMENT")
        else:
            attempts = db.scalars(
                select(AssessmentAttempt)
                .where(
                    AssessmentAttempt.completion_record_id == completion.id,
                    AssessmentAttempt.status == "graded",
                    AssessmentAttempt.graded_at.is_not(None),
                )
                .order_by(
                    AssessmentAttempt.graded_at.desc(),
                    AssessmentAttempt.attempt_number.desc(),
                    AssessmentAttempt.id.desc(),
                )
            ).all()
            superseded_ids = {
                attempt.supersedes_attempt_id
                for attempt in db.scalars(
                    select(AssessmentAttempt).where(
                        AssessmentAttempt.completion_record_id == completion.id,
                        AssessmentAttempt.supersedes_attempt_id.is_not(None),
                    )
                ).all()
            }
            selected_attempt = next(
                (attempt for attempt in attempts if attempt.id not in superseded_ids),
                None,
            )
            if selected_attempt is None or selected_attempt.score is None:
                reasons.append("MISSING_ASSESSMENT")
            elif selected_attempt.graded_at > now:
                # A grade dated after the evaluation time is not yet usable evidence.
                reasons.append("ASSESSMENT_DATE_IN_FUTURE")
            elif selected_attempt.score < minimum_score:
                reasons.append("ASSESSMENT_BELOW_THRESHOLD")
            else:
                evidence_rows.append(
                    {
                        "attempt_id": str(selected_attempt.id),
                        "assessment_key": selected_attempt.assessment_key,
                        "attempt_number": selected_attempt.attempt_number,
                        "score": str(selected_attempt.score),
                        "score_scale": selected_attempt.score_scale,
                        "graded_at": selected_attempt.graded_at.isoformat(),
                    }
                )

    needs_review = bool(REVIEW_REASON_CODES.intersection(reasons))
    outcome = "needs_review" if needs_review else ("ineligible" if reasons else "eligible")
    snapshot = {
        "learner_id": str(learner.id),
        "rule_id": str(rule.id),
        "rule_version_id": str(version.id),
        "credential_scope_id": str(version.credential_scope_id),
        "course_id": str(course.id),
        "criteria": criteria,
        "attempt_selection_policy": policy,
        "minimum_score": str(minimum_score) if minimum_score is not None else None,
        "evidence": evidence_rows,
        "reason_codes": reasons,
        "evaluator_version": EVALUATOR_VERSION,
    }
    digest = hashlib.sha256(canonical_json(snapshot)).digest()
    decision = EligibilityDecision(
        id=uuid4(),
        learner_id=learner.id,
        rule_version_id=version.id,
        credential_scope_id=version.credential_scope_id,
        evaluated_at=now,
        outcome=outcome,
        evaluator_type="user" if evaluator_user_id else "service",
        evaluator_user_id=evaluator_user_id,
        evaluator_reference=evaluator_reference,
        evaluator_version=EVALUATOR_VERSION,
        attempt_selection_policy=policy,
        evidence_snapshot=snapshot,
        input_snapshot_digest=digest,
    )
    db.add(decision)
    db.flush()
    for code in reasons:
        db.add(
            EligibilityReason(
                id=uuid4(),
                eligibility_decision_id=decision.id,
                reason_code=code,
                message=code.replace("_", " ").lower(),
            )
        )
    for evidence in evidence_rows:
        completion_id = (
            UUID(evidence["completion_record_id"])
            if "completion_record_id" in evidence
            else None
        )
        attempt_id = UUID(evidence["attempt_id"]) if "attempt_id" in evidence else None
        db.add(
            EligibilityEvidence(
                id=uuid4(),
                eligibility_decision_id=decision.id,
                learner_id=learner.id,
                completion_record_id=completion_id,
                assessment_attempt_id=attempt_id,
                selection_role="completion" if completion_id else "selected_attempt",
                evidence_snapshot=evidence,
                evidence_digest=hashlib.sha256(canonical_json(evidence)).digest(),
            )
        )
    db.flush()
    return decision, reasons, rule.rule_code
