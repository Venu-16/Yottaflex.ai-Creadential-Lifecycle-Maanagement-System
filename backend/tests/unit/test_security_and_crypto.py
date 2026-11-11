from __future__ import annotations

import base64
import hashlib
import math

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.security import (
    PASSWORD_DIGEST_BYTES,
    PASSWORD_ITERATIONS,
    PASSWORD_SALT_BYTES,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.eligibility import canonical_json


def test_password_hash_round_trip_and_wrong_password() -> None:
    encoded = hash_password("a sufficiently long password")

    assert encoded.startswith(f"pbkdf2_sha256${PASSWORD_ITERATIONS}$")
    assert verify_password("a sufficiently long password", encoded)
    assert not verify_password("a different password", encoded)
    assert not verify_password("a sufficiently long password", None)


@pytest.mark.parametrize(
    "encoded",
    [
        "invalid",
        "pbkdf2_sha1$600000$c2FsdA==$ZGlnZXN0",
        "pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0",
        "pbkdf2_sha256$100000$!!!!$ZGlnZXN0",
        "pbkdf2_sha256$100000$" + base64.urlsafe_b64encode(b"s" * PASSWORD_SALT_BYTES).decode() + "$",
        "pbkdf2_sha256$100000$"
        + base64.urlsafe_b64encode(b"s" * PASSWORD_SALT_BYTES).decode()
        + "$"
        + base64.urlsafe_b64encode(b"").decode(),
    ],
)
def test_malformed_password_hashes_fail_closed(encoded: str) -> None:
    assert not verify_password("", encoded)


def test_password_length_and_malformed_hash_fail_safely() -> None:
    with pytest.raises(ValueError, match="at least 12"):
        hash_password("short")
    assert not verify_password("password", "pbkdf2_sha256$not-a-number$x$y")


def test_settings_reject_weak_secret_and_nonpositive_token_lifetime() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://localhost/test", secret_key="short")
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/test",
            secret_key="replace-with-a-long-random-secret",
        )
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key-with-at-least-32-bytes",
            access_token_expire_minutes=0,
        )
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key-with-at-least-32-bytes",
            jwt_algorithm="HS512",
        )
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key-with-at-least-32-bytes",
            cors_origins="*",
        )


def test_jwt_round_trip_and_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    token = create_access_token("subject-1", expires_minutes=1)
    assert decode_access_token(token)["sub"] == "subject-1"

    with pytest.raises(ValueError, match="lifetime must be positive"):
        create_access_token("subject-1", expires_minutes=0)
    from jose import jwt

    from app.core.config import settings

    expired = jwt.encode(
        {"sub": "subject-1", "exp": 1},
        settings.secret_key,
        algorithm="HS256",
    )
    with pytest.raises(ValueError, match="Invalid or expired"):
        decode_access_token(expired)


def test_jwt_rejects_bad_signature_and_malformed_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    token = create_access_token("subject-1")
    monkeypatch.setattr(settings, "secret_key", "different-secret-key-at-least-32-bytes")

    with pytest.raises(ValueError, match="Invalid or expired"):
        decode_access_token(token)
    with pytest.raises(ValueError, match="Invalid or expired"):
        decode_access_token("not.a.jwt")


def test_canonical_json_and_sha256_are_deterministic() -> None:
    first = canonical_json({"z": 1, "a": "é"})
    second = canonical_json({"a": "é", "z": 1})

    assert first == second == '{"a":"é","z":1}'.encode()
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
    with pytest.raises(ValueError):
        canonical_json({"not_json_number": math.nan})


def test_ed25519_valid_and_invalid_signatures() -> None:
    private_key = Ed25519PrivateKey.generate()
    payload = canonical_json({"credential_id": "CRD-2026-000001"})
    signature = private_key.sign(payload)

    private_key.public_key().verify(signature, payload)
    with pytest.raises(InvalidSignature):
        private_key.public_key().verify(signature, payload + b" ")
    with pytest.raises(InvalidSignature):
        Ed25519PrivateKey.generate().public_key().verify(signature, payload)
    with pytest.raises(InvalidSignature):
        private_key.public_key().verify(signature[:-1] + bytes([signature[-1] ^ 1]), payload)
