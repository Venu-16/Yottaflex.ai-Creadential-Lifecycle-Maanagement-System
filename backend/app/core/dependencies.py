import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.dependencies import get_db
from app.models.domain import Role, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = UUID(claims["sub"])
    except (ValueError, KeyError, TypeError, JWTError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        roles = db.scalars(
            select(Role.role_code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user.id,
                UserRole.revoked_at.is_(None),
                Role.is_active.is_(True),
            )
        ).all()
        if not set(roles).intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The authenticated user lacks the required role.",
            )
        return user

    return dependency


NUL = "\x00"
_NUL_DETAIL = "Request contains an unsupported NUL character."


def _contains_nul(value: Any) -> bool:
    """Walk parsed JSON iteratively and report a NUL character in any key or string."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if NUL in item:
                return True
        elif isinstance(item, dict):
            for key, child in item.items():
                if isinstance(key, str) and NUL in key:
                    return True
                pending.append(child)
        elif isinstance(item, list):
            pending.extend(item)
    return False


async def reject_nul_characters(request: Request) -> None:
    """Reject NUL characters in the path, query string, or JSON body.

    PostgreSQL cannot store or compare text that contains NUL, so such input can
    never match or become a valid record. Rejecting it here returns a clear 422
    instead of letting the database driver fail part-way through a request.
    """
    if NUL in request.scope.get("path", "") or any(
        NUL in key or NUL in value for key, value in request.query_params.multi_items()
    ):
        raise HTTPException(status_code=422, detail=_NUL_DETAIL)
    body = await request.body()
    # A NUL can appear in valid JSON only as the escape sequence \u0000.
    if b"\\u0000" not in body:
        return
    try:
        parsed = json.loads(body)
    except (ValueError, RecursionError):
        return  # Not valid JSON: normal request validation reports it.
    if _contains_nul(parsed):
        raise HTTPException(status_code=422, detail=_NUL_DETAIL)
