from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

PASSWORD_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16
PASSWORD_DIGEST_BYTES = 32


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS, PASSWORD_DIGEST_BYTES
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if encoded_hash is None:
        return False
    try:
        algorithm, iterations, salt_text, digest_text = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations_value = int(iterations)
        if not 100_000 <= iterations_value <= 2_000_000:
            return False
        salt = base64.b64decode(
            salt_text.encode("ascii"), altchars=b"-_", validate=True
        )
        expected = base64.b64decode(
            digest_text.encode("ascii"), altchars=b"-_", validate=True
        )
    except (ValueError, UnicodeError):
        return False
    if len(salt) != PASSWORD_SALT_BYTES or len(expected) != PASSWORD_DIGEST_BYTES:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations_value, len(expected)
    )
    return hmac.compare_digest(actual, expected)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    if expires_minutes is not None and expires_minutes <= 0:
        raise ValueError("Access-token lifetime must be positive.")
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(
        minutes=(
            settings.access_token_expire_minutes
            if expires_minutes is None
            else expires_minutes
        )
    )
    claims: dict[str, Any] = {"sub": subject, "iat": now, "exp": expiry}
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require_sub": True, "require_exp": True},
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired access token.") from exc
