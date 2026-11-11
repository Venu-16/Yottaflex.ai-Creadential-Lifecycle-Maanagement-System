from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.database.connection import SessionLocal
from app.models.domain import Role, User, UserRole

ALLOWED_ROLES = {
    "PLATFORM_ADMINISTRATOR",
    "ACADEMIC_ADMINISTRATOR",
    "INSTRUCTOR",
    "SUPPORT_STAFF",
    "LEARNER",
    "THIRD_PARTY_VERIFIER",
}


def main() -> int:
    principal = (settings.demo_user_principal_key or "").strip()
    password = settings.demo_user_password or ""
    role_code = (settings.demo_user_role or "").strip().upper()
    display_name = (settings.demo_user_display_name or "").strip() or None
    if not principal or not password or role_code not in ALLOWED_ROLES:
        raise SystemExit(
            "Set DEMO_USER_PRINCIPAL_KEY, DEMO_USER_PASSWORD (12+ characters), "
            "and DEMO_USER_ROLE to one of: " + ", ".join(sorted(ALLOWED_ROLES))
        )
    password_hash = hash_password(password)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.principal_key == principal))
        if user is None:
            user = User(
                principal_key=principal,
                password_hash=password_hash,
                display_name=display_name,
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.password_hash = password_hash
            user.display_name = display_name
            user.is_active = True
        role = db.scalar(select(Role).where(Role.role_code == role_code))
        if role is None:
            role = Role(
                role_code=role_code,
                description="Locally bootstrapped demonstration role.",
                is_active=True,
            )
            db.add(role)
            db.flush()
        assignment = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
                UserRole.revoked_at.is_(None),
            )
        )
        if assignment is None:
            db.add(UserRole(user_id=user.id, role_id=role.id, granted_by_user_id=user.id))
        db.commit()
    print(f"Bootstrapped user {principal!r} with role {role_code}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
