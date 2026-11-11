"""Shared scenario helpers for the API integration tests.

The database fixtures are defined in ``test_api_workflows`` and re-exported here so
that every integration module uses the same isolated, disposable PostgreSQL database
(``API_TEST_DATABASE_URL``, empty before each test, dropped after it).
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import app
from app.models.domain import Role, User, UserRole

from .test_api_workflows import (  # noqa: F401  (fixtures re-exported for pytest)
    api_client,
    api_database,
    authenticate,
    create_role_user,
)

ISSUER_CODE = "TEST-ISSUER"
SIGNING_KEY_ID = "test-key-1"

# Text that must never appear in a response body, whatever the input was.
INTERNAL_MARKERS = (
    "psycopg",
    "sqlalchemy",
    "traceback",
    "character varying",
    "nul (0x00)",
    'file "',
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def assert_no_internal_details(response: Response) -> None:
    body = response.text.lower()
    for marker in INTERNAL_MARKERS:
        assert marker not in body, f"response leaked internal detail {marker!r}: {body[:200]}"


class Workspace:
    """An administrator session plus small builders for the credential workflow."""

    def __init__(self, client: TestClient, db: Session, headers: dict[str, str]) -> None:
        self.client = client
        self.db = db
        self.headers = headers
        self._sequence = count(1)

    def _next(self) -> int:
        return next(self._sequence)

    def post(self, path: str, body: Any = None, **kwargs: Any) -> Response:
        return self.client.post(f"/api/v1{path}", json=body, headers=self.headers, **kwargs)

    def patch(self, path: str, body: Any) -> Response:
        return self.client.patch(f"/api/v1{path}", json=body, headers=self.headers)

    def get(self, path: str, **params: Any) -> Response:
        return self.client.get(f"/api/v1{path}", params=params, headers=self.headers)

    def course(self, code: str | None = None) -> str:
        code = code or f"COURSE-{self._next():03d}"
        response = self.post("/courses", {"course_code": code, "title": f"Course {code}"})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def learner(self, name: str | None = None) -> str:
        response = self.post("/learners", {"display_name": name or f"Learner {self._next()}"})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def rule_request(self, rule_code: str, course_id: str, criteria: dict[str, Any]) -> Response:
        return self.post(
            "/credential-rules",
            {
                "rule_code": rule_code,
                "name": f"Rule {rule_code}",
                "course_id": course_id,
                "criteria": criteria,
                "attempt_selection_policy": "latest_graded",
                "effective_from": (utc_now() - timedelta(days=1)).isoformat(),
            },
        )

    def rule(self, rule_code: str, course_id: str, criteria: dict[str, Any] | None = None) -> str:
        response = self.rule_request(
            rule_code, course_id, criteria or {"requires_completion": True}
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def enroll(self, learner_id: str, course_id: str) -> str:
        response = self.post("/enrollments", {"learner_id": learner_id, "course_id": course_id})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def completion_request(
        self,
        enrollment_id: str,
        *,
        status: str = "completed",
        completed_at: datetime | None = None,
    ) -> Response:
        body: dict[str, Any] = {"enrollment_id": enrollment_id, "status": status}
        if status == "completed":
            body["completed_at"] = (completed_at or utc_now() - timedelta(hours=2)).isoformat()
        return self.post("/completions", body)

    def complete(self, enrollment_id: str, **kwargs: Any) -> str:
        response = self.completion_request(enrollment_id, **kwargs)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def attempt(
        self,
        completion_id: str,
        score: str,
        *,
        status: str = "graded",
        graded_at: datetime | None = None,
    ) -> str:
        graded = graded_at or utc_now() - timedelta(hours=3)
        body: dict[str, Any] = {
            "completion_record_id": completion_id,
            "assessment_key": "final",
            "status": status,
            "submitted_at": (graded - timedelta(minutes=30)).isoformat(),
        }
        if status == "graded":
            body.update(score=score, score_scale="0-100", graded_at=graded.isoformat())
        response = self.post("/assessment-attempts", body)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def evaluate(self, learner_id: str, rule_code: str) -> Response:
        return self.post("/eligibility/evaluate", {"learner_id": learner_id, "rule_code": rule_code})

    def issue(self, learner_id: str, rule_code: str) -> Response:
        return self.client.post(
            "/api/v1/credentials/issue",
            json={"learner_id": learner_id, "rule_code": rule_code},
            headers={**self.headers, "Idempotency-Key": f"support-issue-key-{self._next():06d}"},
        )

    def issued_learner(self, course_id: str, rule_code: str) -> tuple[str, str]:
        """Enroll, complete and issue. Returns (learner_id, credential_id)."""
        learner_id = self.learner()
        self.complete(self.enroll(learner_id, course_id))
        response = self.issue(learner_id, rule_code)
        assert response.status_code == 201, response.text
        return learner_id, response.json()["credential_id"]

    def revoke(self, credential_id: str) -> None:
        response = self.post(f"/revocations/{credential_id}", {"reason_code": "ADMIN_ERROR"})
        assert response.status_code == 200, response.text


@pytest.fixture
def workspace(
    api_client: TestClient,  # noqa: F811
    api_database: Session,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> Workspace:
    """Administrator with both admin roles and a registered, configured signing key."""
    _, password = create_role_user(api_database, "PLATFORM_ADMINISTRATOR")
    academic_role = Role(
        role_code="ACADEMIC_ADMINISTRATOR", description="Test issuance role", is_active=True
    )
    api_database.add(academic_role)
    api_database.flush()
    user = api_database.query(User).filter_by(principal_key="test-platform_administrator").one()
    api_database.add(
        UserRole(user_id=user.id, role_id=academic_role.id, granted_by_user_id=user.id)
    )
    api_database.commit()
    token = authenticate(api_client, "test-platform_administrator", password)
    space = Workspace(api_client, api_database, {"Authorization": f"Bearer {token}"})

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    monkeypatch.setattr(
        settings, "credential_signing_private_key", base64.b64encode(private_bytes).decode()
    )
    monkeypatch.setattr(settings, "credential_signing_issuer_code", ISSUER_CODE)
    monkeypatch.setattr(settings, "credential_signing_key_id", SIGNING_KEY_ID)
    assert space.post("/issuers", {"issuer_code": ISSUER_CODE, "name": "Test Issuer"}).status_code == 201
    assert (
        space.post(
            f"/issuers/{ISSUER_CODE}/signing-keys",
            {
                "key_id": SIGNING_KEY_ID,
                "public_key_base64": base64.b64encode(public_bytes).decode(),
                "algorithm": "Ed25519",
                "valid_from": (utc_now() - timedelta(days=1)).isoformat(),
            },
        ).status_code
        == 201
    )
    return space


@pytest.fixture
def lenient_client(api_client: TestClient) -> TestClient:  # noqa: F811
    """Client that returns HTTP 500 responses instead of re-raising server errors.

    Depends on ``api_client`` so that the isolated test database is installed first.
    """
    return TestClient(app, raise_server_exceptions=False)
