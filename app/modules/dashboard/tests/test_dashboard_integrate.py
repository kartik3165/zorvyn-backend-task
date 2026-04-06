# modules/dashboard/tests/integrate.py
"""
Integration tests for the Dashboard API module.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from main import app
from app.database.session import get_db
from app.modules.auth.permission import get_current_user

from app.database.base import Base
from app.models.auth import User, Role, UserRole
from app.models.records import FinancialRecord, Category
from app.utils.enums import (
    RecordType,
    CategoryType,
    UserRoleEnum,
    PermissionAction,
    UserStatus,
)
from app.modules.dashboard.schemas import MonthlyTrend, WeeklyTrend
from fastapi import HTTPException, status


# ============================================================================
# Test Configuration & Fixtures
# ============================================================================

SQLALCHEMY_TEST_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


def create_mock_user_with_admin_role(user_id: uuid4) -> User:
    """Create a mock user with admin role for permission checks."""
    mock_user = User(
        id=user_id,
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password="fake_hash",
        status=UserStatus.ACTIVE,
    )
    
    # Mock the role relationship
    mock_role = MagicMock()
    mock_role.name = UserRoleEnum.ADMIN
    mock_role.id = 1
    mock_user_role = MagicMock()
    mock_user_role.role = mock_role
    mock_user_role.role_id = 1
    mock_user_role.user_id = user_id
    mock_user.user_role = mock_user_role
    mock_user.role_assignments = [mock_user_role]
    
    return mock_user


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionFactory() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Provide an async HTTP client with dependency overrides."""
    user_id = uuid4()
    mock_user = create_mock_user_with_admin_role(user_id)

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Patch require_permission in BOTH dashboard router and service
    with patch("app.modules.dashboard.router.require_permission", return_value=lambda: None), \
         patch("app.modules.dashboard.service.require_permission", return_value=lambda: None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_data(db_session: AsyncSession):
    """Insert realistic test data into the database."""
    user_id = uuid4()
    cat_income = Category(id=1, name="Salary", type=CategoryType.INCOME)
    cat_expense = Category(id=2, name="Groceries", type=CategoryType.EXPENSE)

    db_session.add_all([cat_income, cat_expense])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    records = [
        FinancialRecord(
            id=uuid4(), user_id=user_id, amount=5000.0, type=RecordType.INCOME,
            category_id=1, notes="Monthly salary", date=now - timedelta(days=1)
        ),
        FinancialRecord(
            id=uuid4(), user_id=user_id, amount=150.50, type=RecordType.EXPENSE,
            category_id=2, notes="Weekly groceries", date=now - timedelta(days=2)
        ),
        FinancialRecord(
            id=uuid4(), user_id=user_id, amount=5000.0, type=RecordType.INCOME,
            category_id=1, notes="Last month salary", date=now - timedelta(days=32)
        ),
        FinancialRecord(
            id=uuid4(), user_id=user_id, amount=200.0, type=RecordType.EXPENSE,
            category_id=2, notes="Old expense", date=now - timedelta(days=32)
        ),
        FinancialRecord(
            id=uuid4(), user_id=user_id, amount=10000.0, type=RecordType.INCOME,
            category_id=1, notes="Deleted bonus", date=now, deleted_at=now
        ),
    ]

    db_session.add_all(records)
    await db_session.commit()

    # Update the mock user in the dependency override
    async def override_get_current_user():
        return create_mock_user_with_admin_role(user_id)

    app.dependency_overrides[get_current_user] = override_get_current_user

    return {
        "user_id": user_id,
        "total_income": 10000.0,
        "total_expense": 350.5,
        "record_count": 4,
    }


# ============================================================================
# Test Suite: Dashboard Summary API
# ============================================================================


class TestDashboardSummaryAPI:
    """Test suite for GET /dashboard/summary"""

    @pytest_asyncio.fixture
    async def setup_summary_data(self, db_session: AsyncSession, client: AsyncClient):
        return await setup_data(db_session)

    @pytest.mark.asyncio
    async def test_get_summary_success(self, client: AsyncClient, setup_summary_data):
        response = await client.get("/dashboard/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_income" in data
        assert "total_expense" in data
        assert "net_balance" in data
        assert "record_count" in data
        assert "category_totals" in data
        assert "recent_records" in data

        assert data["total_income"] == 10000.0
        assert data["total_expense"] == 350.5
        assert data["net_balance"] == 9649.5
        assert data["record_count"] == 4
        assert data["income_count"] == 2
        assert data["expense_count"] == 2

    @pytest.mark.asyncio
    async def test_get_summary_excludes_soft_deleted(
        self, client: AsyncClient, setup_summary_data
    ):
        response = await client.get("/dashboard/summary")
        data = response.json()

        assert data["total_income"] == 10000.0
        assert data["record_count"] == 4

    @pytest.mark.asyncio
    async def test_get_summary_categories_aggregation(
        self, client: AsyncClient, setup_summary_data
    ):
        response = await client.get("/dashboard/summary")
        data = response.json()

        categories = data["category_totals"]
        assert len(categories) == 2

        salary_cat = next(c for c in categories if c["category_id"] == 1)
        grocery_cat = next(c for c in categories if c["category_id"] == 2)

        assert salary_cat["total"] == 10000.0
        assert salary_cat["count"] == 2
        assert grocery_cat["total"] == 350.5
        assert grocery_cat["count"] == 2

    @pytest.mark.asyncio
    async def test_get_summary_recent_records_limit_and_order(
        self, client: AsyncClient, setup_summary_data
    ):
        response = await client.get("/dashboard/summary")
        data = response.json()

        recent = data["recent_records"]
        assert len(recent) == 4

        dates = [datetime.fromisoformat(r["date"]) for r in recent]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_get_summary_with_date_filters(
        self, client: AsyncClient, setup_summary_data
    ):
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=35)).isoformat()
        end_date = (now - timedelta(days=30)).isoformat()

        response = await client.get(
            "/dashboard/summary",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_income"] == 5000.0
        assert data["total_expense"] == 200.0
        assert data["record_count"] == 2

    @pytest.mark.asyncio
    async def test_get_summary_empty_database(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        empty_user = create_mock_user_with_admin_role(uuid4())

        async def override_get_current_user():
            return empty_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.get("/dashboard/summary")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["total_income"] == 0.0
        assert data["total_expense"] == 0.0
        assert data["net_balance"] == 0.0
        assert data["record_count"] == 0
        assert data["category_totals"] == []
        assert data["recent_records"] == []

    @pytest.mark.asyncio
    async def test_get_summary_invalid_date_format(self, client: AsyncClient):
        response = await client.get(
            "/dashboard/summary", params={"start_date": "not-a-valid-date"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "detail" in response.json()


# ============================================================================
# Test Suite: Dashboard Trends API
# ============================================================================


class TestDashboardTrendsAPI:
    """Test suite for GET /dashboard/trends"""

    @pytest_asyncio.fixture
    async def setup_trends_data(self, db_session: AsyncSession, client: AsyncClient):
        user_id = uuid4()
        cat = Category(id=10, name="Trend Test", type=CategoryType.INCOME)
        db_session.add(cat)
        await db_session.flush()

        now = datetime.now(timezone.utc)
        records = [
            FinancialRecord(id=uuid4(), user_id=user_id, amount=1000.0, type=RecordType.INCOME, category_id=10, date=now),
            FinancialRecord(id=uuid4(), user_id=user_id, amount=400.0, type=RecordType.EXPENSE, category_id=10, date=now),
            FinancialRecord(id=uuid4(), user_id=user_id, amount=800.0, type=RecordType.INCOME, category_id=10, date=now - timedelta(weeks=2)),
            FinancialRecord(id=uuid4(), user_id=user_id, amount=5000.0, type=RecordType.INCOME, category_id=10, date=now - timedelta(days=60)),
            FinancialRecord(id=uuid4(), user_id=user_id, amount=2000.0, type=RecordType.EXPENSE, category_id=10, date=now - timedelta(days=60)),
        ]
        db_session.add_all(records)
        await db_session.commit()

        async def override_get_current_user():
            return create_mock_user_with_admin_role(user_id)

        app.dependency_overrides[get_current_user] = override_get_current_user

    @pytest.mark.asyncio
    async def test_get_trends_success(self, client: AsyncClient, setup_trends_data):
        response = await client.get("/dashboard/trends")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "monthly" in data
        assert "weekly" in data

        for month in data["monthly"]:
            MonthlyTrend(**month)

        for week in data["weekly"]:
            WeeklyTrend(**week)

    @pytest.mark.asyncio
    async def test_get_trends_net_calculation(
        self, client: AsyncClient, setup_trends_data
    ):
        response = await client.get("/dashboard/trends")
        data = response.json()

        two_months_ago = next(
            (m for m in data["monthly"] if m["income"] == 5000.0), None
        )
        assert two_months_ago is not None
        assert two_months_ago["expense"] == 2000.0
        assert two_months_ago["net"] == 3000.0

    @pytest.mark.asyncio
    async def test_get_trends_custom_limit_params(
        self, client: AsyncClient, setup_trends_data
    ):
        response = await client.get("/dashboard/trends", params={"months": 1, "weeks": 1})
        data = response.json()

        assert len(data["monthly"]) <= 1
        assert len(data["weekly"]) <= 1

    @pytest.mark.asyncio
    async def test_get_trends_empty_database(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        empty_user = create_mock_user_with_admin_role(uuid4())

        async def override_get_current_user():
            return empty_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.get("/dashboard/trends")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["monthly"] == []
        assert data["weekly"] == []

    @pytest.mark.parametrize(
        "params, expected_error_field",
        [
            ({"months": -1}, "months"),
            ({"months": 0}, "months"),
            ({"months": 25}, "months"),
            ({"weeks": -5}, "weeks"),
            ({"weeks": 53}, "weeks"),
            ({"months": "abc"}, "months"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_trends_validation_errors(
        self, client: AsyncClient, params, expected_error_field
    ):
        response = await client.get("/dashboard/trends", params=params)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = response.json()["detail"]
        assert any(err["loc"][1] == expected_error_field for err in detail)


# ============================================================================
# Test Suite: Authentication & Authorization Integration
# ============================================================================


class TestDashboardAuthAndPermissions:
    """Test integration of Auth boundaries."""

    @pytest.mark.asyncio
    async def test_summary_missing_authentication(self, client: AsyncClient):
        app.dependency_overrides.pop(get_current_user, None)

        async def raise_unauthorized():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        app.dependency_overrides[get_current_user] = raise_unauthorized

        # Don't patch require_permission for this test
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/dashboard/summary")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_summary_insufficient_permissions(self, client: AsyncClient):
        # Create a user without role (will fail permission check)
        user_no_role = User(
            id=uuid4(),
            email="norole@test.com",
            full_name="No Role",
            hashed_password="hash",
            status=UserStatus.ACTIVE,
        )
        user_no_role.user_role = None
        user_no_role.role_assignments = []

        async def override_get_current_user():
            return user_no_role

        app.dependency_overrides[get_current_user] = override_get_current_user

        # Don't patch require_permission - let it run real check
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/dashboard/summary")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_trends_insufficient_permissions(self, client: AsyncClient):
        user_no_role = User(
            id=uuid4(),
            email="norole@test.com",
            full_name="No Role",
            hashed_password="hash",
            status=UserStatus.ACTIVE,
        )
        user_no_role.user_role = None
        user_no_role.role_assignments = []

        async def override_get_current_user():
            return user_no_role

        app.dependency_overrides[get_current_user] = override_get_current_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/dashboard/trends")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test Suite: Database Error Handling
# ============================================================================


class TestDatabaseFailureScenarios:
    """Test how the service/repository handles DB issues."""

    @pytest.mark.asyncio
    async def test_summary_database_connection_failure(self, client: AsyncClient):
        async def override_broken_db():
            session = AsyncMock()
            session.execute = AsyncMock(side_effect=Exception("Database connection lost"))
            session.scalar = AsyncMock(side_effect=Exception("Database connection lost"))
            yield session

        app.dependency_overrides[get_db] = override_broken_db

        # Patch require_permission still needed
        with patch("app.modules.dashboard.router.require_permission", return_value=lambda: None):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/dashboard/summary")

        # Exception might be caught and return 500, or propagate
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Test Suite: Data Persistence and Isolation
# ============================================================================


class TestDatabaseIsolation:
    """Ensure tests don't leak state into each other."""

    @pytest.mark.asyncio
    async def test_first_request_creates_no_side_effects(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id = uuid4()
        mock_user = create_mock_user_with_admin_role(user_id)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        res1 = await client.get("/dashboard/summary")
        assert res1.status_code == 200
        assert res1.json()["record_count"] == 0

        res2 = await client.get(
            "/dashboard/summary", params={"start_date": "2020-01-01"}
        )
        assert res2.status_code == 200
        assert res2.json()["record_count"] == 0

        from sqlalchemy import select, func

        result = await db_session.execute(select(func.count(FinancialRecord.id)))
        count = result.scalar()
        assert count == 0