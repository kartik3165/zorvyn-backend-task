# tests/units.py
"""
Comprehensive unit tests for permission.py, service.py, and repository.py

Uses pytest with async support, pytest-mock, and unittest.mock.
All external dependencies (DB, Redis, security functions) are mocked.
"""

import uuid
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.modules.auth import repository, service, permission
from app.utils.enums import UserRoleEnum, UserStatus, PermissionAction


# ============================================================
# Pytest Configuration
# ============================================================

pytestmark = pytest.mark.asyncio


# ============================================================
# Shared Fixtures
# ============================================================

@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession for database operations."""
    return AsyncMock()


@pytest.fixture
def user_id() -> uuid.UUID:
    """Generate a consistent UUID for tests."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def mock_user(user_id: uuid.UUID) -> MagicMock:
    """Create a mock User object with sensible defaults."""
    user = MagicMock()
    user.id = user_id
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.hashed_password = "hashed_password_123"
    user.status = UserStatus.ACTIVE
    user.deleted_at = None
    user.created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    user.updated_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return user


@pytest.fixture
def mock_role() -> MagicMock:
    """Create a mock Role object for ADMIN."""
    role = MagicMock()
    role.id = 1
    role.name = UserRoleEnum.ADMIN
    role.created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return role


@pytest.fixture
def mock_viewer_role() -> MagicMock:
    """Create a mock Role object for VIEWER."""
    role = MagicMock()
    role.id = 2
    role.name = UserRoleEnum.VIEWER
    role.created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return role


@pytest.fixture
def mock_user_role(user_id: uuid.UUID, mock_role: MagicMock) -> MagicMock:
    """Create a mock UserRole assignment."""
    user_role = MagicMock()
    user_role.id = 1
    user_role.user_id = user_id
    user_role.role_id = mock_role.id
    user_role.role = mock_role
    return user_role


@pytest.fixture
def mock_db_result_none() -> MagicMock:
    """Create a mock DB result that returns None from scalars().first()."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    return result


@pytest.fixture
def mock_db_result_value(value: object) -> MagicMock:
    """Create a mock DB result that returns a value from scalars().first()."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    return result


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock FastAPI Request object."""
    request = MagicMock()
    request.cookies = MagicMock()
    return request


# ============================================================
# Helper Functions
# ============================================================

def create_mock_execute_result(scalars_return=None, scalar_one_or_none=None) -> MagicMock:
    """Helper to create a mock execute result with flexible return values."""
    result = MagicMock()
    
    if scalars_return is not None:
        if isinstance(scalars_return, list):
            result.scalars.return_value.all.return_value = scalars_return
        else:
            result.scalars.return_value.first.return_value = scalars_return
    
    if scalar_one_or_none is not None:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    
    return result


# ============================================================
# REPOSITORY TESTS
# ============================================================

class TestGetUserByEmail:
    """Tests for repository.get_user_by_email"""

    async def test_returns_user_when_found(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_user)
        )

        # Act
        result = await repository.get_user_by_email(mock_db, "test@example.com")

        # Assert
        assert result == mock_user
        mock_db.execute.assert_called_once()

    async def test_returns_none_when_not_found(self, mock_db: AsyncMock):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act
        result = await repository.get_user_by_email(mock_db, "nonexistent@example.com")

        # Assert
        assert result is None

    async def test_query_excludes_soft_deleted_users(self, mock_db: AsyncMock):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act
        await repository.get_user_by_email(mock_db, "deleted@example.com")

        # Assert - Verify the WHERE clause contains deleted_at filter
        call_args = mock_db.execute.call_args[0][0]
        query_str = str(call_args)
        assert "deleted_at" in query_str


class TestGetUserById:
    """Tests for repository.get_user_by_id"""

    async def test_returns_user_when_found(
        self, mock_db: AsyncMock, mock_user: MagicMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_user)
        )

        # Act
        result = await repository.get_user_by_id(mock_db, user_id)

        # Assert
        assert result == mock_user
        mock_db.execute.assert_called_once()

    async def test_returns_none_when_not_found(self, mock_db: AsyncMock, user_id: uuid.UUID):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act
        result = await repository.get_user_by_id(mock_db, user_id)

        # Assert
        assert result is None

    async def test_query_excludes_soft_deleted_users(
        self, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act
        await repository.get_user_by_id(mock_db, user_id)

        # Assert
        call_args = mock_db.execute.call_args[0][0]
        query_str = str(call_args)
        assert "deleted_at" in query_str


class TestCreateUser:
    """Tests for repository.create_user"""

    async def test_creates_and_returns_user(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await repository.create_user(mock_db, mock_user)

        # Assert
        assert result == mock_user
        mock_db.add.assert_called_once_with(mock_user)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_user)


class TestUpdateUser:
    """Tests for repository.update_user"""

    async def test_updates_single_field(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await repository.update_user(mock_db, mock_user, full_name="New Name")

        # Assert
        assert result == mock_user
        assert mock_user.full_name == "New Name"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_user)

    async def test_updates_multiple_fields(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await repository.update_user(
            mock_db,
            mock_user,
            full_name="New Name",
            hashed_password="new_hash",
            status=UserStatus.INACTIVE,
        )

        # Assert
        assert mock_user.full_name == "New Name"
        assert mock_user.hashed_password == "new_hash"
        assert mock_user.status == UserStatus.INACTIVE

    @pytest.mark.parametrize(
        "invalid_field",
        ["invalid_field", "nonexistent", "__dict__", "does_not_exist"],
    )
    async def test_raises_error_for_invalid_field(
        self, mock_db: AsyncMock, mock_user: MagicMock, invalid_field: str
    ):
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match=f"User has no column '{invalid_field}'"):
            await repository.update_user(mock_db, mock_user, **{invalid_field: "value"})

    async def test_empty_updates_still_commits(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        await repository.update_user(mock_db, mock_user)

        # Assert
        mock_db.commit.assert_called_once()


class TestSoftDeleteUser:
    """Tests for repository.soft_delete_user"""

    async def test_sets_deleted_at_timestamp(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.commit = AsyncMock()
        before_time = datetime.now(timezone.utc)

        # Act
        await repository.soft_delete_user(mock_db, mock_user)

        # Assert
        assert mock_user.deleted_at is not None
        assert mock_user.deleted_at >= before_time

    async def test_sets_status_to_inactive(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.commit = AsyncMock()

        # Act
        await repository.soft_delete_user(mock_db, mock_user)

        # Assert
        assert mock_user.status == UserStatus.INACTIVE

    async def test_commits_transaction(self, mock_db: AsyncMock, mock_user: MagicMock):
        # Arrange
        mock_db.commit = AsyncMock()

        # Act
        await repository.soft_delete_user(mock_db, mock_user)

        # Assert
        mock_db.commit.assert_called_once()


class TestGetAllRoles:
    """Tests for repository.get_all_roles"""

    async def test_returns_list_of_roles(self, mock_db: AsyncMock):
        # Arrange
        mock_roles = [MagicMock(name=UserRoleEnum.ADMIN), MagicMock(name=UserRoleEnum.VIEWER)]
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_roles)
        )

        # Act
        result = await repository.get_all_roles(mock_db)

        # Assert
        assert len(result) == 2
        assert result == mock_roles

    async def test_returns_empty_list_when_no_roles(self, mock_db: AsyncMock):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=[])
        )

        # Act
        result = await repository.get_all_roles(mock_db)

        # Assert
        assert result == []


class TestGetRoleByName:
    """Tests for repository.get_role_by_name"""

    @pytest.mark.parametrize("role_enum", list(UserRoleEnum))
    async def test_returns_role_when_found(
        self, mock_db: AsyncMock, role_enum: UserRoleEnum
    ):
        # Arrange
        mock_role = MagicMock()
        mock_role.name = role_enum
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_role)
        )

        # Act
        result = await repository.get_role_by_name(mock_db, role_enum)

        # Assert
        assert result == mock_role

    async def test_returns_none_when_not_found(self, mock_db: AsyncMock):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act
        result = await repository.get_role_by_name(mock_db, UserRoleEnum.ADMIN)

        # Assert
        assert result is None


class TestSeedRoles:
    """Tests for repository.seed_roles"""

    async def test_seeds_all_roles_when_table_empty(self, mock_db: AsyncMock):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=[])
        )
        mock_db.add_all = MagicMock()
        mock_db.commit = AsyncMock()

        # Act
        await repository.seed_roles(mock_db)

        # Assert
        mock_db.add_all.assert_called_once()
        added_roles = mock_db.add_all.call_args[0][0]
        assert len(added_roles) == len(UserRoleEnum)
        mock_db.commit.assert_called_once()

    async def test_skips_seeding_when_all_roles_exist(self, mock_db: AsyncMock):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(
                scalars_return=list(UserRoleEnum)
            )
        )
        mock_db.add_all = MagicMock()
        mock_db.commit = AsyncMock()

        # Act
        await repository.seed_roles(mock_db)

        # Assert
        mock_db.add_all.assert_not_called()
        mock_db.commit.assert_not_called()

    async def test_seeds_only_missing_roles(self, mock_db: AsyncMock):
        # Arrange - Only ADMIN exists
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(
                scalars_return=[UserRoleEnum.ADMIN]
            )
        )
        mock_db.add_all = MagicMock()
        mock_db.commit = AsyncMock()

        # Act
        await repository.seed_roles(mock_db)

        # Assert
        mock_db.add_all.assert_called_once()
        added_roles = mock_db.add_all.call_args[0][0]
        assert len(added_roles) == len(UserRoleEnum) - 1


class TestGetUserRoleRow:
    """Tests for repository.get_user_role_row"""

    async def test_returns_user_role_when_found(
        self, mock_db: AsyncMock, mock_user_role: MagicMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_user_role)
        )

        # Act
        result = await repository.get_user_role_row(mock_db, user_id)

        # Assert
        assert result == mock_user_role

    async def test_returns_none_when_not_found(self, mock_db: AsyncMock, user_id: uuid.UUID):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act
        result = await repository.get_user_role_row(mock_db, user_id)

        # Assert
        assert result is None


class TestAssignRole:
    """Tests for repository.assign_role"""

    async def test_assigns_role_successfully(
        self,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
        mock_role: MagicMock,
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            side_effect=[
                # get_user_role_row - returns None (no existing role)
                create_mock_execute_result(scalars_return=None),
                # get_role_by_name - returns role
                create_mock_execute_result(scalars_return=mock_role),
            ]
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await repository.assign_role(mock_db, user_id, UserRoleEnum.ADMIN)

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    async def test_raises_error_when_user_already_has_role(
        self,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
        mock_user_role: MagicMock,
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_user_role)
        )

        # Act & Assert
        with pytest.raises(ValueError, match="already has role"):
            await repository.assign_role(mock_db, user_id, UserRoleEnum.VIEWER)

    async def test_raises_error_when_role_not_found(
        self, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            side_effect=[
                # get_user_role_row - returns None
                create_mock_execute_result(scalars_return=None),
                # get_role_by_name - returns None
                create_mock_execute_result(scalars_return=None),
            ]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await repository.assign_role(mock_db, user_id, UserRoleEnum.ADMIN)


class TestUpdateRole:
    """Tests for repository.update_role"""

    async def test_updates_role_successfully(
        self,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
        mock_user_role: MagicMock,
        mock_viewer_role: MagicMock,
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            side_effect=[
                # get_user_role_row - returns existing
                create_mock_execute_result(scalars_return=mock_user_role),
                # get_role_by_name - returns new role
                create_mock_execute_result(scalars_return=mock_viewer_role),
            ]
        )
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await repository.update_role(mock_db, user_id, UserRoleEnum.VIEWER)

        # Assert
        assert mock_user_role.role_id == mock_viewer_role.id
        mock_db.commit.assert_called_once()

    async def test_raises_error_when_user_has_no_role(
        self, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act & Assert
        with pytest.raises(ValueError, match="no role assigned"):
            await repository.update_role(mock_db, user_id, UserRoleEnum.ADMIN)

    async def test_raises_error_when_new_role_not_found(
        self,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
        mock_user_role: MagicMock,
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            side_effect=[
                # get_user_role_row - returns existing
                create_mock_execute_result(scalars_return=mock_user_role),
                # get_role_by_name - returns None
                create_mock_execute_result(scalars_return=None),
            ]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await repository.update_role(mock_db, user_id, UserRoleEnum.ANALYST)


class TestRevokeRole:
    """Tests for repository.revoke_role"""

    async def test_revokes_role_successfully(
        self,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
        mock_user_role: MagicMock,
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_user_role)
        )
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        # Act
        await repository.revoke_role(mock_db, user_id)

        # Assert
        mock_db.delete.assert_called_once_with(mock_user_role)
        mock_db.commit.assert_called_once()

    async def test_raises_error_when_no_role_to_revoke(
        self, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act & Assert
        with pytest.raises(ValueError, match="no role assigned"):
            await repository.revoke_role(mock_db, user_id)


# ============================================================
# SERVICE TESTS
# ============================================================

class TestGenerateTokens:
    """Tests for service.generate_tokens"""

    @patch("app.modules.auth.service.create_access_token", return_value="access_token")
    @patch("app.modules.auth.service.create_refresh_token", return_value="refresh_token")
    def test_returns_both_tokens(
        self,
        mock_refresh: MagicMock,
        mock_access: MagicMock,
        mock_user: MagicMock,
    ):
        # Act
        result = service.generate_tokens(mock_user)

        # Assert
        assert result["access_token"] == "access_token"
        assert result["refresh_token"] == "refresh_token"
        mock_access.assert_called_once()
        mock_refresh.assert_called_once()

    @patch("app.modules.auth.service.create_access_token", return_value="access")
    @patch("app.modules.auth.service.create_refresh_token", return_value="refresh")
    def test_includes_user_id_in_both_tokens(
        self,
        mock_refresh: MagicMock,
        mock_access: MagicMock,
        mock_user: MagicMock,
    ):
        # Act
        service.generate_tokens(mock_user)

        # Assert
        access_payload = mock_access.call_args[0][0]
        refresh_payload = mock_refresh.call_args[0][0]
        assert access_payload["user_id"] == str(mock_user.id)
        assert refresh_payload["user_id"] == str(mock_user.id)

    @patch("app.modules.auth.service.create_access_token", return_value="access")
    @patch("app.modules.auth.service.create_refresh_token", return_value="refresh")
    def test_includes_correct_type_claims(
        self,
        mock_refresh: MagicMock,
        mock_access: MagicMock,
        mock_user: MagicMock,
    ):
        # Act
        service.generate_tokens(mock_user)

        # Assert
        access_payload = mock_access.call_args[0][0]
        refresh_payload = mock_refresh.call_args[0][0]
        assert access_payload["typ"] == "access"
        assert refresh_payload["typ"] == "refresh"


class TestRotateTokens:
    """Tests for service.rotate_tokens"""

    @patch("app.modules.auth.service.create_access_token", return_value="new_access")
    @patch("app.modules.auth.service.create_refresh_token", return_value="new_refresh")
    @patch("app.modules.auth.service.decode_token")
    def test_returns_new_token_pair_with_old_token(
        self,
        mock_decode: MagicMock,
        mock_refresh: MagicMock,
        mock_access: MagicMock,
    ):
        # Arrange
        mock_decode.return_value = {"user_id": "user-123", "typ": "refresh"}
        old_token = "old_refresh_token"

        # Act
        result = service.rotate_tokens(old_token)

        # Assert
        assert result["access_token"] == "new_access"
        assert result["refresh_token"] == "new_refresh"
        assert result["_old_refresh_token"] == old_token

    @patch("app.modules.auth.service.decode_token")
    def test_raises_401_on_invalid_token(self, mock_decode: MagicMock):
        # Arrange
        mock_decode.side_effect = Exception("Invalid token")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.rotate_tokens("invalid_token")
        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail

    @patch("app.modules.auth.service.decode_token")
    def test_raises_401_on_wrong_token_type(self, mock_decode: MagicMock):
        # Arrange
        mock_decode.return_value = {"user_id": "user-123", "typ": "access"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.rotate_tokens("access_token_as_refresh")
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    @patch("app.modules.auth.service.decode_token")
    def test_raises_401_on_missing_user_id(self, mock_decode: MagicMock):
        # Arrange
        mock_decode.return_value = {"typ": "refresh"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.rotate_tokens("token_without_user_id")
        assert exc_info.value.status_code == 401
        assert "Malformed" in exc_info.value.detail

    @patch("app.modules.auth.service.decode_token")
    def test_raises_401_on_empty_user_id(self, mock_decode: MagicMock):
        # Arrange
        mock_decode.return_value = {"user_id": "", "typ": "refresh"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            service.rotate_tokens("token_with_empty_user_id")
        assert exc_info.value.status_code == 401


class TestBlacklistToken:
    """Tests for service.blacklist_token"""

    @patch("app.modules.auth.service.redis_client")
    @patch("app.modules.auth.service.time.time", return_value=1000000)
    async def test_stores_token_with_calculated_ttl(
        self, mock_time: MagicMock, mock_redis: MagicMock
    ):
        # Arrange
        exp = 1000360  # 360 seconds in the future

        # Act
        await service.blacklist_token("token_123", exp)

        # Assert
        mock_redis.set.assert_called_once_with("token_123", "blacklisted", ex=360)

    @patch("app.modules.auth.service.redis_client")
    @patch("app.modules.auth.service.time.time", return_value=1000000)
    async def test_uses_min_ttl_when_token_expired(
        self, mock_time: MagicMock, mock_redis: MagicMock
    ):
        # Arrange
        exp = 999990  # Token already expired

        # Act
        await service.blacklist_token("token_123", exp)

        # Assert
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 60  # _MIN_TTL_SECONDS

    @patch("app.modules.auth.service.redis_client")
    @patch("app.modules.auth.service.time.time", return_value=1000000)
    async def test_uses_min_ttl_when_ttl_equals_zero(
        self, mock_time: MagicMock, mock_redis: MagicMock
    ):
        # Arrange
        exp = 1000000  # Exactly now

        # Act
        await service.blacklist_token("token_123", exp)

        # Assert
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 60


class TestIsTokenBlacklisted:
    """Tests for service.is_token_blacklisted"""

    @patch("app.modules.auth.service.redis_client")
    async def test_returns_true_when_token_is_blacklisted(self, mock_redis: MagicMock):
        # Arrange
        mock_redis.get = AsyncMock(return_value="blacklisted")

        # Act
        result = await service.is_token_blacklisted("token_123")

        # Assert
        assert result is True

    @patch("app.modules.auth.service.redis_client")
    async def test_returns_false_when_token_not_blacklisted(self, mock_redis: MagicMock):
        # Arrange
        mock_redis.get = AsyncMock(return_value=None)

        # Act
        result = await service.is_token_blacklisted("token_123")

        # Assert
        assert result is False

    @patch("app.modules.auth.service.redis_client")
    async def test_returns_true_for_any_non_none_value(self, mock_redis: MagicMock):
        # Arrange
        mock_redis.get = AsyncMock(return_value="any_value")

        # Act
        result = await service.is_token_blacklisted("token_123")

        # Assert
        assert result is True


class TestGetUserRole:
    """Tests for service.get_user_role"""

    @patch("app.modules.auth.service.redis_client")
    async def test_returns_cached_role_on_cache_hit_string(
        self, mock_redis: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_redis.get = AsyncMock(return_value="admin")

        # Act
        result = await service.get_user_role(mock_db, user_id)

        # Assert
        assert result == "admin"
        mock_db.execute.assert_not_called()

    @patch("app.modules.auth.service.redis_client")
    async def test_returns_cached_role_when_bytes(
        self, mock_redis: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_redis.get = AsyncMock(return_value=b"admin")

        # Act
        result = await service.get_user_role(mock_db, user_id)

        # Assert
        assert result == "admin"

    @patch("app.modules.auth.service.redis_client")
    async def test_queries_db_on_cache_miss_and_caches(
        self, mock_redis: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_redis.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(
                scalar_one_or_none=UserRoleEnum.ADMIN
            )
        )
        mock_redis.set = AsyncMock()

        # Act
        result = await service.get_user_role(mock_db, user_id)

        # Assert
        assert result == "admin"
        mock_db.execute.assert_called_once()
        mock_redis.set.assert_called_once()
        set_call_args = mock_redis.set.call_args
        assert set_call_args[0][0] == f"perm:{user_id}"
        assert set_call_args[1]["ex"] == 300  # _ROLE_CACHE_TTL

    @patch("app.modules.auth.service.redis_client")
    async def test_returns_none_when_user_has_no_role(
        self, mock_redis: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_redis.get = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalar_one_or_none=None)
        )

        # Act
        result = await service.get_user_role(mock_db, user_id)

        # Assert
        assert result is None
        mock_redis.set.assert_not_called()


class TestGetUserRoleOrRaise:
    """Tests for service.get_user_role_or_raise"""

    @patch("app.modules.auth.service.get_user_role")
    async def test_returns_role_when_found(
        self, mock_get_role: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_get_role.return_value = "admin"

        # Act
        result = await service.get_user_role_or_raise(mock_db, user_id)

        # Assert
        assert result == "admin"

    @patch("app.modules.auth.service.get_user_role")
    async def test_raises_403_when_no_role(
        self, mock_get_role: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_get_role.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get_user_role_or_raise(mock_db, user_id)
        assert exc_info.value.status_code == 403
        assert "No role assigned" in exc_info.value.detail


class TestInvalidateRoleCache:
    """Tests for service.invalidate_role_cache"""

    @patch("app.modules.auth.service.redis_client")
    async def test_deletes_correct_cache_key(
        self, mock_redis: MagicMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_redis.delete = AsyncMock()

        # Act
        await service.invalidate_role_cache(user_id)

        # Assert
        mock_redis.delete.assert_called_once_with(f"perm:{user_id}")


class TestAssignRoleHelper:
    """Tests for service._assign_role (internal helper)"""

    @patch("app.modules.auth.service.UserRole")
    async def test_assigns_role_successfully(
        self, mock_user_role_class: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_role = MagicMock()
        mock_role.id = 1

        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=mock_role)
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Act
        await service._assign_role(mock_db, user_id, UserRoleEnum.ADMIN)

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_raises_runtime_error_when_role_not_found(
        self, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_db.execute = AsyncMock(
            return_value=create_mock_execute_result(scalars_return=None)
        )

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await service._assign_role(mock_db, user_id, UserRoleEnum.ADMIN)
        assert "not found" in str(exc_info.value)
        assert "seeded" in str(exc_info.value)


class TestSignup:
    """Tests for service.signup"""

    @patch("app.modules.auth.service.create_user")
    @patch("app.modules.auth.service.get_user_by_email")
    @patch("app.modules.auth.service.hash_password", return_value="hashed")
    async def test_signup_success_for_regular_user(
        self,
        mock_hash: MagicMock,
        mock_get_user: MagicMock,
        mock_create: MagicMock,
        mock_db: AsyncMock,
    ):
        # Arrange
        mock_get_user.return_value = None
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=5))
        )

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.status = UserStatus.ACTIVE
        mock_user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_user.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_create.return_value = mock_user
        mock_db.refresh = AsyncMock()

        # Act
        result = await service.signup(
            mock_db, "Test@example.com ", "Password123!", "Test User"
        )

        # Assert
        assert result.email == "test@example.com"
        mock_hash.assert_called_once_with("Password123!")
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")

    @patch("app.modules.auth.service.get_user_by_email")
    async def test_raises_400_when_email_exists(
        self, mock_get_user: MagicMock, mock_db: AsyncMock
    ):
        # Arrange
        mock_get_user.return_value = MagicMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.signup(
                mock_db, "existing@example.com", "Password123!", "Test User"
            )
        assert exc_info.value.status_code == 400
        assert "different email" in exc_info.value.detail

    @patch("app.modules.auth.service._assign_role")
    @patch("app.modules.auth.service.create_user")
    @patch("app.modules.auth.service.get_user_by_email")
    @patch("app.modules.auth.service.hash_password", return_value="hashed")
    async def test_first_user_becomes_admin(
        self,
        mock_hash: MagicMock,
        mock_get_user: MagicMock,
        mock_create: MagicMock,
        mock_assign_role: AsyncMock,
        mock_db: AsyncMock,
    ):
        # Arrange
        mock_get_user.return_value = None
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=0))
        )

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "first@example.com"
        mock_user.full_name = "First User"
        mock_user.status = UserStatus.ACTIVE
        mock_user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_user.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_create.return_value = mock_user
        mock_db.refresh = AsyncMock()

        # Act
        await service.signup(
            mock_db, "first@example.com", "Password123!", "First User"
        )

        # Assert
        mock_assign_role.assert_called_once_with(mock_db, mock_user.id, UserRoleEnum.ADMIN)

    @patch("app.modules.auth.service.create_user")
    @patch("app.modules.auth.service.get_user_by_email")
    @patch("app.modules.auth.service.hash_password", return_value="hashed")
    async def test_handles_integrity_error(
        self,
        mock_hash: MagicMock,
        mock_get_user: MagicMock,
        mock_create: MagicMock,
        mock_db: AsyncMock,
    ):
        # Arrange
        mock_get_user.return_value = None
        mock_create.side_effect = IntegrityError("duplicate", {}, None) # type: ignore
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=5))
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.signup(
                mock_db, "duplicate@example.com", "Password123!", "Test"
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.parametrize(
        "input_email,expected_normalized",
        [
            ("  TEST@Example.COM  ", "test@example.com"),
            ("Test@Example.COM", "test@example.com"),
            ("  test@example.com  ", "test@example.com"),
        ],
    )
    @patch("app.modules.auth.service.create_user")
    @patch("app.modules.auth.service.get_user_by_email")
    @patch("app.modules.auth.service.hash_password", return_value="hashed")
    async def test_normalizes_email(
        self,
        mock_hash: MagicMock,
        mock_get_user: MagicMock,
        mock_create: MagicMock,
        mock_db: AsyncMock,
        input_email: str,
        expected_normalized: str,
    ):
        # Arrange
        mock_get_user.return_value = None
        mock_db.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=5))
        )
        mock_user = MagicMock()
        mock_user.email = expected_normalized
        mock_user.full_name = "Test"
        mock_user.status = UserStatus.ACTIVE
        mock_user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_user.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_create.return_value = mock_user
        mock_db.refresh = AsyncMock()

        # Act
        await service.signup(mock_db, input_email, "Password123!", "Test")

        # Assert
        mock_get_user.assert_called_once_with(mock_db, expected_normalized)


class TestLogin:
    """Tests for service.login"""

    @patch("app.modules.auth.service.generate_tokens", return_value={"access_token": "access", "refresh_token": "refresh"})
    @patch("app.modules.auth.service.verify_password", return_value=True)
    @patch("app.modules.auth.service.get_user_by_email")
    async def test_login_success(
        self,
        mock_get_user: MagicMock,
        mock_verify: MagicMock,
        mock_tokens: MagicMock,
        mock_db: AsyncMock,
        mock_user: MagicMock,
    ):
        # Arrange
        mock_get_user.return_value = mock_user

        # Act
        result = await service.login(mock_db, "test@example.com", "password123")

        # Assert
        assert result["access_token"] == "access"
        assert result["refresh_token"] == "refresh"

    @patch("app.modules.auth.service.get_user_by_email")
    async def test_raises_401_when_user_not_found(
        self, mock_get_user: MagicMock, mock_db: AsyncMock
    ):
        # Arrange
        mock_get_user.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.login(mock_db, "nonexistent@example.com", "password")
        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail

    @patch("app.modules.auth.service.verify_password", return_value=False)
    @patch("app.modules.auth.service.get_user_by_email")
    async def test_raises_401_when_password_wrong(
        self,
        mock_get_user: MagicMock,
        mock_verify: MagicMock,
        mock_db: AsyncMock,
        mock_user: MagicMock,
    ):
        # Arrange
        mock_get_user.return_value = mock_user

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.login(mock_db, "test@example.com", "wrong_password")
        assert exc_info.value.status_code == 401

    @patch("app.modules.auth.service.get_user_by_email")
    async def test_raises_403_when_account_inactive(
        self, mock_get_user: MagicMock, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_user.status = UserStatus.INACTIVE
        mock_get_user.return_value = mock_user

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.login(mock_db, "test@example.com", "password")
        assert exc_info.value.status_code == 403
        assert "disabled" in exc_info.value.detail

    @patch("app.modules.auth.service.get_user_by_email")
    async def test_raises_403_when_account_suspended(
        self, mock_get_user: MagicMock, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_user.status = UserStatus.SUSPENDED
        mock_get_user.return_value = mock_user

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.login(mock_db, "test@example.com", "password")
        assert exc_info.value.status_code == 403

    @pytest.mark.parametrize("status", [UserStatus.INACTIVE, UserStatus.SUSPENDED])
    @patch("app.modules.auth.service.get_user_by_email")
    async def test_raises_403_for_all_non_active_statuses(
        self, mock_get_user: MagicMock, mock_db: AsyncMock, mock_user: MagicMock, status: UserStatus
    ):
        # Arrange
        mock_user.status = status
        mock_get_user.return_value = mock_user

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.login(mock_db, "test@example.com", "password")
        assert exc_info.value.status_code == 403

    @patch("app.modules.auth.service.generate_tokens", return_value={"access_token": "access", "refresh_token": "refresh"})
    @patch("app.modules.auth.service.verify_password", return_value=True)
    @patch("app.modules.auth.service.get_user_by_email")
    async def test_normalizes_email(
        self,
        mock_get_user: MagicMock,
        mock_verify: MagicMock,
        mock_tokens: MagicMock,
        mock_db: AsyncMock,
        mock_user: MagicMock,
    ):
        # Arrange
        mock_get_user.return_value = mock_user

        # Act
        await service.login(mock_db, "  TEST@Example.COM  ", "password")

        # Assert
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")


class TestUpdateUserProfile:
    """Tests for service.update_user_profile"""

    @patch("app.modules.auth.service.update_user")
    async def test_updates_full_name_only(
        self, mock_update: MagicMock, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        from app.modules.auth.schemas import UpdateUserRequest

        payload = UpdateUserRequest(full_name="New Name")
        updated_user = MagicMock()
        mock_update.return_value = updated_user

        # Act
        result = await service.update_user_profile(mock_db, mock_user, payload)

        # Assert
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["full_name"] == "New Name"
        assert "hashed_password" not in call_kwargs

    @patch("app.modules.auth.service.update_user")
    @patch("app.modules.auth.service.hash_password", return_value="new_hashed")
    @patch("app.modules.auth.service.verify_password", return_value=True)
    async def test_updates_password_with_correct_old_password(
        self,
        mock_verify: MagicMock,
        mock_hash: MagicMock,
        mock_update: MagicMock,
        mock_db: AsyncMock,
        mock_user: MagicMock,
    ):
        # Arrange
        from app.modules.auth.schemas import UpdateUserRequest

        payload = UpdateUserRequest(old_password="old_pass", new_password="NewPass123!")
        updated_user = MagicMock()
        mock_update.return_value = updated_user

        # Act
        result = await service.update_user_profile(mock_db, mock_user, payload)

        # Assert
        mock_verify.assert_called_once_with("old_pass", mock_user.hashed_password)
        mock_hash.assert_called_once_with("NewPass123!")
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["hashed_password"] == "new_hashed"

    @patch("app.modules.auth.service.verify_password", return_value=False)
    async def test_raises_400_when_old_password_wrong(
        self, mock_verify: MagicMock, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        from app.modules.auth.schemas import UpdateUserRequest

        payload = UpdateUserRequest(old_password="wrong_old", new_password="NewPass123!")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update_user_profile(mock_db, mock_user, payload)
        assert exc_info.value.status_code == 400
        assert "Old password is incorrect" in exc_info.value.detail

    @patch("app.modules.auth.service.verify_password", side_effect=[True, True])
    async def test_raises_400_when_new_password_same_as_old(
        self, mock_verify: MagicMock, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        from app.modules.auth.schemas import UpdateUserRequest

        payload = UpdateUserRequest(old_password="same_pass", new_password="same_pass")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update_user_profile(mock_db, mock_user, payload)
        assert exc_info.value.status_code == 400
        assert "must differ" in exc_info.value.detail

    async def test_raises_400_when_no_changes_provided(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        from app.modules.auth.schemas import UpdateUserRequest

        payload = UpdateUserRequest()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update_user_profile(mock_db, mock_user, payload)
        assert exc_info.value.status_code == 400
        assert "No changes" in exc_info.value.detail


class TestDeactivateUser:
    """Tests for service.deactivate_user"""

    @patch("app.modules.auth.service.soft_delete_user")
    async def test_returns_success_message(
        self, mock_soft_delete: AsyncMock, mock_db: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_soft_delete.return_value = None

        # Act
        result = await service.deactivate_user(mock_db, mock_user)

        # Assert
        assert result["message"] == "Account deactivated successfully."
        mock_soft_delete.assert_called_once_with(mock_db, mock_user)


class TestListRoles:
    """Tests for service.list_roles"""

    @patch("app.modules.auth.service.get_all_roles")
    async def test_returns_list_of_role_responses(
        self, mock_get_all: MagicMock, mock_db: AsyncMock
    ):
        # Arrange
        mock_role1 = MagicMock()
        mock_role1.id = 1
        mock_role1.name = UserRoleEnum.ADMIN
        mock_role1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_role2 = MagicMock()
        mock_role2.id = 2
        mock_role2.name = UserRoleEnum.VIEWER
        mock_role2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_get_all.return_value = [mock_role1, mock_role2]

        # Act
        result = await service.list_roles(mock_db)

        # Assert
        assert len(result) == 2
        mock_get_all.assert_called_once_with(mock_db)

    @patch("app.modules.auth.service.get_all_roles")
    async def test_returns_empty_list_when_no_roles(
        self, mock_get_all: MagicMock, mock_db: AsyncMock
    ):
        # Arrange
        mock_get_all.return_value = []

        # Act
        result = await service.list_roles(mock_db)

        # Assert
        assert result == []


class TestGetUserRoleAssignment:
    """Tests for service.get_user_role_assignment"""

    @patch("app.modules.auth.service.get_user_role_row")
    async def test_returns_user_role_response(
        self,
        mock_get_row: MagicMock,
        mock_db: AsyncMock,
        mock_user_role: MagicMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_get_row.return_value = mock_user_role

        # Act
        result = await service.get_user_role_assignment(mock_db, user_id)

        # Assert
        assert result is not None
        mock_get_row.assert_called_once_with(mock_db, user_id)

    @patch("app.modules.auth.service.get_user_role_row")
    async def test_raises_404_when_no_role_assigned(
        self, mock_get_row: MagicMock, mock_db: AsyncMock, user_id: uuid.UUID
    ):
        # Arrange
        mock_get_row.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get_user_role_assignment(mock_db, user_id)
        assert exc_info.value.status_code == 404


class TestAssignUserRole:
    """Tests for service.assign_user_role"""

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.assign_role")
    async def test_assigns_role_and_invalidates_cache(
        self,
        mock_assign: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        mock_user_role: MagicMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_assign.return_value = mock_user_role

        # Act
        result = await service.assign_user_role(mock_db, user_id, UserRoleEnum.ADMIN)

        # Assert
        mock_assign.assert_called_once_with(mock_db, user_id, UserRoleEnum.ADMIN)
        mock_invalidate.assert_called_once_with(user_id)

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.assign_role")
    async def test_raises_409_when_already_has_role(
        self,
        mock_assign: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_assign.side_effect = ValueError("User already has role 'admin'")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.assign_user_role(mock_db, user_id, UserRoleEnum.ADMIN)
        assert exc_info.value.status_code == 409
        mock_invalidate.assert_not_called()

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.assign_role")
    async def test_raises_404_when_role_not_found(
        self,
        mock_assign: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_assign.side_effect = ValueError("Role 'admin' not found")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.assign_user_role(mock_db, user_id, UserRoleEnum.ADMIN)
        assert exc_info.value.status_code == 404
        mock_invalidate.assert_not_called()


class TestUpdateUserRole:
    """Tests for service.update_user_role"""

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.update_role")
    async def test_updates_role_and_invalidates_cache(
        self,
        mock_update: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        mock_user_role: MagicMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_update.return_value = mock_user_role

        # Act
        result = await service.update_user_role(mock_db, user_id, UserRoleEnum.VIEWER)

        # Assert
        mock_update.assert_called_once_with(mock_db, user_id, UserRoleEnum.VIEWER)
        mock_invalidate.assert_called_once_with(user_id)

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.update_role")
    async def test_raises_404_when_no_role_assigned(
        self,
        mock_update: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_update.side_effect = ValueError("User has no role assigned")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update_user_role(mock_db, user_id, UserRoleEnum.ADMIN)
        assert exc_info.value.status_code == 404
        mock_invalidate.assert_not_called()


class TestRevokeUserRole:
    """Tests for service.revoke_user_role"""

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.revoke_role")
    async def test_revokes_role_and_invalidates_cache(
        self,
        mock_revoke: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_revoke.return_value = None

        # Act
        await service.revoke_user_role(mock_db, user_id)

        # Assert
        mock_revoke.assert_called_once_with(mock_db, user_id)
        mock_invalidate.assert_called_once_with(user_id)

    @patch("app.modules.auth.service.invalidate_role_cache")
    @patch("app.modules.auth.service.revoke_role")
    async def test_raises_404_when_no_role_to_revoke(
        self,
        mock_revoke: AsyncMock,
        mock_invalidate: AsyncMock,
        mock_db: AsyncMock,
        user_id: uuid.UUID,
    ):
        # Arrange
        mock_revoke.side_effect = ValueError("User has no role assigned")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.revoke_user_role(mock_db, user_id)
        assert exc_info.value.status_code == 404
        mock_invalidate.assert_not_called()


# ============================================================
# PERMISSION TESTS
# ============================================================

class TestResolveRole:
    """Tests for permission._resolve_role"""

    @pytest.mark.parametrize(
        "role_str,expected",
        [
            ("viewer", UserRoleEnum.VIEWER),
            ("analyst", UserRoleEnum.ANALYST),
            ("admin", UserRoleEnum.ADMIN),
        ],
    )
    def test_returns_enum_for_valid_string(self, role_str: str, expected: UserRoleEnum):
        # Act
        result = permission._resolve_role(role_str)

        # Assert
        assert result == expected

    def test_returns_none_for_none_input(self):
        # Act
        result = permission._resolve_role(None)

        # Assert
        assert result is None

    def test_returns_none_for_empty_string(self):
        # Act
        result = permission._resolve_role("")

        # Assert
        assert result is None

    def test_returns_none_for_invalid_string(self):
        # Act
        result = permission._resolve_role("invalid_role")

        # Assert
        assert result is None

    def test_returns_none_for_whitespace_string(self):
        # Act
        result = permission._resolve_role("   ")

        # Assert
        assert result is None


class TestGetCurrentUser:
    """Tests for permission.get_current_user"""

    @patch("app.modules.auth.permission.get_user_by_id")
    @patch("app.modules.auth.permission.decode_token")
    @patch("app.modules.auth.permission.is_token_blacklisted")
    async def test_returns_user_when_valid_token(
        self,
        mock_blacklisted: AsyncMock,
        mock_decode: MagicMock,
        mock_get_user: AsyncMock,
        mock_user: MagicMock,
        mock_request: MagicMock,
    ):
        # Arrange
        mock_request.cookies.get.return_value = "valid_token"
        mock_blacklisted.return_value = False
        mock_decode.return_value = {"user_id": str(mock_user.id), "typ": "access"}
        mock_get_user.return_value = mock_user
        mock_db = AsyncMock()

        # Act
        result = await permission.get_current_user(mock_request, mock_db)

        # Assert
        assert result == mock_user

    async def test_raises_401_when_no_token(self, mock_request: MagicMock):
        # Arrange
        mock_request.cookies.get.return_value = None
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.get_current_user(mock_request, mock_db)
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @patch("app.modules.auth.permission.is_token_blacklisted")
    async def test_raises_401_when_token_blacklisted(
        self, mock_blacklisted: AsyncMock, mock_request: MagicMock
    ):
        # Arrange
        mock_request.cookies.get.return_value = "blacklisted_token"
        mock_blacklisted.return_value = True
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.get_current_user(mock_request, mock_db)
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail

    @patch("app.modules.auth.permission.decode_token")
    @patch("app.modules.auth.permission.is_token_blacklisted")
    async def test_raises_401_when_token_invalid(
        self,
        mock_blacklisted: AsyncMock,
        mock_decode: MagicMock,
        mock_request: MagicMock,
    ):
        # Arrange
        mock_request.cookies.get.return_value = "invalid_token"
        mock_blacklisted.return_value = False
        mock_decode.side_effect = Exception("Invalid")
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.get_current_user(mock_request, mock_db)
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @patch("app.modules.auth.permission.decode_token")
    @patch("app.modules.auth.permission.is_token_blacklisted")
    async def test_raises_401_when_wrong_token_type(
        self,
        mock_blacklisted: AsyncMock,
        mock_decode: MagicMock,
        mock_request: MagicMock,
    ):
        # Arrange
        mock_request.cookies.get.return_value = "refresh_token_as_access"
        mock_blacklisted.return_value = False
        mock_decode.return_value = {"user_id": "some_id", "typ": "refresh"}
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.get_current_user(mock_request, mock_db)
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    @patch("app.modules.auth.permission.get_user_by_id")
    @patch("app.modules.auth.permission.decode_token")
    @patch("app.modules.auth.permission.is_token_blacklisted")
    async def test_raises_401_when_user_not_found(
        self,
        mock_blacklisted: AsyncMock,
        mock_decode: MagicMock,
        mock_get_user: AsyncMock,
        mock_request: MagicMock,
    ):
        # Arrange
        user_id = uuid.uuid4()
        mock_request.cookies.get.return_value = "valid_token"
        mock_blacklisted.return_value = False
        mock_decode.return_value = {"user_id": str(user_id), "typ": "access"}
        mock_get_user.return_value = None
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.get_current_user(mock_request, mock_db)
        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail


class TestRequireAdmin:
    """Tests for permission.require_admin"""

    @patch("app.modules.auth.permission.get_user_role")
    async def test_allows_admin_user(
        self, mock_get_role: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_get_role.return_value = "admin"
        mock_db = AsyncMock()

        # Act
        result = await permission.require_admin(mock_user, mock_db)

        # Assert
        assert result == mock_user

    @pytest.mark.parametrize("role", ["viewer", "analyst"])
    @patch("app.modules.auth.permission.get_user_role")
    async def test_denies_non_admin_users(
        self, mock_get_role: AsyncMock, mock_user: MagicMock, role: str
    ):
        # Arrange
        mock_get_role.return_value = role
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.require_admin(mock_user, mock_db)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    @patch("app.modules.auth.permission.get_user_role")
    async def test_denies_user_with_no_role(
        self, mock_get_role: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_get_role.return_value = None
        mock_db = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await permission.require_admin(mock_user, mock_db)
        assert exc_info.value.status_code == 403


class TestRequireRole:
    """Tests for permission.require_role factory"""

    @patch("app.modules.auth.permission.get_user_role")
    @pytest.mark.parametrize(
        "minimum_role,user_role,should_pass",
        [
            (UserRoleEnum.VIEWER, UserRoleEnum.VIEWER, True),
            (UserRoleEnum.VIEWER, UserRoleEnum.ANALYST, True),
            (UserRoleEnum.VIEWER, UserRoleEnum.ADMIN, True),
            (UserRoleEnum.ANALYST, UserRoleEnum.VIEWER, False),
            (UserRoleEnum.ANALYST, UserRoleEnum.ANALYST, True),
            (UserRoleEnum.ANALYST, UserRoleEnum.ADMIN, True),
            (UserRoleEnum.ADMIN, UserRoleEnum.VIEWER, False),
            (UserRoleEnum.ADMIN, UserRoleEnum.ANALYST, False),
            (UserRoleEnum.ADMIN, UserRoleEnum.ADMIN, True),
        ],
    )
    async def test_role_hierarchy_enforcement(
        self,
        mock_get_role: AsyncMock,
        mock_user: MagicMock,
        minimum_role: UserRoleEnum,
        user_role: UserRoleEnum,
        should_pass: bool,
    ):
        # Arrange
        mock_get_role.return_value = user_role.value
        mock_db = AsyncMock()
        dependency = permission.require_role(minimum_role)

        # Act & Assert
        if should_pass:
            result = await dependency(mock_user, mock_db)
            assert result == mock_user
        else:
            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_user, mock_db)
            assert exc_info.value.status_code == 403

    @patch("app.modules.auth.permission.get_user_role")
    async def test_raises_403_when_no_role_assigned(
        self, mock_get_role: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_get_role.return_value = None
        mock_db = AsyncMock()
        dependency = permission.require_role(UserRoleEnum.VIEWER)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_user, mock_db)
        assert exc_info.value.status_code == 403
        assert "No role assigned" in exc_info.value.detail

    @patch("app.modules.auth.permission.get_user_role")
    async def test_error_message_includes_required_role(
        self, mock_get_role: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_get_role.return_value = UserRoleEnum.VIEWER.value
        mock_db = AsyncMock()
        dependency = permission.require_role(UserRoleEnum.ADMIN)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_user, mock_db)
        assert "admin" in exc_info.value.detail.lower()


class TestRequirePermission:
    """Tests for permission.require_permission factory"""

    @patch("app.modules.auth.permission.get_user_role")
    @pytest.mark.parametrize(
        "role,action,should_pass",
        [
            # Viewer permissions
            (UserRoleEnum.VIEWER, PermissionAction.VIEW_RECORDS, True),
            (UserRoleEnum.VIEWER, PermissionAction.VIEW_ANALYTICS, True),
            (UserRoleEnum.VIEWER, PermissionAction.CREATE_RECORDS, False),
            (UserRoleEnum.VIEWER, PermissionAction.UPDATE_RECORDS, False),
            (UserRoleEnum.VIEWER, PermissionAction.DELETE_RECORDS, False),
            (UserRoleEnum.VIEWER, PermissionAction.ADVANCED_ANALYSIS, False),
            (UserRoleEnum.VIEWER, PermissionAction.MANAGE_USERS, False),
            (UserRoleEnum.VIEWER, PermissionAction.ASSIGN_ROLES, False),
            # Analyst permissions
            (UserRoleEnum.ANALYST, PermissionAction.VIEW_RECORDS, True),
            (UserRoleEnum.ANALYST, PermissionAction.VIEW_ANALYTICS, True),
            (UserRoleEnum.ANALYST, PermissionAction.ADVANCED_ANALYSIS, True),
            (UserRoleEnum.ANALYST, PermissionAction.CREATE_RECORDS, False),
            (UserRoleEnum.ANALYST, PermissionAction.MANAGE_USERS, False),
            (UserRoleEnum.ANALYST, PermissionAction.ASSIGN_ROLES, False),
            # Admin permissions - has all
            (UserRoleEnum.ADMIN, PermissionAction.VIEW_RECORDS, True),
            (UserRoleEnum.ADMIN, PermissionAction.CREATE_RECORDS, True),
            (UserRoleEnum.ADMIN, PermissionAction.UPDATE_RECORDS, True),
            (UserRoleEnum.ADMIN, PermissionAction.DELETE_RECORDS, True),
            (UserRoleEnum.ADMIN, PermissionAction.VIEW_ANALYTICS, True),
            (UserRoleEnum.ADMIN, PermissionAction.ADVANCED_ANALYSIS, True),
            (UserRoleEnum.ADMIN, PermissionAction.MANAGE_USERS, True),
            (UserRoleEnum.ADMIN, PermissionAction.ASSIGN_ROLES, True),
        ],
    )
    async def test_permission_enforcement(
        self,
        mock_get_role: AsyncMock,
        mock_user: MagicMock,
        role: UserRoleEnum,
        action: PermissionAction,
        should_pass: bool,
    ):
        # Arrange
        mock_get_role.return_value = role.value
        mock_db = AsyncMock()
        dependency = permission.require_permission(action)

        # Act & Assert
        if should_pass:
            result = await dependency(mock_user, mock_db)
            assert result == mock_user
        else:
            with pytest.raises(HTTPException) as exc_info:
                await dependency(mock_user, mock_db)
            assert exc_info.value.status_code == 403

    @patch("app.modules.auth.permission.get_user_role")
    async def test_raises_403_when_no_role_assigned(
        self, mock_get_role: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_get_role.return_value = None
        mock_db = AsyncMock()
        dependency = permission.require_permission(PermissionAction.VIEW_RECORDS)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_user, mock_db)
        assert exc_info.value.status_code == 403
        assert "No role assigned" in exc_info.value.detail

    @patch("app.modules.auth.permission.get_user_role")
    async def test_error_message_includes_role_and_action(
        self, mock_get_role: AsyncMock, mock_user: MagicMock
    ):
        # Arrange
        mock_get_role.return_value = UserRoleEnum.VIEWER.value
        mock_db = AsyncMock()
        dependency = permission.require_permission(PermissionAction.MANAGE_USERS)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_user, mock_db)
        assert exc_info.value.status_code == 403
        assert "viewer" in exc_info.value.detail.lower()
        assert "manage_users" in exc_info.value.detail.lower()