"""Regression tests for malformed input that used to cause HTTP 500.

Every case here returned "Internal Server Error" before the fix. The cases cover:

* NUL characters in the path, the query string and JSON bodies;
* a portable payload whose claimed credential ID cannot exist in the registry;
* timestamps at the edge of the calendar, which could also be stored in a form that
  made the affected record unreadable afterwards;
* page offsets beyond the 64-bit range;
* a time-zone-naive assessment timestamp.

``lenient_client`` returns the 500 response instead of re-raising, so a regression
shows up as a failed status assertion.
"""
from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.domain import AssessmentAttempt, Course, Enrollment, Learner, VerificationRequest

from .support import (  # noqa: F401  (fixtures)
    Workspace,
    api_client,
    api_database,
    assert_no_internal_details,
    lenient_client,
    utc_now,
    workspace,
)

NUL = "a\x00b"
NUL_DETAIL = "Request contains an unsupported NUL character."
# Both are rejected by PostgreSQL or overflow in Python once converted to UTC.
EDGE_TIMESTAMPS = [
    "0001-01-01T00:00:00+00:00",
    "0001-01-01T00:00:00+14:00",
    "1899-12-31T23:59:59+00:00",
    "3000-01-01T00:00:00+00:00",
    "9999-12-31T23:59:59+00:00",
    "9999-12-31T23:59:59-14:00",
]


def assert_rejected(response, status_code: int = 422) -> None:
    assert response.status_code == status_code, f"{response.status_code}: {response.text[:200]}"
    assert_no_internal_details(response)


# --- Public endpoints (no authentication) -------------------------------------


@pytest.mark.parametrize("claimed_id", ["X" * 50, "CRD-2026-0000011", "X" * 5000])
def test_portable_verification_with_impossible_credential_id(
    workspace: Workspace, lenient_client: TestClient, claimed_id: str
) -> None:
    response = lenient_client.post(
        "/api/v1/verification/portable",
        json={"payload": {"credential_id": claimed_id}, "signature_base64": "AA=="},
    )

    # An unverifiable payload is a normal verification outcome, not an error.
    assert_rejected(response, 200)
    body = response.json()
    assert body["overall_result"] == "UNVERIFIABLE"
    assert body["credential_id"] is None
    workspace.db.expire_all()
    stored = workspace.db.query(VerificationRequest).one()
    assert stored.submitted_credential_id is None
    assert stored.credential_id_fk is None


@pytest.mark.parametrize(
    "payload",
    [
        {"credential_id": NUL},
        {"credential_id": "CRD-2026-000001", "signing_key_id": NUL},
        {"credential_id": "CRD-2026-000001", "issuer": {"issuer_code": NUL}},
        {"credential_id": "CRD-2026-000001", "note": {"deep": [NUL]}},
        {"credential_id": "CRD-2026-000001", NUL: "value"},
    ],
)
def test_portable_verification_rejects_nul_characters(
    workspace: Workspace, lenient_client: TestClient, payload: dict
) -> None:
    response = lenient_client.post(
        "/api/v1/verification/portable",
        json={"payload": payload, "signature_base64": "AA=="},
    )

    assert_rejected(response)
    assert response.json()["detail"] == NUL_DETAIL
    assert workspace.db.query(VerificationRequest).count() == 0


def test_portable_verification_handles_wrong_claim_types(
    workspace: Workspace, lenient_client: TestClient
) -> None:
    for payload in (
        {"credential_id": 5},
        {"credential_id": ["CRD-2026-000001"]},
        {"credential_id": "CRD-2026-000001", "issuer": "text"},
        {"credential_id": "CRD-2026-000001", "issuer": {"issuer_code": 7}, "signing_key_id": {}},
        {},
    ):
        response = lenient_client.post(
            "/api/v1/verification/portable",
            json={"payload": payload, "signature_base64": "not base64 !!"},
        )
        assert_rejected(response, 200)
        assert response.json()["overall_result"] == "UNVERIFIABLE"


def test_real_portable_payload_still_verifies(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    _, credential_id = workspace.issued_learner(course_id, "RULE-A")
    portable = workspace.get(f"/credentials/{credential_id}/portable").json()

    response = workspace.client.post("/api/v1/verification/portable", json=portable)

    assert response.status_code == 200
    assert response.json()["overall_result"] == "VALID"
    assert response.json()["credential_id"] == credential_id
    workspace.db.expire_all()
    assert workspace.db.query(VerificationRequest).one().submitted_credential_id == credential_id


@pytest.mark.parametrize("query", ["credential_id=%00", "credential_id=CRD%00", "credential_id=a%00b"])
def test_credential_id_verification_rejects_nul(
    workspace: Workspace, lenient_client: TestClient, query: str
) -> None:
    response = lenient_client.post(f"/api/v1/verification/credential-id?{query}")

    assert_rejected(response)
    assert response.json()["detail"] == NUL_DETAIL
    assert workspace.db.query(VerificationRequest).count() == 0


def test_login_rejects_nul_without_leaking_details(
    workspace: Workspace, lenient_client: TestClient
) -> None:
    for body in (
        {"principal_key": NUL, "password": "local-test-password-2026"},
        {"principal_key": "test-platform_administrator", "password": NUL},
    ):
        response = lenient_client.post("/api/v1/auth/login", json=body)
        assert_rejected(response)
        assert response.json()["detail"] == NUL_DETAIL

    # Ordinary wrong credentials are still a plain 401.
    wrong = lenient_client.post(
        "/api/v1/auth/login",
        json={"principal_key": "test-platform_administrator", "password": "wrong-password"},
    )
    assert wrong.status_code == 401


# --- NUL characters on authenticated endpoints ---------------------------------


def test_nul_in_json_bodies_is_rejected_everywhere(
    workspace: Workspace, lenient_client: TestClient
) -> None:
    course_id = workspace.course()
    learner_id = workspace.learner()
    workspace.rule("RULE-A", course_id)
    completion_id = workspace.complete(workspace.enroll(learner_id, course_id))
    learners_before = workspace.db.query(Learner).count()
    past = (utc_now() - timedelta(days=1)).isoformat()
    requests = [
        ("POST", "/learners", {"display_name": NUL}),
        ("PATCH", f"/learners/{learner_id}", {"display_name": NUL}),
        ("POST", "/courses", {"course_code": "NUL-COURSE", "title": NUL}),
        ("PATCH", f"/courses/{course_id}", {"description": NUL}),
        ("POST", "/issuers", {"issuer_code": NUL, "name": "Issuer"}),
        (
            "POST",
            "/credential-rules",
            {
                "rule_code": "NUL-RULE",
                "name": "Rule",
                "course_id": course_id,
                "criteria": {"requires_completion": True, NUL: 1},
                "effective_from": past,
            },
        ),
        (
            "POST",
            "/credential-rules/RULE-A/versions",
            {"course_id": course_id, "criteria": {"note": NUL}, "effective_from": utc_now().isoformat()},
        ),
        (
            "POST",
            "/assessment-attempts",
            {
                "completion_record_id": completion_id,
                "assessment_key": NUL,
                "status": "submitted",
                "submitted_at": past,
            },
        ),
        ("POST", "/eligibility/evaluate", {"learner_id": learner_id, "rule_code": NUL}),
        ("POST", "/revocations/CRD-2026-000001", {"reason_code": NUL}),
    ]
    for method, path, body in requests:
        response = lenient_client.request(
            method, f"/api/v1{path}", json=body, headers=workspace.headers
        )
        assert_rejected(response)
        assert response.json()["detail"] == NUL_DETAIL, (method, path)
    workspace.db.expire_all()
    assert workspace.db.query(Learner).count() == learners_before
    assert workspace.db.query(AssessmentAttempt).count() == 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/credentials/a%00b"),
        ("GET", "/credentials/%00/portable"),
        ("GET", "/credentials/%00/history"),
        ("PATCH", "/issuers/a%00b"),
        ("POST", "/issuers/%00/signing-keys/key/revoke"),
        ("POST", "/issuers/TEST-ISSUER/signing-keys/a%00b/revoke"),
        ("POST", "/credential-rules/a%00b/versions"),
        ("POST", "/revocations/a%00b"),
        ("GET", "/audit?target_reference=a%00b"),
        ("GET", "/verification/requests?outcome=%00"),
        ("GET", "/reports/verification-analytics?outcome=a%00b"),
    ],
)
def test_nul_in_path_or_query_is_rejected(
    workspace: Workspace, lenient_client: TestClient, method: str, path: str
) -> None:
    body = None if method == "GET" else {"name": "Issuer", "reason_code": "ADMIN_ERROR"}
    response = lenient_client.request(
        method, f"/api/v1{path}", json=body, headers=workspace.headers
    )

    assert_rejected(response)
    assert response.json()["detail"] == NUL_DETAIL


def test_text_that_only_looks_like_a_nul_escape_is_accepted(workspace: Workspace) -> None:
    """The six visible characters backslash-u-0-0-0-0 are ordinary text, not a NUL."""
    literal = "Ada \\u0000 Lovelace"

    response = workspace.post("/learners", {"display_name": literal})

    assert response.status_code == 201, response.text
    assert response.json()["display_name"] == literal
    workspace.db.expire_all()
    assert workspace.db.query(Learner).one().display_name == literal


# --- Timestamps at the edge of the calendar -------------------------------------


@pytest.mark.parametrize("timestamp", EDGE_TIMESTAMPS)
def test_out_of_range_timestamps_are_rejected(
    workspace: Workspace, lenient_client: TestClient, timestamp: str
) -> None:
    course_id = workspace.course()
    learner_id = workspace.learner()
    workspace.rule("RULE-A", course_id)
    enrollment_id = workspace.enroll(learner_id, course_id)
    completion_id = workspace.complete(enrollment_id)
    other_learner = workspace.learner()
    past = (utc_now() - timedelta(days=1)).isoformat()
    requests = [
        ("POST", "/courses", {"course_code": "EDGE", "title": "Edge", "effective_from": timestamp}),
        ("POST", "/courses", {"course_code": "EDGE", "title": "Edge", "effective_to": timestamp}),
        ("PATCH", f"/courses/{course_id}", {"effective_from": timestamp}),
        ("PATCH", f"/courses/{course_id}", {"effective_to": timestamp}),
        (
            "POST",
            "/issuers/TEST-ISSUER/signing-keys",
            {"key_id": "edge", "public_key_base64": "AAAA", "valid_from": timestamp},
        ),
        (
            "POST",
            "/credential-rules",
            {
                "rule_code": "EDGE-RULE",
                "name": "Edge",
                "course_id": course_id,
                "criteria": {"requires_completion": True},
                "effective_from": timestamp,
            },
        ),
        (
            "POST",
            "/credential-rules/RULE-A/versions",
            {"course_id": course_id, "criteria": {"requires_completion": True}, "effective_from": timestamp},
        ),
        (
            "POST",
            "/enrollments",
            {"learner_id": other_learner, "course_id": course_id, "effective_from": timestamp},
        ),
        ("POST", "/completions", {"enrollment_id": enrollment_id, "status": "in_progress", "started_at": timestamp}),
        ("PATCH", f"/completions/{completion_id}", {"status": "completed", "completed_at": timestamp}),
        (
            "POST",
            "/assessment-attempts",
            {
                "completion_record_id": completion_id,
                "assessment_key": "final",
                "status": "submitted",
                "submitted_at": timestamp,
            },
        ),
        (
            "POST",
            "/assessment-attempts",
            {
                "completion_record_id": completion_id,
                "assessment_key": "final",
                "score": "80",
                "status": "graded",
                "submitted_at": past,
                "graded_at": timestamp,
            },
        ),
    ]
    for method, path, body in requests:
        response = lenient_client.request(
            method, f"/api/v1{path}", json=body, headers=workspace.headers
        )
        assert_rejected(response)

    # Nothing was stored, and every list that reads these tables still works.
    workspace.db.expire_all()
    assert workspace.db.query(Course).count() == 1
    assert workspace.db.query(Enrollment).count() == 1
    assert workspace.db.query(AssessmentAttempt).count() == 0
    for path in ("/courses", "/enrollments", "/completions", "/assessment-attempts", "/credential-rules"):
        assert lenient_client.get(f"/api/v1{path}", headers=workspace.headers).status_code == 200


def test_supported_timestamps_are_still_accepted(workspace: Workspace) -> None:
    response = workspace.post(
        "/courses",
        {
            "course_code": "RANGE",
            "title": "Range",
            "effective_from": "1900-01-01T00:00:00+00:00",
            "effective_to": "2999-12-31T23:59:59+00:00",
        },
    )

    assert response.status_code == 201, response.text


@pytest.mark.parametrize("field", ["submitted_at", "graded_at"])
def test_naive_assessment_timestamp_is_rejected(
    workspace: Workspace, lenient_client: TestClient, field: str
) -> None:
    course_id = workspace.course()
    completion_id = workspace.complete(workspace.enroll(workspace.learner(), course_id))
    body = {
        "completion_record_id": completion_id,
        "assessment_key": "final",
        "score": "80",
        "status": "graded",
        "submitted_at": (utc_now() - timedelta(hours=2)).isoformat(),
        "graded_at": (utc_now() - timedelta(hours=1)).isoformat(),
    }
    body[field] = "2026-01-01T00:00:00"

    response = lenient_client.post(
        "/api/v1/assessment-attempts", json=body, headers=workspace.headers
    )

    assert_rejected(response)
    assert response.json()["detail"] == f"{field} must include a timezone."
    assert workspace.db.query(AssessmentAttempt).count() == 0


@pytest.mark.parametrize(
    "query",
    [
        "date_to=9999-12-31",
        "date_from=9999-12-31&date_to=9999-12-31",
        "date_from=0001-01-01",
        "date_from=1899-12-31",
        "date_to=3000-01-01",
    ],
)
def test_analytics_reject_out_of_range_dates(
    workspace: Workspace, lenient_client: TestClient, query: str
) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    workspace.issued_learner(course_id, "RULE-A")

    for path in (
        "/reports/credential-lifecycle",
        "/reports/verification-analytics",
        "/reports/academic-analytics",
    ):
        response = lenient_client.get(f"/api/v1{path}?{query}", headers=workspace.headers)
        assert_rejected(response)
        assert response.json()["detail"] == "Dates must fall between the years 1900 and 2999."

    # The first and last supported years are accepted.
    for edge in ("date_from=1900-01-01&date_to=1900-12-31", "date_from=2999-01-01&date_to=2999-12-31"):
        accepted = lenient_client.get(
            f"/api/v1/reports/credential-lifecycle?{edge}", headers=workspace.headers
        )
        assert accepted.status_code == 200, accepted.text


# --- Paging -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/learners",
        "/courses",
        "/issuers",
        "/credential-rules",
        "/enrollments",
        "/completions",
        "/assessment-attempts",
        "/credentials",
        "/revocations",
        "/verification/requests",
        "/audit",
    ],
)
def test_page_offset_is_bounded(
    workspace: Workspace, lenient_client: TestClient, path: str
) -> None:
    for offset in ("1000000001", "9223372036854775808", "99999999999999999999999"):
        response = lenient_client.get(
            f"/api/v1{path}?offset={offset}", headers=workspace.headers
        )
        assert_rejected(response)

    at_limit = lenient_client.get(
        f"/api/v1{path}?offset=1000000000", headers=workspace.headers
    )
    assert at_limit.status_code == 200, at_limit.text
    assert at_limit.json() == []


def test_unknown_identifiers_are_not_found_rather_than_errors(
    workspace: Workspace, lenient_client: TestClient
) -> None:
    for method, path, body in (
        ("GET", f"/learners/{uuid4()}", None),
        ("GET", "/credentials/CRD-2026-999999", None),
        ("GET", f"/credentials/{'X' * 300}", None),
        ("POST", f"/revocations/{'X' * 300}", {"reason_code": "ADMIN_ERROR"}),
        ("PATCH", f"/issuers/{'X' * 300}", {"name": "Issuer"}),
    ):
        response = lenient_client.request(
            method, f"/api/v1{path}", json=body, headers=workspace.headers
        )
        assert_rejected(response, 404)
