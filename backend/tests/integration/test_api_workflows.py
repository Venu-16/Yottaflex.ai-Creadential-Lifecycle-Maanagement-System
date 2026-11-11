from __future__ import annotations

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database.base import Base
from app.database.dependencies import get_db
from app.main import app
from app.models.domain import (
    AssessmentAttempt,
    AuditEvent,
    CompletionRecord,
    Course,
    Credential,
    CredentialAward,
    CredentialScope,
    EligibilityDecision,
    Enrollment,
    IdempotencyRecord,
    Learner,
    Role,
    User,
    UserRole,
)


@pytest.fixture
def api_database() -> Session:
    database_url = os.environ.get("API_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("API_TEST_DATABASE_URL must point to a dedicated disposable test database.")
    database_name = database_url.rsplit("/", 1)[-1].split("?", 1)[0]
    if "test" not in database_name.lower():
        pytest.fail("Refusing to run API integration tests outside a database named for testing.")
    engine = create_engine(database_url, pool_pre_ping=True)
    if inspect(engine).get_table_names():
        engine.dispose()
        pytest.fail("API integration test database must be empty before the test run.")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def api_client(api_database: Session) -> TestClient:
    session_factory = sessionmaker(
        bind=api_database.get_bind(), autoflush=False, expire_on_commit=False
    )

    def override_get_db():
        session = session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def create_role_user(db: Session, role_code: str) -> tuple[User, str]:
    password = "local-test-password-2026"
    user = User(
        id=uuid4(),
        principal_key=f"test-{role_code.lower()}",
        password_hash=hash_password(password),
        display_name="API Test Actor",
        is_active=True,
    )
    role = Role(role_code=role_code, description="Test role", is_active=True)
    db.add_all([user, role])
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, granted_by_user_id=user.id))
    db.commit()
    return user, password


def authenticate(client: TestClient, principal: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"principal_key": principal, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_authentication_and_deny_by_default(
    api_client: TestClient, api_database: Session
) -> None:
    _, password = create_role_user(api_database, "SUPPORT_STAFF")
    principal = "test-support_staff"

    assert api_client.get("/api/v1/learners").status_code == 401
    assert (
        api_client.post(
            "/api/v1/auth/login",
            json={"principal_key": principal, "password": "wrong-password"},
        ).status_code
        == 401
    )
    token = authenticate(api_client, principal, password)
    profile = api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert profile.status_code == 200
    assert profile.json()["roles"] == ["SUPPORT_STAFF"]
    assert api_client.get(
        "/api/v1/learners", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 403
    assert api_client.post(
        "/api/v1/courses",
        json={"course_code": "DENIED", "title": "Denied"},
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 403
    valid_time = datetime.now(timezone.utc).isoformat()
    probe_id = str(uuid4())
    protected_requests = [
        ("get", "/api/v1/courses", None, {}),
        ("post", "/api/v1/learners", {"display_name": "Denied"}, {}),
        ("post", "/api/v1/courses", {"course_code": "DENIED", "title": "Denied"}, {}),
        ("get", "/api/v1/issuers", None, {}),
        ("post", "/api/v1/issuers", {"issuer_code": "DENIED", "name": "Denied"}, {}),
        ("patch", "/api/v1/issuers/DENIED", {"name": "Denied"}, {}),
        (
            "post",
            "/api/v1/issuers/DENIED/signing-keys",
            {
                "key_id": "denied-key",
                "public_key_base64": base64.b64encode(bytes(32)).decode(),
                "algorithm": "Ed25519",
                "valid_from": valid_time,
            },
            {},
        ),
        ("post", "/api/v1/issuers/DENIED/signing-keys/key/revoke", None, {}),
        ("get", "/api/v1/credential-rules", None, {}),
        (
            "post",
            "/api/v1/credential-rules",
            {
                "rule_code": "DENIED",
                "name": "Denied",
                "course_id": probe_id,
                "criteria": {},
                "effective_from": valid_time,
            },
            {},
        ),
        (
            "post",
            "/api/v1/credential-rules/DENIED/versions",
            {"course_id": probe_id, "criteria": {}, "effective_from": valid_time},
            {},
        ),
        ("get", "/api/v1/enrollments", None, {}),
        ("post", "/api/v1/enrollments", {"learner_id": probe_id, "course_id": probe_id}, {}),
        ("get", "/api/v1/completions", None, {}),
        ("post", "/api/v1/completions", {"enrollment_id": probe_id}, {}),
        ("get", "/api/v1/assessment-attempts", None, {}),
        (
            "post",
            "/api/v1/assessment-attempts",
            {
                "completion_record_id": probe_id,
                "assessment_key": "test",
                "status": "submitted",
                "submitted_at": valid_time,
            },
            {},
        ),
        (
            "post",
            "/api/v1/eligibility/evaluate",
            {"learner_id": probe_id, "rule_code": "DENIED"},
            {},
        ),
        ("get", "/api/v1/credentials", None, {}),
        ("get", "/api/v1/credentials/CRD-2026-000001", None, {}),
        ("get", "/api/v1/credentials/CRD-2026-000001/portable", None, {}),
        ("get", "/api/v1/credentials/CRD-2026-000001/history", None, {}),
        (
            "post",
            "/api/v1/credentials/issue",
            {"learner_id": probe_id, "rule_code": "DENIED"},
            {"Idempotency-Key": "support-denied-issue-01"},
        ),
        ("get", "/api/v1/revocations", None, {}),
        (
            "post",
            "/api/v1/revocations/CRD-2026-000001",
            {"reason_code": "DENIED"},
            {},
        ),
        ("get", "/api/v1/verification/requests", None, {}),
        ("get", "/api/v1/audit", None, {}),
        ("get", "/api/v1/reports/summary", None, {}),
    ]
    for method, path, body, extra_headers in protected_requests:
        response = api_client.request(
            method,
            path,
            json=body,
            headers={"Authorization": f"Bearer {token}", **extra_headers},
        )
        assert response.status_code == 403, f"{method.upper()} {path}: {response.text}"


def test_platform_administrator_cannot_issue_or_revoke(
    api_client: TestClient, api_database: Session
) -> None:
    _, password = create_role_user(api_database, "PLATFORM_ADMINISTRATOR")
    token = authenticate(api_client, "test-platform_administrator", password)
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "platform-cannot-issue-01",
    }

    assert api_client.post(
        "/api/v1/credentials/issue",
        json={"learner_id": str(uuid4()), "rule_code": "UNUSED"},
        headers=headers,
    ).status_code == 403
    assert api_client.post(
        "/api/v1/revocations/CRD-2026-000001",
        json={"reason_code": "UNAUTHORIZED"},
        headers=headers,
    ).status_code == 403


def test_authentication_rejects_bad_expired_and_inactive_tokens(
    api_client: TestClient, api_database: Session
) -> None:
    from jose import jwt
    from app.core.config import settings

    _, password = create_role_user(api_database, "SUPPORT_STAFF")
    principal = "test-support_staff"
    assert api_client.post(
        "/api/v1/auth/login",
        json={"principal_key": "missing-user", "password": password},
    ).status_code == 401
    assert api_client.post(
        "/api/v1/auth/login",
        json={"principal_key": principal, "password": "incorrect-password"},
    ).status_code == 401
    assert api_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer broken"}).status_code == 401

    expired = jwt.encode(
        {"sub": str(api_database.query(User).one().id), "exp": 1},
        settings.secret_key,
        algorithm="HS256",
    )
    assert api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
    ).status_code == 401
    invalid_signature = jwt.encode(
        {"sub": str(api_database.query(User).one().id), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "different-secret-key-at-least-32-bytes",
        algorithm="HS256",
    )
    assert api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid_signature}"}
    ).status_code == 401

    user = api_database.query(User).one()
    token = authenticate(api_client, principal, password)
    user.is_active = False
    api_database.commit()
    assert api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 401


def test_learner_cannot_issue_or_revoke_credentials(
    api_client: TestClient, api_database: Session
) -> None:
    user, password = create_role_user(api_database, "LEARNER")
    api_database.add(
        Learner(
            id=uuid4(),
            learner_id="LRN-111111",
            display_name="Linked Learner",
            user_id=user.id,
        )
    )
    api_database.commit()
    token = authenticate(api_client, "test-learner", password)
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "learner-cannot-issue-01",
    }
    assert api_client.get("/api/v1/learners/me/credentials", headers=headers).json() == []
    assert api_client.get(
        "/api/v1/learners/me/credentials?limit=101", headers=headers
    ).status_code == 422

    issue_response = api_client.post(
        "/api/v1/credentials/issue",
        json={"learner_id": str(uuid4()), "rule_code": "UNUSED"},
        headers=headers,
    )
    revoke_response = api_client.post(
        "/api/v1/revocations/CRD-2026-000001",
        json={"reason_code": "UNAUTHORIZED"},
        headers=headers,
    )
    assert issue_response.status_code == 403
    assert revoke_response.status_code == 403


def test_credential_award_uniqueness_is_enforced_concurrently_by_postgresql(
    api_database: Session,
) -> None:
    from sqlalchemy.exc import IntegrityError

    learner = Learner(id=uuid4(), learner_id="LRN-123456", display_name="Constraint Test")
    course = Course(id=uuid4(), course_code="CONSTRAINT-COURSE", title="Constraint Course")
    api_database.add_all([learner, course])
    api_database.flush()
    scope = CredentialScope(id=uuid4(), course_id=course.id)
    api_database.add(scope)
    api_database.commit()

    barrier = Barrier(2)

    def insert_duplicate_award() -> bool:
        with Session(bind=api_database.get_bind()) as session:
            session.add(
                CredentialAward(
                    id=uuid4(), learner_id=learner.id, credential_scope_id=scope.id
                )
            )
            barrier.wait(timeout=10)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: insert_duplicate_award(), range(2)))
    assert sum(outcomes) == 1
    assert api_database.query(CredentialAward).count() == 1

    api_database.add(
        Enrollment(
            id=uuid4(),
            learner_id=uuid4(),
            course_id=uuid4(),
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        api_database.commit()
    api_database.rollback()


def test_lifecycle_issue_idempotency_portable_verification_and_revocation(
    api_client: TestClient,
    api_database: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    _, password = create_role_user(api_database, "PLATFORM_ADMINISTRATOR")
    academic_role = Role(
        role_code="ACADEMIC_ADMINISTRATOR",
        description="Test issuance role",
        is_active=True,
    )
    api_database.add(academic_role)
    api_database.flush()
    platform_user = api_database.query(User).filter_by(
        principal_key="test-platform_administrator"
    ).one()
    api_database.add(
        UserRole(
            user_id=platform_user.id,
            role_id=academic_role.id,
            granted_by_user_id=platform_user.id,
        )
    )
    api_database.commit()
    token = authenticate(api_client, "test-platform_administrator", password)
    headers = {"Authorization": f"Bearer {token}"}

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
    monkeypatch.setattr(settings, "credential_signing_issuer_code", "TEST-ISSUER")
    monkeypatch.setattr(settings, "credential_signing_key_id", "test-key-1")

    issuer_response = api_client.post(
        "/api/v1/issuers",
        json={"issuer_code": "TEST-ISSUER", "name": "Test Issuer"},
        headers=headers,
    )
    assert issuer_response.status_code == 201
    key_response = api_client.post(
        "/api/v1/issuers/TEST-ISSUER/signing-keys",
        json={
            "key_id": "test-key-1",
            "public_key_base64": base64.b64encode(public_bytes).decode(),
            "algorithm": "Ed25519",
            "valid_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert key_response.status_code == 201
    assert "private" not in key_response.text.lower()
    naive_key = api_client.post(
        "/api/v1/issuers/TEST-ISSUER/signing-keys",
        json={
            "key_id": "naive-key",
            "public_key_base64": base64.b64encode(public_bytes).decode(),
            "algorithm": "Ed25519",
            "valid_from": "2026-11-10T12:00:00",
        },
        headers=headers,
    )
    assert naive_key.status_code == 422

    course_response = api_client.post(
        "/api/v1/courses",
        json={"course_code": "API-COURSE", "title": "API Course"},
        headers=headers,
    )
    assert course_response.status_code == 201
    course_id = course_response.json()["id"]
    updated_course = api_client.patch(
        f"/api/v1/courses/{course_id}",
        json={"title": "API Course Updated"},
        headers=headers,
    )
    assert updated_course.status_code == 200
    assert updated_course.json()["title"] == "API Course Updated"
    assert api_client.get("/api/v1/courses?limit=101", headers=headers).status_code == 422
    invalid_course = api_client.post(
        "/api/v1/courses",
        json={"course_code": "INVALID-STATUS", "title": "Invalid", "status": "unknown"},
        headers=headers,
    )
    assert invalid_course.status_code == 422
    learner_response = api_client.post(
        "/api/v1/learners",
        json={"display_name": "Test Learner"},
        headers=headers,
    )
    assert learner_response.status_code == 201
    learner_id = learner_response.json()["id"]
    updated_learner = api_client.patch(
        f"/api/v1/learners/{learner_id}",
        json={"display_name": "Test Learner Updated"},
        headers=headers,
    )
    assert updated_learner.status_code == 200
    assert updated_learner.json()["display_name"] == "Test Learner Updated"
    assert api_client.get("/api/v1/learners", headers=headers).status_code == 200
    assert api_client.get(f"/api/v1/learners/{learner_id}", headers=headers).status_code == 200
    assert api_client.get("/api/v1/issuers?limit=101", headers=headers).status_code == 422
    rule_response = api_client.post(
        "/api/v1/credential-rules",
        json={
            "rule_code": "API-RULE",
            "name": "API Rule",
            "course_id": course_id,
            "criteria": {
                "requires_completion": True,
                "minimum_score": 70,
                "score_scale": "0-100",
            },
            "attempt_selection_policy": "latest_graded",
            "effective_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert rule_response.status_code == 201
    invalid_rule = api_client.post(
        "/api/v1/credential-rules",
        json={
            "rule_code": "INVALID-RULE",
            "name": "Invalid Rule",
            "course_id": course_id,
            "criteria": {"requires_completion": True, "minimum_score": "NaN"},
            "attempt_selection_policy": "latest_graded",
            "effective_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert invalid_rule.status_code == 422
    naive_rule = api_client.post(
        "/api/v1/credential-rules",
        json={
            "rule_code": "NAIVE-DATE-RULE",
            "name": "Naive Date Rule",
            "course_id": course_id,
            "criteria": {"requires_completion": True},
            "effective_from": "2026-11-10T12:00:00",
        },
        headers=headers,
    )
    assert naive_rule.status_code == 422

    enrollment_response = api_client.post(
        "/api/v1/enrollments",
        json={"learner_id": learner_id, "course_id": course_id},
        headers=headers,
    )
    assert enrollment_response.status_code == 201
    naive_enrollment = api_client.post(
        "/api/v1/enrollments",
        json={
            "learner_id": learner_id,
            "course_id": course_id,
            "effective_from": "2026-11-10T12:00:00",
        },
        headers=headers,
    )
    assert naive_enrollment.status_code == 422
    completed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    invalid_completion = api_client.post(
        "/api/v1/completions",
        json={
            "enrollment_id": enrollment_response.json()["id"],
            "status": "completed",
            "started_at": completed_at.isoformat(),
            "completed_at": (completed_at - timedelta(minutes=1)).isoformat(),
        },
        headers=headers,
    )
    assert invalid_completion.status_code == 422
    completion_response = api_client.post(
        "/api/v1/completions",
        json={
            "enrollment_id": enrollment_response.json()["id"],
            "status": "completed",
            "started_at": (completed_at - timedelta(days=1)).isoformat(),
            "completed_at": completed_at.isoformat(),
        },
        headers=headers,
    )
    assert completion_response.status_code == 201
    attempt_response = api_client.post(
        "/api/v1/assessment-attempts",
        json={
            "completion_record_id": completion_response.json()["id"],
            "assessment_key": "final",
            "score": "85",
            "score_scale": "0-100",
            "result_code": "PASS",
            "status": "graded",
            "submitted_at": (completed_at - timedelta(minutes=30)).isoformat(),
            "graded_at": (completed_at - timedelta(minutes=10)).isoformat(),
        },
        headers=headers,
    )
    assert attempt_response.status_code == 201
    earlier_attempt = api_client.post(
        "/api/v1/assessment-attempts",
        json={
            "completion_record_id": completion_response.json()["id"],
            "assessment_key": "final",
            "score": "95",
            "score_scale": "0-100",
            "status": "graded",
            "submitted_at": (completed_at - timedelta(minutes=70)).isoformat(),
            "graded_at": (completed_at - timedelta(minutes=60)).isoformat(),
        },
        headers=headers,
    )
    assert earlier_attempt.status_code == 201
    ungraded_attempt = api_client.post(
        "/api/v1/assessment-attempts",
        json={
            "completion_record_id": completion_response.json()["id"],
            "assessment_key": "final",
            "status": "submitted",
            "submitted_at": (completed_at + timedelta(minutes=5)).isoformat(),
        },
        headers=headers,
    )
    assert ungraded_attempt.status_code == 201

    eligibility = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"learner_id": learner_id, "rule_code": "API-RULE"},
        headers=headers,
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["outcome"] == "eligible"
    first_decision_id = eligibility.json()["decision_id"]
    first_decision = api_database.get(EligibilityDecision, UUID(first_decision_id))
    selected_attempt_evidence = [
        item
        for item in first_decision.evidence_snapshot["evidence"]
        if "attempt_id" in item
    ]
    assert selected_attempt_evidence[0]["attempt_id"] == attempt_response.json()["id"]

    version_two = api_client.post(
        "/api/v1/credential-rules/API-RULE/versions",
        json={
            "course_id": course_id,
            "criteria": {"requires_completion": True, "minimum_score": 80},
            "attempt_selection_policy": "latest_graded",
            "effective_from": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert version_two.status_code == 201, version_two.text
    reevaluated = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"learner_id": learner_id, "rule_code": "API-RULE"},
        headers=headers,
    )
    assert reevaluated.status_code == 200
    assert reevaluated.json()["rule_version_id"] == version_two.json()["id"]
    assert first_decision.rule_version_id != UUID(reevaluated.json()["rule_version_id"])

    future_rule = api_client.post(
        "/api/v1/credential-rules",
        json={
            "rule_code": "FUTURE-RULE",
            "name": "Scheduled Rule",
            "course_id": course_id,
            "criteria": {"requires_completion": True, "minimum_score": 70},
            "attempt_selection_policy": "latest_graded",
            "effective_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert future_rule.status_code == 201
    scheduled = api_client.post(
        "/api/v1/credential-rules/FUTURE-RULE/versions",
        json={
            "course_id": course_id,
            "criteria": {"requires_completion": True, "minimum_score": 90},
            "attempt_selection_policy": "latest_graded",
            "effective_from": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert scheduled.status_code == 201, scheduled.text
    future_rule_evaluation = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"learner_id": learner_id, "rule_code": "FUTURE-RULE"},
        headers=headers,
    )
    assert future_rule_evaluation.status_code == 200
    assert future_rule_evaluation.json()["rule_version_id"] == future_rule.json()["id"]
    assert future_rule_evaluation.json()["outcome"] == "eligible"

    issue_headers = {**headers, "Idempotency-Key": "idempotency-key-e2e-001"}
    issue_request = {"learner_id": learner_id, "rule_code": "API-RULE"}
    credential_count_before_failure = api_database.query(Credential).count()
    monkeypatch.setattr(settings, "credential_signing_private_key", None)
    missing_key = api_client.post(
        "/api/v1/credentials/issue",
        json=issue_request,
        headers={**headers, "Idempotency-Key": "missing-signing-key-001"},
    )
    assert missing_key.status_code == 503
    assert api_database.query(Credential).count() == credential_count_before_failure
    monkeypatch.setattr(
        settings,
        "credential_signing_private_key",
        base64.b64encode(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )).decode(),
    )
    mismatched_key = api_client.post(
        "/api/v1/credentials/issue",
        json=issue_request,
        headers={**headers, "Idempotency-Key": "mismatched-signing-key-01"},
    )
    assert mismatched_key.status_code == 503
    assert api_database.query(Credential).count() == credential_count_before_failure
    monkeypatch.setattr(settings, "credential_signing_private_key", base64.b64encode(private_bytes).decode())

    decision_count_before_failure = api_database.query(EligibilityDecision).count()
    award_count_before_failure = api_database.query(CredentialAward).count()
    idempotency_count_before_failure = api_database.query(IdempotencyRecord).count()

    class FailingSigner:
        def public_key(self):
            return private_key.public_key()

        def sign(self, payload_bytes: bytes) -> bytes:
            raise RuntimeError("injected signing failure")

    class FailingPrivateKey:
        @staticmethod
        def from_private_bytes(seed: bytes) -> FailingSigner:
            return FailingSigner()

    with monkeypatch.context() as patch:
        patch.setattr(
            "app.services.credentials.Ed25519PrivateKey", FailingPrivateKey
        )
        signing_failure = api_client.post(
            "/api/v1/credentials/issue",
            json=issue_request,
            headers={**headers, "Idempotency-Key": "signing-failure-rollback-01"},
        )
    assert signing_failure.status_code == 503
    assert "injected signing failure" not in signing_failure.text
    assert api_database.query(Credential).count() == credential_count_before_failure
    assert api_database.query(CredentialAward).count() == award_count_before_failure
    assert api_database.query(EligibilityDecision).count() == decision_count_before_failure
    assert api_database.query(IdempotencyRecord).count() == idempotency_count_before_failure

    api_database.execute(text("""
        CREATE FUNCTION phase65_reject_credential() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'injected database failure' USING ERRCODE = '23514';
        END;
        $$;
    """))
    api_database.execute(text("""
        CREATE TRIGGER phase65_reject_credential_insert
        BEFORE INSERT ON credentials
        FOR EACH ROW EXECUTE FUNCTION phase65_reject_credential();
    """))
    api_database.commit()
    event_count_before_failure = api_database.query(AuditEvent).count()
    failed_database_issue = api_client.post(
        "/api/v1/credentials/issue",
        json=issue_request,
        headers={**headers, "Idempotency-Key": "database-failure-rollback-01"},
    )
    assert failed_database_issue.status_code == 409
    assert "injected database failure" not in failed_database_issue.text
    api_database.execute(text("DROP TRIGGER phase65_reject_credential_insert ON credentials"))
    api_database.execute(text("DROP FUNCTION phase65_reject_credential()"))
    api_database.commit()
    assert api_database.query(Credential).count() == credential_count_before_failure
    assert api_database.query(CredentialAward).count() == award_count_before_failure
    assert api_database.query(EligibilityDecision).count() == decision_count_before_failure
    assert api_database.query(IdempotencyRecord).count() == idempotency_count_before_failure
    assert api_database.query(AuditEvent).count() == event_count_before_failure

    def concurrent_issue():
        return api_client.post(
            "/api/v1/credentials/issue", json=issue_request, headers=issue_headers
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent_responses = list(executor.map(lambda _: concurrent_issue(), range(2)))
    assert [response.status_code for response in concurrent_responses] == [201, 201]
    issued = concurrent_responses[0]
    assert concurrent_responses[0].json()["id"] == concurrent_responses[1].json()["id"]
    credential_id = issued.json()["credential_id"]
    repeated = api_client.post(
        "/api/v1/credentials/issue", json=issue_request, headers=issue_headers
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == issued.json()["id"]
    assert issued.json()["credential_id"].startswith("CRD-")
    malformed_idempotency = api_client.post(
        "/api/v1/credentials/issue",
        json=issue_request,
        headers={**headers, "Idempotency-Key": "short"},
    )
    assert malformed_idempotency.status_code == 400
    reused_key = api_client.post(
        "/api/v1/credentials/issue",
        json={"learner_id": learner_id, "rule_code": "OTHER-RULE"},
        headers=issue_headers,
    )
    assert reused_key.status_code == 409
    duplicate_award = api_client.post(
        "/api/v1/credentials/issue",
        json=issue_request,
        headers={**headers, "Idempotency-Key": "idempotency-key-second-001"},
    )
    assert duplicate_award.status_code == 409
    unknown_credential = api_client.post(
        "/api/v1/verification/credential-id",
        params={"credential_id": "CRD-2026-999999"},
    )
    assert unknown_credential.status_code == 200
    assert unknown_credential.json()["overall_result"] == "NOT_FOUND"

    original_credential = api_database.query(Credential).one()
    duplicate_learner = Learner(
        id=uuid4(), learner_id="LRN-654321", display_name="Duplicate ID Probe"
    )
    duplicate_award_slot = CredentialAward(
        id=uuid4(),
        learner_id=duplicate_learner.id,
        credential_scope_id=original_credential.credential_scope_id,
    )
    original_decision = api_database.get(
        EligibilityDecision, original_credential.eligibility_decision_id
    )
    duplicate_decision = EligibilityDecision(
        id=uuid4(),
        learner_id=duplicate_learner.id,
        rule_version_id=original_credential.rule_version_id,
        credential_scope_id=original_credential.credential_scope_id,
        outcome="eligible",
        evaluator_type="user",
        evaluator_user_id=platform_user.id,
        evaluator_reference=str(platform_user.id),
        evaluator_version=original_decision.evaluator_version,
        attempt_selection_policy=original_decision.attempt_selection_policy,
        evidence_snapshot={},
        input_snapshot_digest=bytes(32),
    )
    api_database.add(duplicate_learner)
    api_database.flush()
    api_database.add_all([duplicate_award_slot, duplicate_decision])
    api_database.commit()
    from sqlalchemy.exc import IntegrityError

    api_database.add(
        Credential(
            id=uuid4(),
            credential_id=original_credential.credential_id,
            award_id=duplicate_award_slot.id,
            learner_id=duplicate_learner.id,
            credential_scope_id=original_credential.credential_scope_id,
            issuer_id=original_credential.issuer_id,
            rule_version_id=original_credential.rule_version_id,
            eligibility_decision_id=duplicate_decision.id,
            issued_at=original_credential.issued_at,
            payload_version=original_credential.payload_version,
            canonical_payload=original_credential.canonical_payload,
            sha256_digest=original_credential.sha256_digest,
            signature=original_credential.signature,
            signature_algorithm=original_credential.signature_algorithm,
            signing_key_id=original_credential.signing_key_id,
        )
    )
    with pytest.raises(IntegrityError):
        api_database.commit()
    api_database.rollback()
    assert api_database.query(Credential).count() == 1

    verified = api_client.post(
        "/api/v1/verification/credential-id",
        params={"credential_id": credential_id},
    )
    assert verified.status_code == 200
    assert verified.json()["overall_result"] == "VALID"
    assert "Test Learner" not in verified.text

    portable = api_client.get(
        f"/api/v1/credentials/{credential_id}/portable", headers=headers
    )
    assert portable.status_code == 200
    portable_verified = api_client.post(
        "/api/v1/verification/portable", json=portable.json()
    )
    assert portable_verified.status_code == 200
    assert portable_verified.json()["overall_result"] == "VALID"
    tampered_portable_payload = dict(portable.json()["payload"])
    tampered_portable_payload["course_code"] = "ALTERED-COURSE"
    tampered_portable = api_client.post(
        "/api/v1/verification/portable",
        json={
            "payload": tampered_portable_payload,
            "signature_base64": portable.json()["signature_base64"],
        },
    )
    assert tampered_portable.status_code == 200
    assert tampered_portable.json()["overall_result"] == "TAMPERED"
    bad_signature = base64.b64encode(bytes(64)).decode()
    invalid_signature = api_client.post(
        "/api/v1/verification/portable",
        json={"payload": portable.json()["payload"], "signature_base64": bad_signature},
    )
    assert invalid_signature.status_code == 200
    assert invalid_signature.json()["overall_result"] == "INVALID_SIGNATURE"
    malformed_key_claim = dict(portable.json()["payload"])
    malformed_key_claim["signing_key_id"] = {"not": "a string"}
    malformed_key_claim["credential_id"] = "CRD-2026-999998"
    malformed_key_verification = api_client.post(
        "/api/v1/verification/portable",
        json={
            "payload": malformed_key_claim,
            "signature_base64": portable.json()["signature_base64"],
        },
    )
    assert malformed_key_verification.status_code == 200
    assert malformed_key_verification.json()["overall_result"] == "UNVERIFIABLE"
    unknown_key_payload = dict(portable.json()["payload"])
    unknown_key_payload["signing_key_id"] = "missing-key"
    unknown_key_payload["credential_id"] = "CRD-2026-999999"
    unknown_key = api_client.post(
        "/api/v1/verification/portable",
        json={
            "payload": unknown_key_payload,
            "signature_base64": portable.json()["signature_base64"],
        },
    )
    assert unknown_key.status_code == 200
    assert unknown_key.json()["overall_result"] == "UNVERIFIABLE"

    rotated_private = Ed25519PrivateKey.generate()
    rotated_private_bytes = rotated_private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    rotated_public = rotated_private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    rotated_key_response = api_client.post(
        "/api/v1/issuers/TEST-ISSUER/signing-keys",
        json={
            "key_id": "test-key-2",
            "public_key_base64": base64.b64encode(rotated_public).decode(),
            "algorithm": "Ed25519",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "supersedes_key_id": key_response.json()["id"],
        },
        headers=headers,
    )
    assert rotated_key_response.status_code == 201, rotated_key_response.text
    assert "private" not in rotated_key_response.text.lower()
    monkeypatch.setattr(
        settings,
        "credential_signing_private_key",
        base64.b64encode(rotated_private_bytes).decode(),
    )
    monkeypatch.setattr(settings, "credential_signing_key_id", "test-key-2")
    historical_id_verification = api_client.post(
        "/api/v1/verification/credential-id", params={"credential_id": credential_id}
    )
    assert historical_id_verification.status_code == 200
    assert historical_id_verification.json()["overall_result"] == "VALID"
    historical_portable_verification = api_client.post(
        "/api/v1/verification/portable", json=portable.json()
    )
    assert historical_portable_verification.status_code == 200
    assert historical_portable_verification.json()["overall_result"] == "UNVERIFIABLE"

    revoked = api_client.post(
        f"/api/v1/revocations/{credential_id}",
        json={"reason_code": "TEST_REVOCATION", "reason_detail": "Integration test"},
        headers=headers,
    )
    assert revoked.status_code == 200
    verified_after_revocation = api_client.post(
        "/api/v1/verification/credential-id",
        params={"credential_id": credential_id},
    )
    assert verified_after_revocation.status_code == 200
    assert verified_after_revocation.json()["overall_result"] == "REVOKED"
    audit = api_client.get(
        "/api/v1/audit", params={"target_reference": credential_id}, headers=headers
    )
    assert audit.status_code == 200
    event_types = {event["event_type"] for event in audit.json()}
    assert {"credential.issued", "credential.revoked", "credential.verification"} <= event_types
    audit_rows_before = api_database.query(AuditEvent).count()
    duplicate_revocation = api_client.post(
        f"/api/v1/revocations/{credential_id}",
        json={"reason_code": "DUPLICATE"},
        headers=headers,
    )
    assert duplicate_revocation.status_code == 409
    assert api_database.query(AuditEvent).count() == audit_rows_before

    summary = api_client.get("/api/v1/reports/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_credentials"] == 1
    assert summary.json()["total_revocations"] == 1
    verification_report = api_client.get("/api/v1/reports/verification", headers=headers)
    assert verification_report.status_code == 200
    assert verification_report.json()["groups"]
    issuance_report = api_client.get("/api/v1/reports/issuance", headers=headers)
    assert issuance_report.status_code == 200
    revocation_report = api_client.get("/api/v1/reports/revocations", headers=headers)
    assert revocation_report.status_code == 200
    assert revocation_report.json()["by_reason"]["TEST_REVOCATION"] == 1
    verification_history = api_client.get("/api/v1/verification/requests", headers=headers)
    assert verification_history.status_code == 200
    assert all("learner_id" not in row for row in verification_history.json())

    tampered_payload = api_database.query(Credential).one()
    tampered_payload.canonical_payload += b" "
    api_database.commit()
    tampered_verification = api_client.post(
        "/api/v1/verification/credential-id",
        params={"credential_id": credential_id},
    )
    assert tampered_verification.status_code == 200
    assert tampered_verification.json()["overall_result"] == "TAMPERED"

    ineligible_learner = api_client.post(
        "/api/v1/learners",
        json={"display_name": "Learner Without Completion"},
        headers=headers,
    )
    assert ineligible_learner.status_code == 201
    ineligible_enrollment = api_client.post(
        "/api/v1/enrollments",
        json={"learner_id": ineligible_learner.json()["id"], "course_id": course_id},
        headers=headers,
    )
    assert ineligible_enrollment.status_code == 201
    rejected_issue = api_client.post(
        "/api/v1/credentials/issue",
        json={"learner_id": ineligible_learner.json()["id"], "rule_code": "API-RULE"},
        headers={**headers, "Idempotency-Key": "idempotency-key-ineligible-01"},
    )
    assert rejected_issue.status_code == 422
    missing_learner_evaluation = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"learner_id": str(uuid4()), "rule_code": "API-RULE"},
        headers=headers,
    )
    assert missing_learner_evaluation.status_code == 404
    missing_completion_attempt = api_client.post(
        "/api/v1/assessment-attempts",
        json={
            "completion_record_id": str(uuid4()),
            "assessment_key": "missing-completion",
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert missing_completion_attempt.status_code == 404

    no_assessment_learner = api_client.post(
        "/api/v1/learners",
        json={"display_name": "Learner Without Assessment"},
        headers=headers,
    )
    no_assessment_enrollment = api_client.post(
        "/api/v1/enrollments",
        json={"learner_id": no_assessment_learner.json()["id"], "course_id": course_id},
        headers=headers,
    )
    no_assessment_completion = api_client.post(
        "/api/v1/completions",
        json={
            "enrollment_id": no_assessment_enrollment.json()["id"],
            "status": "completed",
            "started_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert no_assessment_completion.status_code == 201
    no_assessment_evaluation = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"learner_id": no_assessment_learner.json()["id"], "rule_code": "API-RULE"},
        headers=headers,
    )
    assert no_assessment_evaluation.status_code == 200
    assert no_assessment_evaluation.json()["outcome"] == "ineligible"
    assert "MISSING_ASSESSMENT" in no_assessment_evaluation.json()["reason_codes"]

    below_threshold_learner = api_client.post(
        "/api/v1/learners", json={"display_name": "Learner Below Threshold"}, headers=headers
    )
    below_threshold_enrollment = api_client.post(
        "/api/v1/enrollments",
        json={"learner_id": below_threshold_learner.json()["id"], "course_id": course_id},
        headers=headers,
    )
    below_completed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    below_threshold_completion = api_client.post(
        "/api/v1/completions",
        json={
            "enrollment_id": below_threshold_enrollment.json()["id"],
            "status": "completed",
            "started_at": (below_completed_at - timedelta(days=1)).isoformat(),
            "completed_at": below_completed_at.isoformat(),
        },
        headers=headers,
    )
    below_threshold_attempt = api_client.post(
        "/api/v1/assessment-attempts",
        json={
            "completion_record_id": below_threshold_completion.json()["id"],
            "assessment_key": "final",
            "score": "79",
            "score_scale": "0-100",
            "status": "graded",
            "submitted_at": (below_completed_at - timedelta(hours=1)).isoformat(),
            "graded_at": (below_completed_at - timedelta(minutes=30)).isoformat(),
        },
        headers=headers,
    )
    assert below_threshold_attempt.status_code == 201
    below_threshold_evaluation = api_client.post(
        "/api/v1/eligibility/evaluate",
        json={"learner_id": below_threshold_learner.json()["id"], "rule_code": "API-RULE"},
        headers=headers,
    )
    assert below_threshold_evaluation.status_code == 200
    assert below_threshold_evaluation.json()["outcome"] == "ineligible"
    assert "ASSESSMENT_BELOW_THRESHOLD" in below_threshold_evaluation.json()["reason_codes"]
    before_ineligible_issue_count = api_database.query(Credential).count()
    below_threshold_issue = api_client.post(
        "/api/v1/credentials/issue",
        json={"learner_id": below_threshold_learner.json()["id"], "rule_code": "API-RULE"},
        headers={**headers, "Idempotency-Key": "idempotency-key-below-score-01"},
    )
    assert below_threshold_issue.status_code == 422
    assert api_database.query(Credential).count() == before_ineligible_issue_count

    assert api_database.query(EligibilityDecision).count() >= 3
    assert api_database.query(CompletionRecord).count() == 3
    assert api_database.query(AssessmentAttempt).count() == 4
