import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.config import settings
from app.database.session import get_db
from app.models.auth import User
from app.modules.auth.permission import get_current_user, require_permission
from app.modules.auth.schemas import (
    AssignRoleRequest,
    LoginRequest,
    RoleResponse,
    SignUpRequest,
    StandardResponse,
    UpdateRoleRequest,
    UpdateUserRequest,
    UserResponse,
    UserRoleResponse,
    UserWithRoleResponse,
)
from app.modules.auth.service import (
    # auth
    assign_user_role,
    deactivate_user,
    get_user_role_assignment,
    list_roles,
    login,
    revoke_user_role,
    signup,
    update_user_profile,
    get_user_role,
    # token
    blacklist_token,
    is_token_blacklisted,
    rotate_tokens,
    update_user_role,
)
from app.utils.enums import PermissionAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
router_author = APIRouter(prefix="/account", tags=["Authorization"])


@router.post("/signup", response_model=StandardResponse[UserResponse], status_code=201)
async def signup_api(
    request: SignUpRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    user = await signup(db, request.email, request.password, request.full_name)
    return StandardResponse(message="Account created successfully.", data=user)


@router.post("/login", response_model=StandardResponse)
async def login_api(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and set httpOnly cookie tokens."""
    tokens = await login(db, request.email, request.password)

    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )

    return StandardResponse(message="Login successful")


@router.post("/refresh", response_model=StandardResponse)
async def refresh_token_api(request: Request, response: Response):
    """Rotate the refresh token. Old refresh token is blacklisted immediately."""
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    if await is_token_blacklisted(refresh_token):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    result = rotate_tokens(refresh_token)

    # Blacklist the consumed refresh token before issuing new cookies
    try:
        old_token = result.pop("_old_refresh_token", None)
        if old_token:
            payload = decode_token(old_token)
            await blacklist_token(old_token, payload["exp"])
    except Exception:
        pass

    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,  # type: ignore
    )

    return StandardResponse(message="Token refreshed")


@router.post("/logout", response_model=StandardResponse)
async def logout(request: Request, response: Response):
    """Blacklist the current access token and clear all auth cookies."""
    access_token = request.cookies.get("access_token")

    if access_token:
        try:
            payload = decode_token(access_token)
            await blacklist_token(access_token, payload["exp"])
        except Exception:
            pass  

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")

    return StandardResponse(message="Logged out successfully")


@router.get("/me", response_model=StandardResponse[UserWithRoleResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's details including their assigned role."""
    raw_role = await get_user_role(db, current_user.id)  # type: ignore
    data = UserWithRoleResponse.model_validate(current_user)
    data.role = raw_role  # type: ignore
    return StandardResponse(message="User fetched successfully", data=data)


@router.patch("/me", response_model=StandardResponse[UserResponse])
async def update_profile(
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's display name or password."""
    updated = await update_user_profile(db, current_user, request)
    return StandardResponse(message="Profile updated.", data=updated)


@router.delete("/me", response_model=StandardResponse)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete the authenticated user's account."""
    result = await deactivate_user(db, current_user)
    return StandardResponse(message=result["message"])


@router_author.get(
    "",
    response_model=StandardResponse[list[RoleResponse]],
    dependencies=[Depends(require_permission(PermissionAction.ASSIGN_ROLES))],
)
async def get_roles(db: AsyncSession = Depends(get_db)):
    """List all available roles."""
    roles = await list_roles(db)
    return StandardResponse(message="Roles fetched successfully.", data=roles)
 
  
@router_author.get(
    "/users/{user_id}",
    response_model=StandardResponse[UserRoleResponse],
    dependencies=[Depends(require_permission(PermissionAction.MANAGE_USERS))],
)
async def get_role_for_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the current role assignment for a specific user."""
    role = await get_user_role_assignment(db, user_id)
    return StandardResponse(message="User role fetched successfully.", data=role)
 
 
@router_author.post(
    "/users",
    response_model=StandardResponse[UserRoleResponse],
    status_code=201,
    dependencies=[Depends(require_permission(PermissionAction.ASSIGN_ROLES))],
)
async def assign_role_to_user(
    request: AssignRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Assign a role to a user who currently has none."""
    role = await assign_user_role(db, request.user_id, request.role)
    return StandardResponse(message="Role assigned successfully.", data=role)
 
 
@router_author.patch(
    "/users/{user_id}",
    response_model=StandardResponse[UserRoleResponse],
    dependencies=[Depends(require_permission(PermissionAction.ASSIGN_ROLES))],
)
async def update_role_for_user(
    user_id: uuid.UUID,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Change the role of a user who already has one."""
    role = await update_user_role(db, user_id, request.role)
    return StandardResponse(message="Role updated successfully.", data=role)
 
 
@router_author.delete(
    "/users/{user_id}",
    response_model=StandardResponse,
    dependencies=[Depends(require_permission(PermissionAction.ASSIGN_ROLES))],
)
async def revoke_role_from_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a user's role assignment entirely."""
    await revoke_user_role(db, user_id)
    return StandardResponse(message="Role revoked successfully.")
