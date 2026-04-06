import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.pool import StaticPool
import pytest_asyncio

from main import app
from app.database.base import Base
from app.database.session import get_db
from app.modules.auth.permission import get_current_user
from app.models.records import FinancialRecord, Category
from app.utils.enums import RecordType, CategoryType, UserRoleEnum

# --- Database & Client Setup ---

SQLALCHEMY_TEST_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_TEST_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

MOCK_USER_ID = uuid4()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    # Create mock user with ALL attributes the permission system might need
    mock_user = MagicMock()
    mock_user.id = MOCK_USER_ID
    mock_user.email = "test@example.com"
    mock_user.status = "active"
    
    # Mock user_role relationship that permission.py might check
    mock_role = MagicMock()
    mock_role.name = UserRoleEnum.ADMIN
    mock_role.id = 1
    mock_user_role = MagicMock()
    mock_user_role.role = mock_role
    mock_user_role.role_id = 1
    mock_user_role.user_id = MOCK_USER_ID
    mock_user.user_role = mock_user_role
    
    # Also add role_assignments list (alternative pattern)
    mock_user.role_assignments = [mock_user_role]

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Patch the permission check directly in the records router module
    # This is needed because require_permission(action) creates a new dependency
    with patch("app.modules.records.router.require_permission", return_value=lambda: None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# --- Helpers ---

async def create_test_category(
    db: AsyncSession,
    name: str = "Salary",
    cat_type: CategoryType = CategoryType.INCOME,
) -> Category:
    category = Category(name=name, type=cat_type)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def seed_record(
    db: AsyncSession,
    user_id,
    category_id: int,
    amount: float = 100.0,
    r_type: RecordType = RecordType.INCOME,
    notes: str = "Test note",
) -> FinancialRecord:
    record = FinancialRecord(
        user_id=user_id,
        amount=amount,
        type=r_type,
        category_id=category_id,
        notes=notes,
        date=datetime(2024, 1, 15, 12, 0, 0),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def build_create_payload(
    category_id: int,
    amount: float = 150.0,
    r_type: str = "income",
    notes: str = "New record",
    date: str = "2024-06-15T10:00:00",
) -> dict:
    return {
        "amount": amount,
        "type": r_type,
        "category_id": category_id,
        "notes": notes,
        "date": date,
    }


# --- Integration Tests ---


@pytest.mark.asyncio
async def test_create_record_success(client: AsyncClient, db_session: AsyncSession):
    category = await create_test_category(db_session)
    payload = build_create_payload(category.id)

    response = await client.post("/records/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Record created successfully"
    assert data["data"]["amount"] == 150.0
    assert data["data"]["type"] == "income"
    assert data["data"]["category_id"] == category.id
    assert "id" in data["data"]

    result = await db_session.execute(select(FinancialRecord))
    records = result.scalars().all()
    assert len(records) == 1
    assert records[0].amount == 150.0


@pytest.mark.asyncio
async def test_create_record_validation_error_missing_fields(client: AsyncClient):
    payload = {"type": "income"}

    response = await client.post("/records/", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_record_validation_error_invalid_amount(
    client: AsyncClient, db_session: AsyncSession
):
    category = await create_test_category(db_session)
    payload = build_create_payload(category.id, amount=-50.0)

    response = await client.post("/records/", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_record_validation_error_zero_amount(
    client: AsyncClient, db_session: AsyncSession
):
    category = await create_test_category(db_session)
    payload = build_create_payload(category.id, amount=0.0)

    response = await client.post("/records/", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_records_empty(client: AsyncClient):
    response = await client.get("/records/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Records fetched successfully"
    assert data["data"]["items"] == []
    assert data["data"]["pagination"]["total_items"] == 0
    assert data["data"]["pagination"]["total_pages"] == 0


@pytest.mark.asyncio
async def test_get_records_with_data(client: AsyncClient, db_session: AsyncSession):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID

    await seed_record(db_session, mock_user_id, category.id, amount=100.0)
    await seed_record(db_session, mock_user_id, category.id, amount=200.0)

    response = await client.get("/records/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["items"]) == 2
    assert data["data"]["pagination"]["total_items"] == 2
    assert data["data"]["pagination"]["total_pages"] == 1


@pytest.mark.asyncio
async def test_get_records_with_type_filter(
    client: AsyncClient, db_session: AsyncSession
):
    cat_income = await create_test_category(db_session, "Salary", CategoryType.INCOME)
    cat_expense = await create_test_category(db_session, "Rent", CategoryType.EXPENSE)
    mock_user_id = MOCK_USER_ID

    await seed_record(db_session, mock_user_id, cat_income.id, r_type=RecordType.INCOME)
    await seed_record(db_session, mock_user_id, cat_expense.id, r_type=RecordType.EXPENSE)

    response = await client.get("/records/", params={"type": "expense"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["type"] == "expense"
    assert data["data"]["pagination"]["total_items"] == 1


@pytest.mark.asyncio
async def test_get_records_with_search_filter(
    client: AsyncClient, db_session: AsyncSession
):
    category = await create_test_category(db_session, "Groceries", CategoryType.EXPENSE)
    mock_user_id = MOCK_USER_ID

    await seed_record(db_session, mock_user_id, category.id, notes="Buy apples and bananas")
    await seed_record(db_session, mock_user_id, category.id, notes="Monthly rent payment")

    response = await client.get("/records/", params={"search": "apples"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["items"]) == 1
    assert "apples" in data["data"]["items"][0]["notes"]


@pytest.mark.asyncio
async def test_get_records_pagination(client: AsyncClient, db_session: AsyncSession):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID

    for _ in range(15):
        await seed_record(db_session, mock_user_id, category.id)

    response = await client.get("/records/", params={"page": 1, "page_size": 10})

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["items"]) == 10
    assert data["data"]["pagination"]["total_items"] == 15
    assert data["data"]["pagination"]["total_pages"] == 2
    assert data["data"]["pagination"]["page"] == 1

    response_page_2 = await client.get("/records/", params={"page": 2, "page_size": 10})
    data_p2 = response_page_2.json()
    assert len(data_p2["data"]["items"]) == 5


@pytest.mark.asyncio
async def test_update_record_success(client: AsyncClient, db_session: AsyncSession):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID
    record = await seed_record(db_session, mock_user_id, category.id, amount=100.0)

    update_payload = {"amount": 250.0, "notes": "Updated notes"}
    response = await client.put(f"/records/{record.id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Record updated successfully"
    assert data["data"]["amount"] == 250.0
    assert data["data"]["notes"] == "Updated notes"

    await db_session.refresh(record)
    assert record.amount == 250.0
    assert record.notes == "Updated notes"


@pytest.mark.asyncio
async def test_update_record_not_found(client: AsyncClient, db_session: AsyncSession):
    fake_id = uuid4()
    update_payload = {"amount": 250.0}

    response = await client.put(f"/records/{fake_id}", json=update_payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"


@pytest.mark.asyncio
async def test_update_record_partial_update(
    client: AsyncClient, db_session: AsyncSession
):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID
    record = await seed_record(
        db_session, mock_user_id, category.id, amount=100.0, notes="Original"
    )

    update_payload = {"notes": "Only notes changed"}
    response = await client.put(f"/records/{record.id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["amount"] == 100.0
    assert data["data"]["notes"] == "Only notes changed"


@pytest.mark.asyncio
async def test_delete_record_success(client: AsyncClient, db_session: AsyncSession):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID
    record = await seed_record(db_session, mock_user_id, category.id)

    response = await client.delete(f"/records/{record.id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Record deleted successfully"

    get_response = await client.get("/records/")
    assert len(get_response.json()["data"]["items"]) == 0

    await db_session.refresh(record)
    assert record.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_record_not_found(client: AsyncClient):
    fake_id = uuid4()

    response = await client.delete(f"/records/{fake_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"


@pytest.mark.asyncio
async def test_get_records_isolated_by_user(
    client: AsyncClient, db_session: AsyncSession
):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID
    other_user_id = uuid4()

    await seed_record(db_session, mock_user_id, category.id, amount=100.0)
    await seed_record(db_session, other_user_id, category.id, amount=500.0)

    response = await client.get("/records/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["amount"] == 100.0


@pytest.mark.asyncio
async def test_update_record_does_not_affect_other_users(
    client: AsyncClient, db_session: AsyncSession
):
    category = await create_test_category(db_session)
    mock_user_id = MOCK_USER_ID
    other_user_id = uuid4()

    other_record = await seed_record(
        db_session, other_user_id, category.id, amount=500.0, notes="Other user note"
    )

    update_payload = {"amount": 999.0}
    response = await client.put(f"/records/{other_record.id}", json=update_payload)

    assert response.status_code == 404

    await db_session.refresh(other_record)
    assert other_record.amount == 500.0