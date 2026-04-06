import re
import uuid
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.utils.enums import UserRoleEnum, UserStatus


DataT = TypeVar("DataT")


class StandardResponse(BaseModel, Generic[DataT]):
    """
    Every endpoint returns:
        { "success": true, "message": "...", "data": { ... } }
    """
    success: bool = True
    message: str = "OK"
    data: Optional[DataT] = None


_PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#])[A-Za-z\d@$!%*?&_\-#]{8,128}$"
)


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255, strip_whitespace=True) # type: ignore

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not _PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be 8-128 chars and contain uppercase, lowercase, "
                "digit, and special character (@$!%*?&_-#)."
            )
        return v

    @field_validator("full_name")
    @classmethod
    def no_numeric_only_name(cls, v: str) -> str:
        if v.strip().isdigit():
            raise ValueError("full_name must not be numeric only.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    # Keep max generous on login — never hint on failures
    password: str = Field(min_length=1, max_length=128)


class UpdateUserRequest(BaseModel):
    """Partial profile update — all fields optional."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255, strip_whitespace=True) # type: ignore
    old_password: Optional[str] = Field(default=None, min_length=1, max_length=128)
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def password_change_requires_both(self) -> "UpdateUserRequest":
        has_old = bool(self.old_password)
        has_new = bool(self.new_password)
        if has_old ^ has_new:
            raise ValueError("Both old_password and new_password are required to change password.")
        if self.new_password and not _PASSWORD_REGEX.match(self.new_password):
            raise ValueError(
                "new_password must be 8-128 chars and contain uppercase, lowercase, "
                "digit, and special character."
            )
        return self


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Safe user projection — never includes hashed_password."""
    id: uuid.UUID
    email: str
    full_name: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class UserWithRoleResponse(UserResponse):
    """Extends UserResponse with the user's assigned role."""
    role: Optional[UserRoleEnum] = None

class RoleResponse(BaseModel):
    """Public projection of a Role row."""
    id: int
    name: UserRoleEnum
    created_at: datetime
 
    model_config = {"from_attributes": True}
 
 
class AssignRoleRequest(BaseModel):
    user_id: uuid.UUID
    role: UserRoleEnum
 
 
class UpdateRoleRequest(BaseModel):
    role: UserRoleEnum
 
 
class UserRoleResponse(BaseModel):
    """Public projection of a UserRole assignment."""
    id: int
    user_id: uuid.UUID
    role: RoleResponse
 
    model_config = {"from_attributes": True}