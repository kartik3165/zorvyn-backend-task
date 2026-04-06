import logging
import time
import uuid
from typing import Dict, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import User, UserRole, Role
from app.modules.auth.schemas import RoleResponse, UpdateUserRequest, UserResponse, UserRoleResponse
from app.modules.auth.repository import assign_role, create_user, get_all_roles, get_user_by_email, get_user_role_row, revoke_role, soft_delete_user, update_role, update_user
from app.utils.enums import UserStatus, UserRoleEnum

logger = logging.getLogger(__name__)

_ACCESS_TYPE  = "access"
_REFRESH_TYPE = "refresh"
_ROLE_CACHE_TTL = 300
_MIN_TTL_SECONDS = 60


def generate_tokens(user) -> Dict[str, str]:
    """
    Issue a fresh access + refresh token pair.
    A 'typ' claim is embedded to prevent token-type confusion attacks.
    """
    base = {
        "user_id": str(user.id),
    }
    return {
        "access_token":  create_access_token({**base,  "typ": _ACCESS_TYPE}),
        "refresh_token": create_refresh_token({**base, "typ": _REFRESH_TYPE}),
    }


def rotate_tokens(refresh_token: str) -> Dict[str, str]:
    """
    Validate a refresh token and return a brand-new access + refresh pair.
    The caller (api.py) is responsible for blacklisting the old refresh token.

    Raises HTTP 401 on any validation failure.
    """
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    if payload.get("typ") != _REFRESH_TYPE:
        raise HTTPException(status_code=401, detail="Invalid token type.")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Malformed refresh token.")

    base = {"user_id": user_id}

    logger.info("Rotated tokens for user_id=%s", user_id)
    return {
        "access_token":       create_access_token({**base,  "typ": _ACCESS_TYPE}),
        "refresh_token":      create_refresh_token({**base, "typ": _REFRESH_TYPE}),
        "_old_refresh_token": refresh_token,
    }


async def blacklist_token(token: str, exp: int) -> None:
    """
    Store a revoked token in Redis until it expires naturally.

    Args:
        token: Raw JWT string.
        exp:   Unix timestamp from the token's 'exp' claim.
    """
    ttl = max(exp - int(time.time()), _MIN_TTL_SECONDS)
    await redis_client.set(token, "blacklisted", ex=ttl)
    logger.debug("Blacklisted token (ttl=%ds)", ttl)


async def is_token_blacklisted(token: str) -> bool:
    """Return True if the token has been revoked."""
    return await redis_client.get(token) is not None


def _role_cache_key(user_id: uuid.UUID) -> str:
    return f"perm:{user_id}"


async def get_user_role(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[str]:
    """
    Resolve a user's role using Redis as an L1 cache.
    Returns None when the user has no role assigned.
    """
    key = _role_cache_key(user_id)

    cached = await redis_client.get(key)
    if cached is not None:
        role = cached.decode("utf-8") if isinstance(cached, bytes) else cached
        logger.debug("Role cache HIT  user=%s role=%s", user_id, role)
        return role

    # Join UserRole → Role to get the role name
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .limit(1)
    )
    role_name = result.scalar_one_or_none()

    if role_name is None:
        return None

    # Enum value may be a string or enum instance
    role_str = role_name.value if hasattr(role_name, "value") else str(role_name) # type: ignore
    await redis_client.set(key, role_str, ex=_ROLE_CACHE_TTL)
    logger.debug("Role cache MISS user=%s role=%s", user_id, role_str)
    return role_str


async def get_user_role_or_raise(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> str:
    """Same as get_user_role but raises HTTP 403 when no role is found."""
    role = await get_user_role(db, user_id)
    if role is None:
        raise HTTPException(status_code=403, detail="No role assigned to this user.")
    return role


async def invalidate_role_cache(user_id: uuid.UUID) -> None:
    """
    Evict the cached role entry.
    Call this whenever a user's role is created, updated, or removed.
    """
    key = _role_cache_key(user_id)
    await redis_client.delete(key)
    logger.debug("Evicted role cache user=%s", user_id)


async def _assign_role(db: AsyncSession, user_id: uuid.UUID, role: UserRoleEnum) -> None:
    """
    Look up the Role row for the given enum value and create a UserRole assignment.
    Assumes Role rows are pre-seeded in the database.
    """
    result = await db.execute(select(Role).where(Role.name == role))
    role_row = result.scalars().first()
    if not role_row:
        raise RuntimeError(f"Role '{role}' not found in the database. Ensure roles are seeded.")
    db.add(UserRole(user_id=user_id, role_id=role_row.id))
    await db.commit()
    logger.info("Assigned role=%s to user_id=%s", role, user_id)


async def signup(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
) -> UserResponse:
    email = email.lower().strip()

    if await get_user_by_email(db, email):
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Please try a different email."
        )

    result = await db.execute(select(func.count()).select_from(User))
    is_first_user = result.scalar_one() == 0

    try:
        new_user = User(
            email=email,
            full_name=full_name.strip(),
            hashed_password=hash_password(password),
        )
        created = await create_user(db, new_user)

    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Registration failed. Please try a different email."
        )

    if is_first_user:
        await _assign_role(db, created.id, UserRoleEnum.ADMIN) # type: ignore
        logger.info("First user registered as ADMIN: %s", email)
    else:
        logger.info("New user registered: %s", email)

    await db.refresh(created)
    return UserResponse.model_validate(created)


async def login(db: AsyncSession, email: str, password: str) -> Dict[str, str]:
    email = email.lower().strip()
    user  = await get_user_by_email(db, email)

    if not user or not verify_password(password, user.hashed_password):  # type: ignore
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    if user.status != UserStatus.ACTIVE:  # type: ignore
        raise HTTPException(status_code=403, detail="Account is disabled. Contact support.")

    logger.info("User logged in: %s", email)
    return generate_tokens(user)


async def update_user_profile(
    db: AsyncSession,
    user: User,
    payload: UpdateUserRequest,
) -> UserResponse:
    """Apply profile changes. Password change requires old_password verification."""
    updates: dict = {}

    if payload.full_name:
        updates["full_name"] = payload.full_name.strip()

    if payload.new_password:
        if not verify_password(payload.old_password, user.hashed_password):  # type: ignore
            raise HTTPException(status_code=400, detail="Old password is incorrect.")
        if verify_password(payload.new_password, user.hashed_password):  # type: ignore
            raise HTTPException(status_code=400, detail="New password must differ from the current one.")
        updates["hashed_password"] = hash_password(payload.new_password)

    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided.")

    updated = await update_user(db, user, **updates)
    logger.info("User profile updated: id=%s fields=%s", user.id, list(updates.keys()))
    return UserResponse.model_validate(updated)


async def deactivate_user(db: AsyncSession, user: User) -> dict:
    """Soft-delete the user account."""
    await soft_delete_user(db, user)
    logger.info("User account deactivated: id=%s", user.id)
    return {"message": "Account deactivated successfully."}


async def list_roles(db: AsyncSession) -> list[RoleResponse]:
    """Return all available roles."""
    roles = await get_all_roles(db)
    return [RoleResponse.model_validate(r) for r in roles]
 
 
async def get_user_role_assignment(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserRoleResponse:
    """
    Return the current role assignment for a user.
    Raises 404 if no role is assigned.
    """
    user_role = await get_user_role_row(db, user_id)
    if not user_role:
        raise HTTPException(status_code=404, detail="No role assigned to this user.")
    return UserRoleResponse.model_validate(user_role)
 
 
async def assign_user_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRoleEnum,
) -> UserRoleResponse:
    """
    Assign a role to a user who currently has none.
    Raises 409 if the user already has a role.
    Raises 404 if the role enum value is not seeded in the DB.
    """
    try:
        user_role = await assign_role(db, user_id, role)
    except ValueError as e:
        msg = str(e)
        if "already has role" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=404, detail=msg)
 
    await invalidate_role_cache(user_id)
    logger.info("Role assigned: user_id=%s role=%s", user_id, role)
    return UserRoleResponse.model_validate(user_role)
 
 
async def update_user_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    new_role: UserRoleEnum,
) -> UserRoleResponse:
    """
    Change the role of a user who already has one.
    Raises 404 if the user has no role yet.
    """
    try:
        user_role = await update_role(db, user_id, new_role)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
 
    await invalidate_role_cache(user_id)
    logger.info("Role updated: user_id=%s new_role=%s", user_id, new_role)
    return UserRoleResponse.model_validate(user_role)
 
 
async def revoke_user_role(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """
    Remove a user's role assignment.
    Raises 404 if the user has no role to revoke.
    """
    try:
        await revoke_role(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
 
    await invalidate_role_cache(user_id)
    logger.info("Role revoked: user_id=%s", user_id)