from typing import Callable
import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from app.core.security import decode_token
from app.database.session import get_db
from app.models.auth import User
from app.utils.enums import PermissionAction, ROLE_PERMISSIONS, UserRoleEnum
from app.modules.auth.service import is_token_blacklisted, get_user_role
from app.modules.auth.repository import get_user_by_id
from sqlalchemy.ext.asyncio import AsyncSession


_ROLE_HIERARCHY: dict[UserRoleEnum, int] = {
    UserRoleEnum.VIEWER:  0,
    UserRoleEnum.ANALYST: 1,
    UserRoleEnum.ADMIN:   2,
}

_bearer = HTTPBearer()


def _resolve_role(role: str | None) -> UserRoleEnum | None:
    """
    Safely coerce a raw string returned from the role cache / DB into a
    UserRoleEnum member.  Returns None when the string is falsy or unknown.
    """
    if not role:
        return None
    try:
        return UserRoleEnum(role)
    except ValueError:
        return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if await is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token revoked")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("typ") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user = await get_user_by_id(db, uuid.UUID(str(payload["user_id"])))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Allow only ADMIN-role users to proceed."""
    raw_role = await get_user_role(db, uuid.UUID(str(current_user.id)))
    role = _resolve_role(raw_role)
    if _ROLE_HIERARCHY.get(role, -1) < _ROLE_HIERARCHY[UserRoleEnum.ADMIN]:  # type: ignore[arg-type]
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def require_role(minimum_role: UserRoleEnum) -> Callable:
    """
    Factory that returns a FastAPI dependency enforcing a minimum role.

    Usage:
        @router.delete(
            "/resources/{resource_id}",
            dependencies=[Depends(require_role(UserRoleEnum.ADMIN))],
        )
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        raw_role = await get_user_role(db, uuid.UUID(str(current_user.id)))
        role = _resolve_role(raw_role)

        if role is None:
            raise HTTPException(status_code=403, detail="No role assigned to your account.")

        if _ROLE_HIERARCHY.get(role, -1) < _ROLE_HIERARCHY.get(minimum_role, 99):
            raise HTTPException(
                status_code=403,
                detail=f"This action requires at least the '{minimum_role}' role.",
            )
        return current_user

    return _check


def require_permission(action: PermissionAction) -> Callable:
    """
    Factory that returns a FastAPI dependency enforcing a specific action-level
    permission from the RBAC matrix.
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        raw_role = await get_user_role(db, uuid.UUID(str(current_user.id)))
        role = _resolve_role(raw_role)

        if role is None:
            raise HTTPException(status_code=403, detail="No role assigned to your account.")

        allowed_actions = ROLE_PERMISSIONS.get(role, set())
        if action not in allowed_actions:
            raise HTTPException(
                status_code=403,
                detail=f"The '{role.value}' role cannot perform '{action.value}'.",
            )

        return current_user

    return _check
