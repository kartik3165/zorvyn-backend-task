from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import TIMESTAMP, Boolean, Column, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.models.utils import generate_uuid
from app.utils.enums import UserStatus, UserRoleEnum


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    role_assignments = relationship("UserRole", back_populates="user")
    records = relationship("FinancialRecord", back_populates="user")

    __table_args__ = (
        Index("idx_users_email", "email"), 
        Index("idx_users_not_deleted", "deleted_at"),
    )

    def __repr__(self):
        return f"<User {self.email}>"
    

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(Enum(UserRoleEnum), unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    users = relationship("UserRole", back_populates="role")

    __table_args__ = (
        Index("idx_roles_name", "name"),
    )

class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="users")

    __table_args__ = (
        Index("idx_user_roles_user_id", "user_id"),
        Index("idx_user_roles_role_id", "role_id"),
        Index("idx_user_roles_user_role", "user_id", "role_id"),
    )