from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, verify_password
from app.database.dependencies import get_db
from app.models.domain import Role, User, UserRole
from app.schemas.api import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Exchange credentials for a JWT")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(
        select(User).where(
            User.principal_key == payload.principal_key,
            User.is_active.is_(True),
        )
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserResponse, summary="Return the authenticated user")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    roles = db.scalars(
        select(Role.role_code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user.id,
            UserRole.revoked_at.is_(None),
            Role.is_active.is_(True),
        )
        .order_by(Role.role_code)
    ).all()
    return UserResponse(
        id=user.id,
        principal_key=user.principal_key,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=roles,
    )
