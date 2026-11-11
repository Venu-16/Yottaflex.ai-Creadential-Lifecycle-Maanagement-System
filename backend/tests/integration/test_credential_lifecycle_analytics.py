"""Regression tests for GET /reports/credential-lifecycle.

The endpoint used to fail with HTTP 500 as soon as one credential existed, because
the status buckets were built twice. These tests cover zero, one and many credentials.
"""
from __future__ import annotations

from datetime import timedelta

from .support import (  # noqa: F401  (fixtures)
    Workspace,
    api_client,
    api_database,
    utc_now,
    workspace,
)

LIFECYCLE = "/reports/credential-lifecycle"
BUCKET_KEYS = {"key", "count"}
TIME_BUCKET_KEYS = {"period", "outcome", "count"}


def lifecycle(space: Workspace, **params: str) -> dict:
    response = space.get(LIFECYCLE, **params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "as_of",
        "credential_status",
        "issuance_over_time",
        "revocations_over_time",
        "eligibility_outcomes",
    }
    for bucket in body["credential_status"] + body["eligibility_outcomes"]:
        assert set(bucket) == BUCKET_KEYS
        assert isinstance(bucket["key"], str) and isinstance(bucket["count"], int)
    for bucket in body["issuance_over_time"] + body["revocations_over_time"]:
        assert set(bucket) == TIME_BUCKET_KEYS
        assert isinstance(bucket["period"], str) and isinstance(bucket["count"], int)
    return body


def test_lifecycle_with_zero_credentials(workspace: Workspace) -> None:
    body = lifecycle(workspace)

    assert body["credential_status"] == []
    assert body["issuance_over_time"] == []
    assert body["revocations_over_time"] == []
    assert body["eligibility_outcomes"] == []


def test_lifecycle_with_zero_credentials_but_recorded_decisions(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    learner_id = workspace.learner()
    assert workspace.evaluate(learner_id, "RULE-A").json()["outcome"] == "ineligible"

    body = lifecycle(workspace)

    assert body["credential_status"] == []
    assert body["issuance_over_time"] == []
    assert body["eligibility_outcomes"] == [{"key": "ineligible", "count": 1}]


def test_lifecycle_with_one_active_credential(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    workspace.issued_learner(course_id, "RULE-A")
    month = utc_now().strftime("%Y-%m")

    body = lifecycle(workspace)

    assert body["credential_status"] == [{"key": "active", "count": 1}]
    assert sum(row["count"] for row in body["issuance_over_time"]) == 1
    assert {row["period"] for row in body["issuance_over_time"]} <= {
        month,
        (utc_now() - timedelta(minutes=5)).strftime("%Y-%m"),
    }
    assert body["revocations_over_time"] == []
    assert body["eligibility_outcomes"] == [{"key": "eligible", "count": 1}]


def test_lifecycle_with_one_revoked_credential(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    _, credential_id = workspace.issued_learner(course_id, "RULE-A")
    workspace.revoke(credential_id)

    body = lifecycle(workspace)

    assert body["credential_status"] == [{"key": "revoked", "count": 1}]
    assert sum(row["count"] for row in body["issuance_over_time"]) == 1
    assert sum(row["count"] for row in body["revocations_over_time"]) == 1


def test_lifecycle_with_multiple_credentials_and_filters(workspace: Workspace) -> None:
    first_course = workspace.course()
    second_course = workspace.course()
    workspace.rule("RULE-A", first_course)
    workspace.rule("RULE-B", second_course)
    issued = [workspace.issued_learner(first_course, "RULE-A") for _ in range(3)]
    workspace.issued_learner(second_course, "RULE-B")
    workspace.revoke(issued[0][1])
    # One learner who is evaluated but not eligible, so both outcomes are present.
    assert workspace.evaluate(workspace.learner(), "RULE-A").json()["outcome"] == "ineligible"

    everything = lifecycle(workspace)
    assert everything["credential_status"] == [
        {"key": "active", "count": 3},
        {"key": "revoked", "count": 1},
    ]
    assert sum(row["count"] for row in everything["issuance_over_time"]) == 4
    assert sum(row["count"] for row in everything["revocations_over_time"]) == 1
    assert everything["eligibility_outcomes"] == [
        {"key": "eligible", "count": 4},
        {"key": "ineligible", "count": 1},
    ]

    # The buckets agree with the overview totals computed by a separate endpoint.
    overview = workspace.get("/reports/overview").json()
    assert overview["total_credentials_issued"] == 4
    assert overview["total_revoked_credentials"] == 1

    active_only = lifecycle(workspace, credential_status="active")
    assert active_only["credential_status"] == [{"key": "active", "count": 3}]
    assert sum(row["count"] for row in active_only["issuance_over_time"]) == 3
    assert active_only["revocations_over_time"] == []

    revoked_only = lifecycle(workspace, credential_status="revoked")
    assert revoked_only["credential_status"] == [{"key": "revoked", "count": 1}]
    assert sum(row["count"] for row in revoked_only["issuance_over_time"]) == 1
    assert sum(row["count"] for row in revoked_only["revocations_over_time"]) == 1

    first_course_only = lifecycle(workspace, course_id=first_course)
    assert first_course_only["credential_status"] == [
        {"key": "active", "count": 2},
        {"key": "revoked", "count": 1},
    ]
    assert first_course_only["eligibility_outcomes"] == [
        {"key": "eligible", "count": 3},
        {"key": "ineligible", "count": 1},
    ]
    second_course_only = lifecycle(workspace, course_id=second_course)
    assert second_course_only["credential_status"] == [{"key": "active", "count": 1}]
    assert second_course_only["revocations_over_time"] == []

    today = utc_now().date()
    in_window = lifecycle(
        workspace,
        date_from=(today - timedelta(days=1)).isoformat(),
        date_to=(today + timedelta(days=1)).isoformat(),
    )
    assert in_window["credential_status"] == everything["credential_status"]
    before_any_issue = lifecycle(
        workspace,
        date_from=(today - timedelta(days=30)).isoformat(),
        date_to=(today - timedelta(days=10)).isoformat(),
    )
    assert before_any_issue["credential_status"] == []
    assert before_any_issue["issuance_over_time"] == []
    assert before_any_issue["revocations_over_time"] == []
    assert before_any_issue["eligibility_outcomes"] == []


def test_lifecycle_rejects_unknown_status_filter(workspace: Workspace) -> None:
    course_id = workspace.course()
    workspace.rule("RULE-A", course_id)
    workspace.issued_learner(course_id, "RULE-A")

    assert workspace.get(LIFECYCLE, credential_status="expired").status_code == 422
