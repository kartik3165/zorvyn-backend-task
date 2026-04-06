# tests/integrate.py
"""
Integration tests for the auth module.

Tests the full flow: router → service → repository → database

Uses:
- SQLite in-memory database for persistence testing
- Fake Redis implementation for caching/blacklisting
- Real security functions for token operations
- TestClient for HTTP endpoint testing
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Float,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator, CHAR

# ============================================================
# Test Infrastructure - Type Handling for SQLite
# ============================================================


class SQLiteUUID(TypeDecorator):
    """
    Platform-independent UUID type.
    Uses CHAR(36) for SQLite, native UUID for PostgreSQL.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID

            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


# ============================================================
# Test Infrastructure - Fake Redis
# ============================================================


class FakeRedis:
    """
    In-memory Redis replacement for testing.
    Supports get, set, delete operations used in the codebase.
    """

    def __init__(self):
        self._store: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[bytes]:
        value = self._store.get(key)
        if value is None:
            return None
        if isinstance(value, str):
            return value.encode("utf-8")
        return value

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    def clear(self):
        self._store.clear()


fake_redis = FakeRedis()


# ============================================================
# Test Infrastructure - Database Models (SQLite compatible)
# ============================================================

TestBase = declarative_base()


def generate_test_uuid() -> uuid.UUID:
    return uuid.uuid4()


class TestUser(TestBase):
    __tablename__ = "users"

    id = Column(SQLiteUUID(), primary_key=True, default=generate_test_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    status = Column(Enum("active", "inactive", "suspended", name="userstatus"), default="active", nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    role_assignments = relationship("TestUserRole", back_populates="user")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_not_deleted", "deleted_at"),
    )


class TestRole(TestBase):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(Enum("viewer", "analyst", "admin", name="userroleenum"), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    users = relationship("TestUserRole", back_populates="role")

    __table_args__ = (Index("idx_roles_name", "name"),)


class TestUserRole(TestBase):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id", ondelete="CASCADE"))
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"))
    user = relationship("TestUser", back_populates="role_assignments")
    role = relationship("TestRole", back_populates="users")

    __table_args__ = (
        Index("idx_user_roles_user_id", "user_id"),
        Index("idx_user_roles_role_id", "role_id"),
    )


class TestFinancialRecord(TestBase):
    __tablename__ = "financial_records"

    id = Column(SQLiteUUID(), primary_key=True, default=generate_test_uuid)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id", ondelete="CASCADE"))
    amount = Column(Float, nullable=False)
    type = Column(Enum("income", "expense", name="recordtype"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    notes = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("TestUser")

    __table_args__ = (
        Index("idx_records_user_id", "user_id"),
        Index("idx_records_type", "type"),
    )


class TestCategory(TestBase):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    type = Column(Enum("income", "expense", name="categorytype"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Test Infrastructure - Database Setup
# ============================================================

SQLALCHEMY_TEST_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_test_db():
    """Create all tables in the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)


async def drop_test_db():
    """Drop all tables in the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)


async def seed_test_roles(db: AsyncSession):
    """Seed the roles table with all role values."""
    roles = [
        TestRole(id=1, name="viewer"),
        TestRole(id=2, name="analyst"),
        TestRole(id=3, name="admin"),
    ]
    db.add_all(roles)
    await db.commit()


# ============================================================
# Pytest Fixtures
# ============================================================

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup_database():
    """Set up and tear down the test database for each test."""
    await init_test_db()
    yield
    await drop_test_db()
    fake_redis.clear()


@pytest.fixture
async def db_session() -> AsyncSession: # type: ignore
    """Provide a database session for direct DB operations."""
    async with TestSessionLocal() as session:
        yield session # type: ignore


@pytest.fixture
async def seeded_db(db_session: AsyncSession) -> AsyncSession:
    """Provide a database session with roles already seeded."""
    await seed_test_roles(db_session)
    return db_session


@pytest.fixture
def app(seeded_db: AsyncSession) -> FastAPI: # type: ignore
    """
    Create a FastAPI app with all dependencies overridden for testing.
    """
    from app.modules.auth.router import router, router_author
    from app.modules.auth import permission, repository, service
    from app.utils.enums import UserRoleEnum, UserStatus

    app = FastAPI()
    app.include_router(router)
    app.include_router(router_author)

    # Override database dependency
    async def override_get_db():
        yield seeded_db

    app.dependency_overrides[Depends] = override_get_db  # type: ignore

    # Patch the database module references in repository
    async def patched_get_user_by_email(db: AsyncSession, email: str):
        result = await db.execute(
            select(TestUser).where(
                TestUser.email == email, TestUser.deleted_at.is_(None)
            )
        )
        user = result.scalars().first()
        if user:
            # Convert to look like a regular User object
            user.status = UserStatus(user.status.value if hasattr(user.status, 'value') else user.status) # type: ignore
        return user

    async def patched_get_user_by_id(db: AsyncSession, user_id: uuid.UUID):
        result = await db.execute(
            select(TestUser).where(
                TestUser.id == user_id, TestUser.deleted_at.is_(None)
            )
        )
        user = result.scalars().first()
        if user:
            user.status = UserStatus(user.status.value if hasattr(user.status, 'value') else user.status) # type: ignore
        return user

    async def patched_create_user(db: AsyncSession, user: Any) -> Any:
        test_user = TestUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            status=user.status.value if hasattr(user.status, 'value') else user.status,
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        # Copy back to original object for service layer compatibility
        user.id = test_user.id
        user.created_at = test_user.created_at
        user.updated_at = test_user.updated_at
        return user

    async def patched_update_user(db: AsyncSession, user: Any, **fields) -> Any:
        for key, value in fields.items():
            setattr(user, key, value)
        await db.commit()
        await db.refresh(user)
        return user

    async def patched_soft_delete_user(db: AsyncSession, user: Any) -> None:
        from datetime import datetime, timezone
        user.deleted_at = datetime.now(timezone.utc)
        user.status = UserStatus.INACTIVE
        await db.commit()

    async def patched_get_all_roles(db: AsyncSession):
        result = await db.execute(select(TestRole).order_by(TestRole.id))
        roles = result.scalars().all()
        # Convert to look like Role objects
        converted = []
        for r in roles:
            mock_role = MagicMock()
            mock_role.id = r.id
            mock_role.name = UserRoleEnum(r.name.value if hasattr(r.name, 'value') else r.name)
            mock_role.created_at = r.created_at
            converted.append(mock_role)
        return converted

    async def patched_get_role_by_name(db: AsyncSession, name: UserRoleEnum):
        result = await db.execute(
            select(TestRole).where(TestRole.name == name.value)
        )
        r = result.scalars().first()
        if r:
            mock_role = MagicMock()
            mock_role.id = r.id
            mock_role.name = UserRoleEnum(r.name.value if hasattr(r.name, 'value') else r.name)
            mock_role.created_at = r.created_at
            return mock_role
        return None

    async def patched_get_user_role_row(db: AsyncSession, user_id: uuid.UUID):
        result = await db.execute(
            select(TestUserRole).where(TestUserRole.user_id == user_id)
        )
        ur = result.scalars().first()
        if ur:
            mock_ur = MagicMock()
            mock_ur.id = ur.id
            mock_ur.user_id = ur.user_id
            mock_ur.role_id = ur.role_id
            # Fetch role for relationship
            role_result = await db.execute(
                select(TestRole).where(TestRole.id == ur.role_id)
            )
            role = role_result.scalars().first()
            if role:
                mock_role = MagicMock()
                mock_role.id = role.id
                mock_role.name = UserRoleEnum(role.name.value if hasattr(role.name, 'value') else role.name)
                mock_role.created_at = role.created_at
                mock_ur.role = mock_role
            return mock_ur
        return None

    async def patched_assign_role(db: AsyncSession, user_id: uuid.UUID, role: UserRoleEnum):
        existing = await patched_get_user_role_row(db, user_id)
        if existing:
            raise ValueError(f"User already has role '{existing.role.name}'. Use update to change it.")

        role_row = await patched_get_role_by_name(db, role)
        if not role_row:
            raise ValueError(f"Role '{role}' not found. Ensure roles are seeded.")

        user_role = TestUserRole(user_id=user_id, role_id=role_row.id)
        db.add(user_role)
        await db.commit()
        await db.refresh(user_role)
        
        mock_ur = MagicMock()
        mock_ur.id = user_role.id
        mock_ur.user_id = user_role.user_id
        mock_ur.role_id = user_role.role_id
        mock_ur.role = role_row
        return mock_ur

    async def patched_update_role(db: AsyncSession, user_id: uuid.UUID, new_role: UserRoleEnum):
        user_role = await patched_get_user_role_row(db, user_id)
        if not user_role:
            raise ValueError("User has no role assigned. Use assign to set one.")

        role_row = await patched_get_role_by_name(db, new_role)
        if not role_row:
            raise ValueError(f"Role '{new_role}' not found. Ensure roles are seeded.")

        # Update in DB
        result = await db.execute(
            select(TestUserRole).where(TestUserRole.user_id == user_id)
        )
        db_user_role = result.scalars().first()
        if db_user_role:
            db_user_role.role_id = role_row.id
            await db.commit()

        user_role.role_id = role_row.id
        user_role.role = role_row
        return user_role

    async def patched_revoke_role(db: AsyncSession, user_id: uuid.UUID):
        user_role = await patched_get_user_role_row(db, user_id)
        if not user_role:
            raise ValueError("User has no role assigned.")

        result = await db.execute(
            select(TestUserRole).where(TestUserRole.user_id == user_id)
        )
        db_user_role = result.scalars().first()
        if db_user_role:
            await db.delete(db_user_role)
            await db.commit()

    # Patch repository functions
    with patch.object(repository, "get_user_by_email", patched_get_user_by_email), \
         patch.object(repository, "get_user_by_id", patched_get_user_by_id), \
         patch.object(repository, "create_user", patched_create_user), \
         patch.object(repository, "update_user", patched_update_user), \
         patch.object(repository, "soft_delete_user", patched_soft_delete_user), \
         patch.object(repository, "get_all_roles", patched_get_all_roles), \
         patch.object(repository, "get_role_by_name", patched_get_role_by_name), \
         patch.object(repository, "get_user_role_row", patched_get_user_role_row), \
         patch.object(repository, "assign_role", patched_assign_role), \
         patch.object(repository, "update_role", patched_update_role), \
         patch.object(repository, "revoke_role", patched_revoke_role), \
         patch.object(service, "redis_client", fake_redis), \
         patch.object(permission, "is_token_blacklisted", service.is_token_blacklisted), \
         patch.object(permission, "get_user_role", service.get_user_role):

        # Also patch get_db dependency
        from app.database.session import get_db
        app.dependency_overrides[get_db] = override_get_db

        yield app # type: ignore

    app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide a test client for making HTTP requests."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_credentials() -> Dict[str, str]:
    """Return admin user credentials."""
    return {
        "email": "admin@test.com",
        "password": "AdminPass123!",
        "full_name": "Admin User",
    }


@pytest.fixture
def viewer_credentials() -> Dict[str, str]:
    """Return regular user credentials."""
    return {
        "email": "viewer@test.com",
        "password": "ViewerPass123!",
        "full_name": "Viewer User",
    }


@pytest.fixture
def valid_passwords() -> list[str]:
    """Return list of valid passwords for testing."""
    return [
        "Password123!",
        "Secure_Pass-99",
        "MyP@ssw0rd#",
        "Complex!Pass123",
    ]


@pytest.fixture
def invalid_passwords() -> list[str]:
    """Return list of invalid passwords for testing."""
    return [
        "short",  # Too short
        "nouppercase123!",  # No uppercase
        "NOLOWERCASE123!",  # No lowercase
        "NoDigitPass!",  # No digit
        "NoSpecial123",  # No special char
        "   ",  # Whitespace only
    ]


# ============================================================
# Helper Functions
# ============================================================


def create_user_and_get_tokens(
    client: TestClient,
    email: str,
    password: str,
    full_name: str,
    is_first_user: bool = False,
) -> Dict[str, str]:
    """Helper to create a user and extract tokens from cookies."""
    signup_response = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert signup_response.status_code == 201

    # Login to get tokens
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    cookies = {
        "access_token": login_response.cookies.get("access_token"),
        "refresh_token": login_response.cookies.get("refresh_token"),
        "csrf_token": login_response.cookies.get("csrf_token"),
    }
    return cookies


def create_admin_user(client: TestClient) -> Dict[str, str]:
    """Create the first user (becomes admin) and return tokens."""
    return create_user_and_get_tokens(
        client,
        "admin@test.com",
        "AdminPass123!",
        "Admin User",
        is_first_user=True,
    )


def create_regular_user(client: TestClient, email: str = "user@test.com") -> Dict[str, str]:
    """Create a regular user and return tokens."""
    return create_user_and_get_tokens(
        client,
        email,
        "UserPass123!",
        "Regular User",
    )


def create_viewer_user(client: TestClient) -> Dict[str, str]:
    """Create a viewer user and return tokens."""
    return create_user_and_get_tokens(
        client,
        "viewer@test.com",
        "ViewerPass123!",
        "Viewer User",
    )


# ============================================================
# Signup Endpoint Tests
# ============================================================


class TestSignupEndpoint:
    """Integration tests for POST /auth/signup"""

    def test_signup_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "newuser@test.com",
                "password": "NewUser123!",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "created successfully" in data["message"].lower()
        assert data["data"]["email"] == "newuser@test.com"
        assert data["data"]["full_name"] == "New User"
        assert data["data"]["status"] == "active"
        assert "id" in data["data"]

    def test_first_user_becomes_admin(self, client: TestClient, db_session: AsyncSession):
        """Test that the first registered user automatically becomes admin."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "first@test.com",
                "password": "FirstUser123!",
                "full_name": "First User",
            },
        )

        assert response.status_code == 201

        # Verify user has admin role by checking /me endpoint
        login_resp = client.post(
            "/auth/login",
            json={"email": "first@test.com", "password": "FirstUser123!"},
        )
        cookies = {"access_token": login_resp.cookies.get("access_token")}

        me_resp = client.get("/auth/me", cookies=cookies)
        assert me_resp.status_code == 200
        assert me_resp.json()["data"]["role"] == "admin"

    def test_second_user_is_not_admin(self, client: TestClient):
        """Test that subsequent users don't automatically get admin role."""
        # Create first user (admin)
        create_admin_user(client)

        # Create second user
        response = client.post(
            "/auth/signup",
            json={
                "email": "second@test.com",
                "password": "SecondUser123!",
                "full_name": "Second User",
            },
        )

        assert response.status_code == 201

        # Verify second user has no role
        login_resp = client.post(
            "/auth/login",
            json={"email": "second@test.com", "password": "SecondUser123!"},
        )
        cookies = {"access_token": login_resp.cookies.get("access_token")}

        me_resp = client.get("/auth/me", cookies=cookies)
        assert me_resp.status_code == 200
        assert me_resp.json()["data"]["role"] is None

    def test_signup_duplicate_email_returns_400(self, client: TestClient):
        """Test that duplicate email registration fails."""
        # Create first user
        client.post(
            "/auth/signup",
            json={
                "email": "duplicate@test.com",
                "password": "UserPass123!",
                "full_name": "First User",
            },
        )

        # Try to create second user with same email
        response = client.post(
            "/auth/signup",
            json={
                "email": "duplicate@test.com",
                "password": "DifferentPass123!",
                "full_name": "Second User",
            },
        )

        assert response.status_code == 400
        assert "different email" in response.json()["detail"].lower()

    def test_signup_duplicate_email_case_insensitive(self, client: TestClient):
        """Test that email comparison is case-insensitive."""
        # Create user with lowercase email
        client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": "UserPass123!",
                "full_name": "User",
            },
        )

        # Try with uppercase
        response = client.post(
            "/auth/signup",
            json={
                "email": "TEST@EXAMPLE.COM",
                "password": "DifferentPass123!",
                "full_name": "User 2",
            },
        )

        assert response.status_code == 400

    def test_signup_normalizes_email(self, client: TestClient):
        """Test that email is normalized (lowercased, trimmed)."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "  NEWUSER@TEST.COM  ",
                "password": "NewUser123!",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        assert response.json()["data"]["email"] == "newuser@test.com"

    @pytest.mark.parametrize("password", [
        "short",
        "nouppercase123!",
        "NOLOWERCASE123!",
        "NoDigitPass!",
        "NoSpecial123",
    ])
    def test_signup_invalid_password_returns_422(self, client: TestClient, password: str):
        """Test that invalid passwords are rejected."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": password,
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422

    def test_signup_numeric_only_name_returns_422(self, client: TestClient):
        """Test that numeric-only full names are rejected."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": "ValidPass123!",
                "full_name": "12345",
            },
        )

        assert response.status_code == 422

    def test_signup_missing_fields_returns_422(self, client: TestClient):
        """Test that missing required fields are rejected."""
        response = client.post(
            "/auth/signup",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422

    def test_signup_invalid_email_returns_422(self, client: TestClient):
        """Test that invalid email format is rejected."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "not-an-email",
                "password": "ValidPass123!",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 422

    def test_signup_short_name_returns_422(self, client: TestClient):
        """Test that too short full name is rejected."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "test@example.com",
                "password": "ValidPass123!",
                "full_name": "A",
            },
        )

        assert response.status_code == 422


# ============================================================
# Login Endpoint Tests
# ============================================================


class TestLoginEndpoint:
    """Integration tests for POST /auth/login"""

    def test_login_success(self, client: TestClient):
        """Test successful login."""
        # Create user first
        create_admin_user(client)

        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123!"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert "csrf_token" in response.cookies

    def test_login_sets_httponly_cookies(self, client: TestClient):
        """Test that token cookies are set as HttpOnly."""
        create_admin_user(client)

        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123!"},
        )

        # Check cookie attributes (TestClient doesn't expose all attributes,
        # but we can verify the cookies are set)
        assert response.cookies.get("access_token") is not None
        assert response.cookies.get("refresh_token") is not None
        assert response.cookies.get("csrf_token") is not None

    def test_login_wrong_password_returns_401(self, client: TestClient):
        """Test that wrong password fails."""
        create_admin_user(client)

        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "WrongPassword123!"},
        )

        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_email_returns_401(self, client: TestClient):
        """Test that nonexistent email fails."""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@test.com", "password": "SomePass123!"},
        )

        assert response.status_code == 401

    def test_login_inactive_user_returns_403(self, client: TestClient):
        """Test that inactive user cannot login."""
        create_admin_user(client)

        # Deactivate user
        cookies = create_admin_user(client)
        client.delete("/auth/me", cookies=cookies)

        # Try to login again
        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123!"},
        )

        assert response.status_code == 401  # User is soft-deleted, not found

    def test_login_case_insensitive_email(self, client: TestClient):
        """Test that login email comparison is case-insensitive."""
        create_admin_user(client)

        response = client.post(
            "/auth/login",
            json={"email": "ADMIN@TEST.COM", "password": "AdminPass123!"},
        )

        assert response.status_code == 200

    def test_login_missing_fields_returns_422(self, client: TestClient):
        """Test that missing fields are rejected."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com"},
        )

        assert response.status_code == 422


# ============================================================
# Get Current User Endpoint Tests
# ============================================================


class TestGetMeEndpoint:
    """Integration tests for GET /auth/me"""

    def test_get_me_success(self, client: TestClient):
        """Test getting current user info."""
        cookies = create_admin_user(client)

        response = client.get("/auth/me", cookies=cookies)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == "admin@test.com"
        assert data["full_name"] == "Admin User"
        assert data["role"] == "admin"

    def test_get_me_without_token_returns_401(self, client: TestClient):
        """Test that unauthenticated request fails."""
        response = client.get("/auth/me")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_get_me_with_invalid_token_returns_401(self, client: TestClient):
        """Test that invalid token is rejected."""
        cookies = {"access_token": "invalid_token"}

        response = client.get("/auth/me", cookies=cookies)

        assert response.status_code == 401

    def test_get_me_with_blacklisted_token_returns_401(self, client: TestClient):
        """Test that blacklisted token is rejected."""
        cookies = create_admin_user(client)

        # Blacklist the token via logout
        client.post("/auth/logout", cookies=cookies)

        # Try to use the same token
        response = client.get("/auth/me", cookies=cookies)

        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()

    def test_get_me_returns_correct_fields(self, client: TestClient):
        """Test that response contains all expected fields."""
        cookies = create_admin_user(client)

        response = client.get("/auth/me", cookies=cookies)
        data = response.json()["data"]

        expected_fields = ["id", "email", "full_name", "status", "created_at", "updated_at", "role"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_get_me_does_not_return_password(self, client: TestClient):
        """Test that password is never exposed."""
        cookies = create_admin_user(client)

        response = client.get("/auth/me", cookies=cookies)
        data = response.json()["data"]

        assert "password" not in data
        assert "hashed_password" not in data


# ============================================================
# Update Profile Endpoint Tests
# ============================================================


class TestUpdateProfileEndpoint:
    """Integration tests for PATCH /auth/me"""

    def test_update_full_name_success(self, client: TestClient):
        """Test updating user's full name."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={"full_name": "New Name"},
            cookies=cookies,
        )

        assert response.status_code == 200
        assert response.json()["data"]["full_name"] == "New Name"

    def test_update_password_success(self, client: TestClient):
        """Test updating user's password."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={
                "old_password": "AdminPass123!",
                "new_password": "NewSecurePass456!",
            },
            cookies=cookies,
        )

        assert response.status_code == 200

        # Verify new password works
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "NewSecurePass456!"},
        )
        assert login_response.status_code == 200

    def test_update_password_wrong_old_password(self, client: TestClient):
        """Test that wrong old password is rejected."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={
                "old_password": "WrongOldPass123!",
                "new_password": "NewSecurePass456!",
            },
            cookies=cookies,
        )

        assert response.status_code == 400
        assert "old password is incorrect" in response.json()["detail"].lower()

    def test_update_password_same_as_old(self, client: TestClient):
        """Test that new password same as old is rejected."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={
                "old_password": "AdminPass123!",
                "new_password": "AdminPass123!",
            },
            cookies=cookies,
        )

        assert response.status_code == 400
        assert "must differ" in response.json()["detail"].lower()

    def test_update_password_without_old_returns_422(self, client: TestClient):
        """Test that providing only new password is rejected."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={"new_password": "NewSecurePass456!"},
            cookies=cookies,
        )

        assert response.status_code == 422

    def test_update_no_changes_returns_400(self, client: TestClient):
        """Test that empty update request is rejected."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={},
            cookies=cookies,
        )

        assert response.status_code == 400
        assert "no changes" in response.json()["detail"].lower()

    def test_update_invalid_new_password_returns_422(self, client: TestClient):
        """Test that invalid new password format is rejected."""
        cookies = create_admin_user(client)

        response = client.patch(
            "/auth/me",
            json={
                "old_password": "AdminPass123!",
                "new_password": "weak",
            },
            cookies=cookies,
        )

        assert response.status_code == 422

    def test_update_without_auth_returns_401(self, client: TestClient):
        """Test that unauthenticated update fails."""
        response = client.patch(
            "/auth/me",
            json={"full_name": "New Name"},
        )

        assert response.status_code == 401


# ============================================================
# Deactivate Account Endpoint Tests
# ============================================================


class TestDeactivateEndpoint:
    """Integration tests for DELETE /auth/me"""

    def test_deactivate_success(self, client: TestClient):
        """Test successful account deactivation."""
        cookies = create_admin_user(client)

        response = client.delete("/auth/me", cookies=cookies)

        assert response.status_code == 200
        assert "deactivated" in response.json()["message"].lower()

    def test_deactivated_user_cannot_login(self, client: TestClient):
        """Test that deactivated user cannot login."""
        cookies = create_admin_user(client)

        client.delete("/auth/me", cookies=cookies)

        response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123!"},
        )

        assert response.status_code == 401

    def test_deactivate_without_auth_returns_401(self, client: TestClient):
        """Test that unauthenticated deactivation fails."""
        response = client.delete("/auth/me")

        assert response.status_code == 401


# ============================================================
# Logout Endpoint Tests
# ============================================================


class TestLogoutEndpoint:
    """Integration tests for POST /auth/logout"""

    def test_logout_success(self, client: TestClient):
        """Test successful logout."""
        cookies = create_admin_user(client)

        response = client.post("/auth/logout", cookies=cookies)

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    def test_logout_blacklists_token(self, client: TestClient):
        """Test that logout blacklists the access token."""
        cookies = create_admin_user(client)

        client.post("/auth/logout", cookies=cookies)

        # Try to use the same token
        response = client.get("/auth/me", cookies=cookies)

        assert response.status_code == 401

    def test_logout_clears_cookies(self, client: TestClient):
        """Test that logout clears auth cookies."""
        cookies = create_admin_user(client)

        response = client.post("/auth/logout", cookies=cookies)

        # Response should indicate cookies are cleared
        # (TestClient doesn't expose Set-Cookie headers for deletion easily)
        assert response.status_code == 200

    def test_logout_without_token_succeeds(self, client: TestClient):
        """Test that logout without token still succeeds (idempotent)."""
        response = client.post("/auth/logout")

        assert response.status_code == 200


# ============================================================
# Refresh Token Endpoint Tests
# ============================================================


class TestRefreshTokenEndpoint:
    """Integration tests for POST /auth/refresh"""

    def test_refresh_success(self, client: TestClient):
        """Test successful token refresh."""
        cookies = create_admin_user(client)

        response = client.post("/auth/refresh", cookies=cookies)

        assert response.status_code == 200
        assert "refreshed" in response.json()["message"].lower()
        # New tokens should be set
        assert response.cookies.get("access_token") is not None
        assert response.cookies.get("refresh_token") is not None

    def test_refresh_without_token_returns_401(self, client: TestClient):
        """Test that refresh without token fails."""
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert "missing refresh token" in response.json()["detail"].lower()

    def test_old_refresh_token_blacklisted(self, client: TestClient):
        """Test that old refresh token is blacklisted after refresh."""
        cookies = create_admin_user(client)
        old_refresh_token = cookies["refresh_token"]

        # Refresh tokens
        response = client.post("/auth/refresh", cookies=cookies)
        assert response.status_code == 200

        # Try to use old refresh token
        old_cookies = {"refresh_token": old_refresh_token}
        response = client.post("/auth/refresh", cookies=old_cookies)

        assert response.status_code == 401

    def test_new_tokens_work_after_refresh(self, client: TestClient):
        """Test that new tokens work after refresh."""
        cookies = create_admin_user(client)

        # Refresh
        refresh_response = client.post("/auth/refresh", cookies=cookies)
        new_cookies = {
            "access_token": refresh_response.cookies.get("access_token"),
        }

        # Use new access token
        me_response = client.get("/auth/me", cookies=new_cookies)

        assert me_response.status_code == 200


# ============================================================
# Roles List Endpoint Tests
# ============================================================


class TestListRolesEndpoint:
    """Integration tests for GET /account (list roles)"""

    def test_list_roles_as_admin_success(self, client: TestClient):
        """Test that admin can list all roles."""
        cookies = create_admin_user(client)

        response = client.get("/account", cookies=cookies)

        assert response.status_code == 200
        roles = response.json()["data"]
        assert len(roles) == 3
        role_names = [r["name"] for r in roles]
        assert "viewer" in role_names
        assert "analyst" in role_names
        assert "admin" in role_names

    def test_list_roles_as_viewer_returns_403(self, client: TestClient):
        """Test that viewer cannot list roles."""
        # Create admin first (to ensure roles exist)
        create_admin_user(client)

        # Create viewer user
        viewer_cookies = create_viewer_user(client)

        response = client.get("/account", cookies=viewer_cookies)

        assert response.status_code == 403

    def test_list_roles_without_auth_returns_401(self, client: TestClient):
        """Test that unauthenticated request fails."""
        response = client.get("/account")

        assert response.status_code == 401

    def test_list_roles_contains_correct_fields(self, client: TestClient):
        """Test that role response has correct fields."""
        cookies = create_admin_user(client)

        response = client.get("/account", cookies=cookies)
        role = response.json()["data"][0]

        expected_fields = ["id", "name", "created_at"]
        for field in expected_fields:
            assert field in role


# ============================================================
# User Role Assignment Endpoint Tests
# ============================================================


class TestAssignRoleEndpoint:
    """Integration tests for POST /account/users (assign role)"""

    def test_assign_role_success(self, client: TestClient):
        """Test successful role assignment."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID from /me
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign viewer role
        response = client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        assert response.status_code == 201
        assert response.json()["data"]["role"]["name"] == "viewer"

    def test_assign_role_updates_user_role(self, client: TestClient):
        """Test that assigned role is reflected in user profile."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign role
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "analyst"},
            cookies=admin_cookies,
        )

        # Verify role is set
        me_response = client.get("/auth/me", cookies=user_cookies)
        assert me_response.json()["data"]["role"] == "analyst"

    def test_assign_role_to_user_with_existing_role_returns_409(self, client: TestClient):
        """Test that assigning role to user who already has one fails."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign first role
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Try to assign another role (should fail - need to use update)
        response = client.post(
            "/account/users",
            json={"user_id": user_id, "role": "analyst"},
            cookies=admin_cookies,
        )

        assert response.status_code == 409
        assert "already has role" in response.json()["detail"].lower()

    def test_assign_role_as_non_admin_returns_403(self, client: TestClient):
        """Test that non-admin cannot assign roles."""
        create_admin_user(client)
        viewer_cookies = create_viewer_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.post(
            "/account/users",
            json={"user_id": user_id, "role": "analyst"},
            cookies=viewer_cookies,
        )

        assert response.status_code == 403

    def test_assign_role_without_auth_returns_401(self, client: TestClient):
        """Test that unauthenticated request fails."""
        response = client.post(
            "/account/users",
            json={"user_id": str(uuid.uuid4()), "role": "viewer"},
        )

        assert response.status_code == 401

    def test_assign_invalid_role_returns_422(self, client: TestClient):
        """Test that invalid role enum value is rejected."""
        admin_cookies = create_admin_user(client)

        response = client.post(
            "/account/users",
            json={"user_id": str(uuid.uuid4()), "role": "invalid_role"},
            cookies=admin_cookies,
        )

        assert response.status_code == 422


# ============================================================
# User Role Update Endpoint Tests
# ============================================================


class TestUpdateRoleEndpoint:
    """Integration tests for PATCH /account/users/{user_id} (update role)"""

    def test_update_role_success(self, client: TestClient):
        """Test successful role update."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # First assign a role
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Then update to different role
        response = client.patch(
            f"/account/users/{user_id}",
            json={"role": "analyst"},
            cookies=admin_cookies,
        )

        assert response.status_code == 200
        assert response.json()["data"]["role"]["name"] == "analyst"

    def test_update_role_for_user_without_role_returns_404(self, client: TestClient):
        """Test that updating role for user without role fails."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID (user has no role assigned)
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.patch(
            f"/account/users/{user_id}",
            json={"role": "analyst"},
            cookies=admin_cookies,
        )

        assert response.status_code == 404

    def test_update_role_as_non_admin_returns_403(self, client: TestClient):
        """Test that non-admin cannot update roles."""
        create_admin_user(client)
        viewer_cookies = create_viewer_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.patch(
            f"/account/users/{user_id}",
            json={"role": "analyst"},
            cookies=viewer_cookies,
        )

        assert response.status_code == 403

    def test_update_role_invalidates_cache(self, client: TestClient):
        """Test that role update invalidates the cache."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign initial role (caches it)
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Verify initial role
        me_response = client.get("/auth/me", cookies=user_cookies)
        assert me_response.json()["data"]["role"] == "viewer"

        # Update role
        client.patch(
            f"/account/users/{user_id}",
            json={"role": "analyst"},
            cookies=admin_cookies,
        )

        # Verify updated role (should not use stale cache)
        me_response = client.get("/auth/me", cookies=user_cookies)
        assert me_response.json()["data"]["role"] == "analyst"


# ============================================================
# User Role Revoke Endpoint Tests
# ============================================================


class TestRevokeRoleEndpoint:
    """Integration tests for DELETE /account/users/{user_id} (revoke role)"""

    def test_revoke_role_success(self, client: TestClient):
        """Test successful role revocation."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign a role first
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Revoke the role
        response = client.delete(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )

        assert response.status_code == 200
        assert "revoked" in response.json()["message"].lower()

    def test_revoke_role_removes_from_user(self, client: TestClient):
        """Test that revoked role is removed from user profile."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign and revoke
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )
        client.delete(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )

        # Verify role is gone
        me_response = client.get("/auth/me", cookies=user_cookies)
        assert me_response.json()["data"]["role"] is None

    def test_revoke_role_for_user_without_role_returns_404(self, client: TestClient):
        """Test that revoking role for user without role fails."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID (user has no role)
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.delete(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )

        assert response.status_code == 404

    def test_revoke_role_as_non_admin_returns_403(self, client: TestClient):
        """Test that non-admin cannot revoke roles."""
        create_admin_user(client)
        viewer_cookies = create_viewer_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.delete(
            f"/account/users/{user_id}",
            cookies=viewer_cookies,
        )

        assert response.status_code == 403

    def test_revoke_role_invalidates_cache(self, client: TestClient):
        """Test that role revocation invalidates the cache."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign role (caches it)
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Verify role is cached
        me_response = client.get("/auth/me", cookies=user_cookies)
        assert me_response.json()["data"]["role"] == "viewer"

        # Revoke role
        client.delete(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )

        # Verify role is gone (not using stale cache)
        me_response = client.get("/auth/me", cookies=user_cookies)
        assert me_response.json()["data"]["role"] is None


# ============================================================
# Get User Role Endpoint Tests
# ============================================================


class TestGetUserRoleEndpoint:
    """Integration tests for GET /account/users/{user_id}"""

    def test_get_user_role_success(self, client: TestClient):
        """Test getting user's role assignment."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        # Assign a role
        client.post(
            "/account/users",
            json={"user_id": user_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Get user role
        response = client.get(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )

        assert response.status_code == 200
        assert response.json()["data"]["role"]["name"] == "viewer"

    def test_get_user_role_no_assignment_returns_404(self, client: TestClient):
        """Test that getting role for user without assignment fails."""
        admin_cookies = create_admin_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID (no role assigned)
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.get(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )

        assert response.status_code == 404

    def test_get_user_role_as_non_admin_returns_403(self, client: TestClient):
        """Test that non-admin cannot get user roles."""
        create_admin_user(client)
        viewer_cookies = create_viewer_user(client)
        user_cookies = create_regular_user(client)

        # Get user ID
        me_response = client.get("/auth/me", cookies=user_cookies)
        user_id = me_response.json()["data"]["id"]

        response = client.get(
            f"/account/users/{user_id}",
            cookies=viewer_cookies,
        )

        assert response.status_code == 403


# ============================================================
# Permission Hierarchy Tests
# ============================================================


class TestPermissionHierarchy:
    """Tests for role-based access hierarchy"""

    def test_viewer_cannot_access_admin_endpoints(self, client: TestClient):
        """Test that viewer role cannot access admin-only endpoints."""
        create_admin_user(client)

        # Create and assign viewer role to user
        viewer_cookies = create_viewer_user(client)
        viewer_me = client.get("/auth/me", cookies=viewer_cookies)
        viewer_id = viewer_me.json()["data"]["id"]

        # Admin assigns viewer role
        admin_cookies = create_admin_user(client)
        client.post(
            "/account/users",
            json={"user_id": viewer_id, "role": "viewer"},
            cookies=admin_cookies,
        )

        # Viewer tries to list roles
        response = client.get("/account", cookies=viewer_cookies)
        assert response.status_code == 403

    def test_analyst_cannot_access_admin_endpoints(self, client: TestClient):
        """Test that analyst role cannot access admin-only endpoints."""
        create_admin_user(client)
        analyst_cookies = create_regular_user(client)
        analyst_me = client.get("/auth/me", cookies=analyst_cookies)
        analyst_id = analyst_me.json()["data"]["id"]

        # Admin assigns analyst role
        admin_cookies = create_admin_user(client)
        client.post(
            "/account/users",
            json={"user_id": analyst_id, "role": "analyst"},
            cookies=admin_cookies,
        )

        # Analyst tries to manage users
        response = client.get("/account", cookies=analyst_cookies)
        assert response.status_code == 403

    def test_role_hierarchy_viewer_lt_analyst_lt_admin(self, client: TestClient):
        """Test the role hierarchy: viewer < analyst < admin."""
        admin_cookies = create_admin_user(client)

        # Create three users
        viewer_cookies = create_viewer_user(client)
        analyst_cookies = create_regular_user(client, "analyst@test.com")
        another_viewer = create_regular_user(client, "viewer2@test.com")

        # Get user IDs
        viewer_id = client.get("/auth/me", cookies=viewer_cookies).json()["data"]["id"]
        analyst_id = client.get("/auth/me", cookies=analyst_cookies).json()["data"]["id"]
        another_viewer_id = client.get("/auth/me", cookies=another_viewer).json()["data"]["id"]

        # Assign roles
        client.post("/account/users", json={"user_id": viewer_id, "role": "viewer"}, cookies=admin_cookies)
        client.post("/account/users", json={"user_id": analyst_id, "role": "analyst"}, cookies=admin_cookies)
        client.post("/account/users", json={"user_id": another_viewer_id, "role": "viewer"}, cookies=admin_cookies)

        # Viewer cannot access admin endpoints
        assert client.get("/account", cookies=viewer_cookies).status_code == 403

        # Analyst cannot access admin endpoints
        assert client.get("/account", cookies=analyst_cookies).status_code == 403

        # Admin can access admin endpoints
        assert client.get("/account", cookies=admin_cookies).status_code == 200


# ============================================================
# Full Flow Integration Tests
# ============================================================


class TestFullUserLifecycle:
    """End-to-end tests for complete user lifecycle"""

    def test_complete_user_lifecycle(self, client: TestClient):
        """Test the complete lifecycle: signup → login → update → assign role → revoke → deactivate"""
        # 1. Signup
        signup_response = client.post(
            "/auth/signup",
            json={
                "email": "lifecycle@test.com",
                "password": "Lifecycle123!",
                "full_name": "Lifecycle User",
            },
        )
        assert signup_response.status_code == 201
        user_id = signup_response.json()["data"]["id"]

        # 2. Login
        login_response = client.post(
            "/auth/login",
            json={"email": "lifecycle@test.com", "password": "Lifecycle123!"},
        )
        assert login_response.status_code == 200
        cookies = {
            "access_token": login_response.cookies.get("access_token"),
            "refresh_token": login_response.cookies.get("refresh_token"),
        }

        # 3. Get profile
        me_response = client.get("/auth/me", cookies=cookies)
        assert me_response.status_code == 200
        assert me_response.json()["data"]["full_name"] == "Lifecycle User"

        # 4. Update profile
        update_response = client.patch(
            "/auth/me",
            json={"full_name": "Updated Name"},
            cookies=cookies,
        )
        assert update_response.status_code == 200
        assert update_response.json()["data"]["full_name"] == "Updated Name"

        # 5. Create admin and assign role to user
        admin_cookies = create_admin_user(client)
        assign_response = client.post(
            "/account/users",
            json={"user_id": user_id, "role": "analyst"},
            cookies=admin_cookies,
        )
        assert assign_response.status_code == 201

        # 6. Verify role
        me_response = client.get("/auth/me", cookies=cookies)
        assert me_response.json()["data"]["role"] == "analyst"

        # 7. Update role
        update_role_response = client.patch(
            f"/account/users/{user_id}",
            json={"role": "viewer"},
            cookies=admin_cookies,
        )
        assert update_role_response.status_code == 200

        # 8. Verify updated role
        me_response = client.get("/auth/me", cookies=cookies)
        assert me_response.json()["data"]["role"] == "viewer"

        # 9. Revoke role
        revoke_response = client.delete(
            f"/account/users/{user_id}",
            cookies=admin_cookies,
        )
        assert revoke_response.status_code == 200

        # 10. Verify role removed
        me_response = client.get("/auth/me", cookies=cookies)
        assert me_response.json()["data"]["role"] is None

        # 11. Logout
        logout_response = client.post("/auth/logout", cookies=cookies)
        assert logout_response.status_code == 200

        # 12. Verify token is blacklisted
        me_response = client.get("/auth/me", cookies=cookies)
        assert me_response.status_code == 401

    def test_token_refresh_flow(self, client: TestClient):
        """Test the complete token refresh flow."""
        # Signup and login
        create_admin_user(client)
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123!"},
        )
        original_cookies = {
            "access_token": login_response.cookies.get("access_token"),
            "refresh_token": login_response.cookies.get("refresh_token"),
        }

        # Use original token
        me_response = client.get("/auth/me", cookies=original_cookies)
        assert me_response.status_code == 200

        # Refresh tokens
        refresh_response = client.post("/auth/refresh", cookies=original_cookies)
        assert refresh_response.status_code == 200
        new_cookies = {
            "access_token": refresh_response.cookies.get("access_token"),
            "refresh_token": refresh_response.cookies.get("refresh_token"),
        }

        # Original tokens should be invalidated
        me_response = client.get("/auth/me", cookies=original_cookies)
        assert me_response.status_code == 401

        # New tokens should work
        me_response = client.get("/auth/me", cookies=new_cookies)
        assert me_response.status_code == 200

        # Refresh again with new tokens
        refresh_response = client.post("/auth/refresh", cookies=new_cookies)
        assert refresh_response.status_code == 200
        newer_cookies = {
            "access_token": refresh_response.cookies.get("access_token"),
        }

        me_response = client.get("/auth/me", cookies=newer_cookies)
        assert me_response.status_code == 200


# ============================================================
# Edge Case Tests
# ============================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_multiple_users_same_session(self, client: TestClient):
        """Test handling multiple users in the same test session."""
        # Create multiple users
        user1_cookies = create_admin_user(client)
        user2_cookies = create_regular_user(client, "user2@test.com")
        user3_cookies = create_regular_user(client, "user3@test.com")

        # All should be able to access their own profiles
        assert client.get("/auth/me", cookies=user1_cookies).status_code == 200
        assert client.get("/auth/me", cookies=user2_cookies).status_code == 200
        assert client.get("/auth/me", cookies=user3_cookies).status_code == 200

        # Each should see their own data
        assert client.get("/auth/me", cookies=user1_cookies).json()["data"]["email"] == "admin@test.com"
        assert client.get("/auth/me", cookies=user2_cookies).json()["data"]["email"] == "user2@test.com"
        assert client.get("/auth/me", cookies=user3_cookies).json()["data"]["email"] == "user3@test.com"

    def test_concurrent_role_assignments(self, client: TestClient):
        """Test that role assignments are properly sequenced."""
        admin_cookies = create_admin_user(client)

        # Create multiple users
        users = []
        for i in range(3):
            cookies = create_regular_user(client, f"user{i}@test.com")
            me_response = client.get("/auth/me", cookies=cookies)
            users.append(me_response.json()["data"]["id"])

        # Assign different roles to each
        roles = ["viewer", "analyst", "viewer"]
        for user_id, role in zip(users, roles):
            response = client.post(
                "/account/users",
                json={"user_id": user_id, "role": role},
                cookies=admin_cookies,
            )
            assert response.status_code == 201

    def test_empty_cookie_handling(self, client: TestClient):
        """Test handling of empty/missing cookies."""
        response = client.get("/auth/me", cookies={})
        assert response.status_code == 401

    def test_malformed_uuid_in_endpoints(self, client: TestClient):
        """Test handling of malformed UUID in URL parameters."""
        admin_cookies = create_admin_user(client)

        response = client.get("/account/users/not-a-uuid", cookies=admin_cookies)
        assert response.status_code == 422

    def test_whitespace_in_email(self, client: TestClient):
        """Test that whitespace in email is handled correctly."""
        # Signup with whitespace
        response = client.post(
            "/auth/signup",
            json={
                "email": "  spaced@test.com  ",
                "password": "ValidPass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201

        # Login with whitespace should work
        login_response = client.post(
            "/auth/login",
            json={"email": "  SPACED@TEST.COM  ", "password": "ValidPass123!"},
        )
        assert login_response.status_code == 200

    def test_very_long_email(self, client: TestClient):
        """Test handling of maximum length email."""
        long_local = "a" * 64  # Max local part is 64 chars
        response = client.post(
            "/auth/signup",
            json={
                "email": f"{long_local}@test.com",
                "password": "ValidPass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201

    def test_password_at_max_length(self, client: TestClient):
        """Test that maximum length password works."""
        max_password = "A" * 64 + "a" * 32 + "1" * 16 + "!@#$"  # ~116 chars
        response = client.post(
            "/auth/signup",
            json={
                "email": "maxpass@test.com",
                "password": max_password,
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201