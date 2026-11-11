"""Regression tests for the credential issuance business rules.

Rules under test:

* a course completion cannot be dated in the future;
* a credential is never issued before the completion it certifies;
* a rule must require completion, a minimum score, or both;
* issuance requires a non-cancelled enrollment in the rule's course;
* eligibility is never granted on missing, unfinished or future-dated evidence;
* rejecting a request never alters an existing signed credential or audit record.

Some cases write a row directly to the database. They stand for records that were
stored before these rules existed, which the API can no longer create.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.domain import (
    AssessmentAttempt,
    AuditEvent,
    CompletionRecord,
    Credential,
    CredentialRuleVersion,
    Enrollment,
)

from .support import (  # noqa: F401  (fixtures)
    Workspace,
    api_client,
    api_database,
    utc_now,
    workspace,
)


def credential_count(space: Workspace) -> int:
    space.db.expire_all()
    return space.db.query(Credential).count()


def assert_issuance_rejected(space: Workspace, learner_id: str, rule_code: str, reason: str) -> None:
    """Issuance returns 422 naming the reason, stores no credential, and is audited."""
    before = credential_count(space)
    response = space.issue(learner_id, rule_code)
    assert response.status_code == 422, response.text
    assert reason in response.json()["detail"]
    assert credential_count(space) == before
    rejection = space.db.scalars(
        select(AuditEvent)
        .where(AuditEvent.event_type == "credential.issuance_rejected")
        .order_by(AuditEvent.occurred_at.desc())
    ).first()
    assert rejection is not None
    assert rejection.outcome == "rejected"
    assert rejection.reason_code == reason


def evaluation(space: Workspace, learner_id: str, rule_code: str) -> tuple[str, list[str]]:
    response = space.evaluate(learner_id, rule_code)
    assert response.status_code == 200, response.text
    return response.json()["outcome"], response.json()["reason_codes"]


# --- Future-dated completions -------------------------------------------------


def test_future_dated_completion_is_rejected_on_create(workspace: Workspace) -> None:
    course_id = workspace.course()
    enrollment_id = workspace.enroll(workspace.learner(), course_id)

    for delta in (timedelta(minutes=10), timedelta(days=1), timedelta(days=30)):
        response = workspace.completion_request(enrollment_id, completed_at=utc_now() + delta)
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == "completed_at cannot be in the future."
    assert workspace.db.query(CompletionRecord).count() == 0

    # The same enrollment still accepts a completion dated in the past.
    assert workspace.completion_request(enrollment_id).status_code == 201


def test_future_dated_completion_is_rejected_on_update(workspace: Workspace) -> None:
    course_id = workspace.course()
    enrollment_id = workspace.enroll(workspace.learner(), course_id)
    completion_id = workspace.complete(enrollment_id, status="in_progress")

    response = workspace.patch(
        f"/completions/{completion_id}",
        {"status": "completed", "completed_at": (utc_now() + timedelta(days=30)).isoformat()},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "completed_at cannot be in the future."
    workspace.db.expire_all()
    stored = workspace.db.get(CompletionRecord, UUID(completion_id))
    assert stored.status == "in_progress" and stored.completed_at is None

    accepted = workspace.patch(
        f"/completions/{completion_id}",
        {"status": "completed", "completed_at": (utc_now() - timedelta(minutes=1)).isoformat()},
    )
    assert accepted.status_code == 200, accepted.text


def test_completion_inside_clock_tolerance_is_stored_but_not_yet_usable(
    workspace: Workspace,
) -> None:
    """A client clock slightly ahead is tolerated on input, never at issuance."""
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    enrollment_id = workspace.enroll(learner_id, course_id)

    ahead = workspace.completion_request(enrollment_id, completed_at=utc_now() + timedelta(minutes=3))
    assert ahead.status_code == 201, ahead.text

    assert evaluation(workspace, learner_id, "RULE-A") == (
        "ineligible",
        ["COMPLETION_DATE_IN_FUTURE"],
    )
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "COMPLETION_DATE_IN_FUTURE")


# --- Completion before issuance -----------------------------------------------


def test_stored_future_completion_cannot_produce_a_credential(workspace: Workspace) -> None:
    """The case found by the audit: a completion dated 30 days ahead was issued."""
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    completion_id = workspace.complete(workspace.enroll(learner_id, course_id))
    stored = workspace.db.get(CompletionRecord, UUID(completion_id))
    stored.completed_at = utc_now() + timedelta(days=30)
    workspace.db.commit()

    assert evaluation(workspace, learner_id, "RULE-A") == (
        "ineligible",
        ["COMPLETION_DATE_IN_FUTURE"],
    )
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "COMPLETION_DATE_IN_FUTURE")


def test_issued_credential_is_never_dated_before_its_completion(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    completed_at = utc_now() - timedelta(seconds=2)
    completion_id = workspace.complete(
        workspace.enroll(learner_id, course_id), completed_at=completed_at
    )

    issued = workspace.issue(learner_id, "RULE-A")
    assert issued.status_code == 201, issued.text

    workspace.db.expire_all()
    credential = workspace.db.query(Credential).one()
    completion = workspace.db.get(CompletionRecord, UUID(completion_id))
    assert completion.completed_at <= credential.issued_at
    portable = workspace.get(f"/credentials/{credential.credential_id}/portable").json()
    signed_completed_at = datetime.fromisoformat(portable["payload"]["completion"]["completed_at"])
    signed_issued_at = datetime.fromisoformat(portable["payload"]["issued_at"])
    assert signed_completed_at == completion.completed_at
    assert signed_completed_at <= signed_issued_at


def test_score_only_rule_cannot_issue_without_a_completed_course(workspace: Workspace) -> None:
    """A score-only rule may grant eligibility, but issuance still needs completion."""
    course_id = workspace.course()
    workspace.rule("SCORE-ONLY", course_id, {"requires_completion": False, "minimum_score": 70})
    learner_id = workspace.learner()
    completion_id = workspace.complete(workspace.enroll(learner_id, course_id), status="in_progress")
    workspace.attempt(completion_id, "90")

    assert evaluation(workspace, learner_id, "SCORE-ONLY") == ("eligible", [])
    assert_issuance_rejected(
        workspace, learner_id, "SCORE-ONLY", "COMPLETION_REQUIRED_BEFORE_ISSUANCE"
    )

    # Once the course is completed, the same learner and rule can be issued.
    completed = workspace.patch(
        f"/completions/{completion_id}",
        {"status": "completed", "completed_at": (utc_now() - timedelta(seconds=1)).isoformat()},
    )
    assert completed.status_code == 200, completed.text
    issued = workspace.issue(learner_id, "SCORE-ONLY")
    assert issued.status_code == 201, issued.text
    workspace.db.expire_all()
    credential = workspace.db.query(Credential).one()
    assert workspace.db.get(CompletionRecord, UUID(completion_id)).completed_at <= credential.issued_at


# --- Empty rules ---------------------------------------------------------------


@pytest.mark.parametrize(
    "criteria",
    [
        {"requires_completion": False},
        {"requires_completion": False, "minimum_score": None},
        {"requires_completion": False, "score_scale": "0-100"},
    ],
)
def test_rule_without_requirements_is_rejected_on_create(
    workspace: Workspace, criteria: dict
) -> None:
    course_id = workspace.course()

    response = workspace.rule_request("EMPTY-RULE", course_id, criteria)

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "A credential rule must require course completion, a minimum score, or both."
    )
    assert workspace.db.query(CredentialRuleVersion).count() == 0


def test_rule_version_without_requirements_is_rejected(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)

    response = workspace.post(
        "/credential-rules/RULE-A/versions",
        {
            "course_id": course_id,
            "criteria": {"requires_completion": False},
            "effective_from": utc_now().isoformat(),
        },
    )

    assert response.status_code == 422, response.text
    workspace.db.expire_all()
    versions = workspace.db.query(CredentialRuleVersion).all()
    assert len(versions) == 1
    assert versions[0].effective_to is None  # The existing version was not closed.


@pytest.mark.parametrize(
    "criteria",
    [
        {},
        {"requires_completion": True},
        {"minimum_score": 70},
        {"requires_completion": True, "minimum_score": 70, "score_scale": "0-100"},
        {"requires_completion": False, "minimum_score": 70},
    ],
)
def test_rules_with_at_least_one_requirement_are_still_accepted(
    workspace: Workspace, criteria: dict
) -> None:
    course_id = workspace.course()

    assert workspace.rule_request("VALID-RULE", course_id, criteria).status_code == 201


def test_stored_empty_rule_never_grants_eligibility_or_a_credential(workspace: Workspace) -> None:
    """The case found by the audit: an empty rule issued a credential to anyone."""
    course_id = workspace.course()
    version_id = workspace.rule("LEGACY-EMPTY", course_id)
    version = workspace.db.get(CredentialRuleVersion, UUID(version_id))
    version.criteria = {"requires_completion": False, "attempt_selection_policy": "latest_graded"}
    workspace.db.commit()

    not_enrolled = workspace.learner()
    outcome, reasons = evaluation(workspace, not_enrolled, "LEGACY-EMPTY")
    assert outcome == "needs_review"
    assert reasons == ["RULE_HAS_NO_REQUIREMENTS", "MISSING_ENROLLMENT"]
    assert_issuance_rejected(workspace, not_enrolled, "LEGACY-EMPTY", "RULE_HAS_NO_REQUIREMENTS")

    # Even a learner who really completed the course is sent to review, not issued.
    completed = workspace.learner()
    workspace.complete(workspace.enroll(completed, course_id))
    assert evaluation(workspace, completed, "LEGACY-EMPTY") == (
        "needs_review",
        ["RULE_HAS_NO_REQUIREMENTS"],
    )
    assert_issuance_rejected(workspace, completed, "LEGACY-EMPTY", "RULE_HAS_NO_REQUIREMENTS")


# --- Enrollment required --------------------------------------------------------


def test_learner_without_enrollment_is_not_eligible(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    workspace.rule("RULE-SCORE", course_id, {"requires_completion": True, "minimum_score": 70})
    learner_id = workspace.learner()

    assert evaluation(workspace, learner_id, "RULE-A") == (
        "ineligible",
        ["MISSING_ENROLLMENT", "MISSING_COMPLETION"],
    )
    assert evaluation(workspace, learner_id, "RULE-SCORE") == (
        "ineligible",
        ["MISSING_ENROLLMENT", "MISSING_COMPLETION", "MISSING_ASSESSMENT"],
    )
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "MISSING_ENROLLMENT")


def test_enrollment_in_another_course_does_not_count(workspace: Workspace) -> None:
    rule_course = workspace.course()
    other_course = workspace.course()
    workspace.rule("RULE-A", rule_course)
    learner_id = workspace.learner()
    workspace.complete(workspace.enroll(learner_id, other_course))

    outcome, reasons = evaluation(workspace, learner_id, "RULE-A")

    assert outcome == "ineligible"
    assert reasons[0] == "MISSING_ENROLLMENT"
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "MISSING_ENROLLMENT")


def test_cancelled_enrollment_does_not_count(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    enrollment_id = workspace.enroll(learner_id, course_id)
    workspace.complete(enrollment_id)
    assert evaluation(workspace, learner_id, "RULE-A") == ("eligible", [])

    workspace.db.get(Enrollment, UUID(enrollment_id)).status = "cancelled"
    workspace.db.commit()

    outcome, reasons = evaluation(workspace, learner_id, "RULE-A")
    assert outcome == "ineligible"
    assert reasons[0] == "MISSING_ENROLLMENT"
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "MISSING_ENROLLMENT")


# --- Incomplete evidence ---------------------------------------------------------


def test_enrolled_learner_without_completion_record_is_not_eligible(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    workspace.enroll(learner_id, course_id)

    assert evaluation(workspace, learner_id, "RULE-A") == ("ineligible", ["MISSING_COMPLETION"])
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "MISSING_COMPLETION")


@pytest.mark.parametrize("status", ["in_progress", "incomplete", "failed"])
def test_unfinished_course_is_not_eligible(workspace: Workspace, status: str) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    workspace.complete(workspace.enroll(learner_id, course_id), status=status)

    assert evaluation(workspace, learner_id, "RULE-A") == ("ineligible", ["COURSE_INCOMPLETE"])
    assert_issuance_rejected(workspace, learner_id, "RULE-A", "COURSE_INCOMPLETE")


def test_missing_or_ungraded_assessment_is_not_eligible(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-SCORE", course_id, {"requires_completion": True, "minimum_score": 70})
    learner_id = workspace.learner()
    completion_id = workspace.complete(workspace.enroll(learner_id, course_id))

    assert evaluation(workspace, learner_id, "RULE-SCORE") == ("ineligible", ["MISSING_ASSESSMENT"])

    workspace.attempt(completion_id, "", status="submitted")
    assert evaluation(workspace, learner_id, "RULE-SCORE") == ("ineligible", ["MISSING_ASSESSMENT"])
    assert_issuance_rejected(workspace, learner_id, "RULE-SCORE", "MISSING_ASSESSMENT")


def test_future_dated_grade_is_not_usable_evidence(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-SCORE", course_id, {"requires_completion": True, "minimum_score": 70})
    learner_id = workspace.learner()
    completion_id = workspace.complete(workspace.enroll(learner_id, course_id))
    attempt_id = workspace.attempt(completion_id, "95")
    assert evaluation(workspace, learner_id, "RULE-SCORE") == ("eligible", [])

    workspace.db.get(AssessmentAttempt, UUID(attempt_id)).graded_at = utc_now() + timedelta(days=7)
    workspace.db.commit()

    assert evaluation(workspace, learner_id, "RULE-SCORE") == (
        "ineligible",
        ["ASSESSMENT_DATE_IN_FUTURE"],
    )
    assert_issuance_rejected(workspace, learner_id, "RULE-SCORE", "ASSESSMENT_DATE_IN_FUTURE")


def test_complete_evidence_is_still_eligible_and_issued(workspace: Workspace) -> None:
    """The valid path is unchanged by the stricter rules."""
    course_id = workspace.course()
    workspace.rule("RULE-SCORE", course_id, {"requires_completion": True, "minimum_score": 70})
    learner_id = workspace.learner()
    completion_id = workspace.complete(workspace.enroll(learner_id, course_id))
    workspace.attempt(completion_id, "70")

    assert evaluation(workspace, learner_id, "RULE-SCORE") == ("eligible", [])
    issued = workspace.issue(learner_id, "RULE-SCORE")
    assert issued.status_code == 201, issued.text
    verification = workspace.client.post(
        "/api/v1/verification/credential-id",
        params={"credential_id": issued.json()["credential_id"]},
    )
    assert verification.json()["overall_result"] == "VALID"


# --- Existing credentials and audit history are preserved -------------------------


def test_rejections_leave_existing_credentials_and_audit_history_untouched(
    workspace: Workspace,
) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id, credential_id = workspace.issued_learner(course_id, "RULE-A")
    completion = workspace.db.query(CompletionRecord).one()

    def credential_state() -> tuple:
        workspace.db.expire_all()
        row = workspace.db.query(Credential).one()
        return (
            row.id,
            row.credential_id,
            row.issued_at,
            bytes(row.canonical_payload),
            bytes(row.sha256_digest),
            bytes(row.signature),
            row.eligibility_decision_id,
            row.signing_key_id,
        )

    def audit_state() -> dict:
        workspace.db.expire_all()
        return {
            event.id: (
                event.event_type,
                event.outcome,
                event.actor_reference,
                event.target_reference,
                event.reason_code,
                event.occurred_at,
                event.event_data,
            )
            for event in workspace.db.query(AuditEvent).all()
        }

    credential_before = credential_state()
    audit_before = audit_state()
    portable_before = workspace.get(f"/credentials/{credential_id}/portable").json()

    # Every newly enforced rule rejects something here.
    assert (
        workspace.patch(
            f"/completions/{completion.id}",
            {"status": "completed", "completed_at": (utc_now() + timedelta(days=30)).isoformat()},
        ).status_code
        == 422
    )
    assert workspace.rule_request("EMPTY", course_id, {"requires_completion": False}).status_code == 422
    assert workspace.issue(workspace.learner(), "RULE-A").status_code == 422
    enrolled_only = workspace.learner()
    workspace.enroll(enrolled_only, course_id)
    assert workspace.issue(enrolled_only, "RULE-A").status_code == 422
    # A second credential for the same learner and course is still refused.
    assert workspace.issue(learner_id, "RULE-A").status_code == 409

    assert credential_state() == credential_before
    assert workspace.get(f"/credentials/{credential_id}/portable").json() == portable_before
    audit_after = audit_state()
    for event_id, recorded in audit_before.items():
        assert audit_after[event_id] == recorded  # No earlier event changed or vanished.
    added = [audit_after[event_id] for event_id in audit_after.keys() - audit_before.keys()]
    assert sum(1 for event in added if event[0] == "credential.issuance_rejected") == 2

    # The original credential still verifies by ID and as a portable payload.
    by_id = workspace.client.post(
        "/api/v1/verification/credential-id", params={"credential_id": credential_id}
    )
    assert by_id.json()["overall_result"] == "VALID"
    by_payload = workspace.client.post("/api/v1/verification/portable", json=portable_before)
    assert by_payload.json()["overall_result"] == "VALID"
