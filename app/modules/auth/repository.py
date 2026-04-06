import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Role, User, UserRole
from app.utils.enums import UserRoleEnum, UserStatus


logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Lookup by email; excludes soft-deleted users."""
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Lookup by primary key; excludes soft-deleted users."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def create_user(db: AsyncSession, user: User) -> User:
    """Persist a new User row. Caller must handle IntegrityError for duplicate emails."""
    db.add(user)
    await db.commit()
    await db.refresh(user)  # populate server-generated columns (created_at, etc.)
    logger.info("Created user id=%s email=%s", user.id, user.email)
    return user


async def update_user(db: AsyncSession, user: User, **fields) -> User:
    """
    Apply arbitrary column updates to an existing User instance.
    Example:
        await update_user(db, user, full_name="Alice", hashed_password="...")
    """
    for key, value in fields.items():
        if not hasattr(user, key):
            raise ValueError(f"User has no column '{key}'")
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    logger.info("Updated user id=%s fields=%s", user.id, list(fields.keys()))
    return user


async def soft_delete_user(db: AsyncSession, user: User) -> None:
    """Mark the account as deleted without removing the row (preserves audit trail)."""
    user.deleted_at = datetime.now(timezone.utc)  # type: ignore
    user.status = UserStatus.INACTIVE  # type: ignore
    await db.commit()
    logger.info("Soft-deleted user id=%s", user.id)

async def get_all_roles(db: AsyncSession) -> list[Role]:
    """Return all role rows ordered by id (insertion order = hierarchy order)."""
    result = await db.execute(select(Role).order_by(Role.id))
    return list(result.scalars().all())
 
 
async def get_role_by_name(db: AsyncSession, name: UserRoleEnum) -> Optional[Role]:
    """Lookup a Role row by its enum value."""
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalars().first()
 
 
async def seed_roles(db: AsyncSession) -> None:
    """
    Idempotently insert all UserRoleEnum values into the roles table.
    Safe to call on every startup — skips roles that already exist.
    """
    existing_result = await db.execute(select(Role.name))
    existing = {row for row in existing_result.scalars().all()}
 
    new_roles = [
        Role(name=role)
        for role in UserRoleEnum
        if role not in existing
    ]
 
    if new_roles:
        db.add_all(new_roles)
        await db.commit()
        logger.info("Seeded %d role(s): %s", len(new_roles), [r.name for r in new_roles])
    else:
        logger.debug("Role seeding skipped — all roles already exist.")
 
  
async def get_user_role_row(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[UserRole]:
    """Return the UserRole assignment for a user, or None if unassigned."""
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    return result.scalars().first()
 
 
async def assign_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRoleEnum,
) -> UserRole:
    """
    Assign a role to a user. Raises ValueError if the user already has a role
    (use update_role to change it) or if the target role doesn't exist.
    """
    existing = await get_user_role_row(db, user_id)
    if existing:
        raise ValueError(f"User already has role '{existing.role.name}'. Use update to change it.")
 
    role_row = await get_role_by_name(db, role)
    if not role_row:
        raise ValueError(f"Role '{role}' not found. Ensure roles are seeded.")
 
    user_role = UserRole(user_id=user_id, role_id=role_row.id)
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)
    logger.info("Assigned role=%s to user_id=%s", role, user_id)
    return user_role
 
 
async def update_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    new_role: UserRoleEnum,
) -> UserRole:
    """
    Change an existing role assignment. Raises ValueError if the user has no
    role assigned yet (use assign_role) or if the new role doesn't exist.
    """
    user_role = await get_user_role_row(db, user_id)
    if not user_role:
        raise ValueError("User has no role assigned. Use assign to set one.")
 
    role_row = await get_role_by_name(db, new_role)
    if not role_row:
        raise ValueError(f"Role '{new_role}' not found. Ensure roles are seeded.")
 
    user_role.role_id = role_row.id  # type: ignore
    await db.commit()
    await db.refresh(user_role)
    logger.info("Updated role to=%s for user_id=%s", new_role, user_id)
    return user_role
 
 
async def revoke_role(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Remove a user's role assignment entirely."""
    user_role = await get_user_role_row(db, user_id)
    if not user_role:
        raise ValueError("User has no role assigned.")
 
    await db.delete(user_role)
    await db.commit()
    logger.info("Revoked role for user_id=%s", user_id)