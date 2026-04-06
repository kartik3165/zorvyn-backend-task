from math import ceil

from sqlalchemy import String, cast, func, or_, select

from app.models.records import Category, FinancialRecord
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

async def create_record(db: AsyncSession, data, user_id: UUID):
    record = FinancialRecord(**data.dict(), user_id=user_id)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def _apply_record_filters(query, user_id: UUID, filters: dict):
    query = query.where(
        FinancialRecord.user_id == user_id,
        FinancialRecord.deleted_at.is_(None)
    )

    if filters.get("type"):
        query = query.where(FinancialRecord.type == filters["type"])

    if filters.get("category_id"):
        query = query.where(FinancialRecord.category_id == filters["category_id"])

    if filters.get("start_date"):
        query = query.where(FinancialRecord.date >= filters["start_date"])

    if filters.get("end_date"):
        query = query.where(FinancialRecord.date <= filters["end_date"])

    search = filters.get("search")
    search_value = search.strip() if isinstance(search, str) else None
    if search_value:
        search_term = f"%{search_value}%"
        query = query.outerjoin(Category, FinancialRecord.category_id == Category.id).where(
            or_(
                FinancialRecord.notes.ilike(search_term),
                Category.name.ilike(search_term),
                cast(FinancialRecord.type, String).ilike(search_term),
            )
        )

    return query


async def get_records(
    db: AsyncSession,
    user_id: UUID,
    filters: dict,
    page: int,
    page_size: int,
):
    base_query = _apply_record_filters(select(FinancialRecord), user_id, filters)
    count_query = _apply_record_filters(select(func.count()).select_from(FinancialRecord), user_id, filters)

    total_items = (await db.execute(count_query)).scalar_one()
    total_pages = ceil(total_items / page_size) if total_items else 0
    offset = (page - 1) * page_size

    records_query = (
        base_query
        .order_by(FinancialRecord.date.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(records_query)

    return {
        "items": result.scalars().all(),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
    }


async def get_record_by_id(db: AsyncSession, record_id: UUID, user_id: UUID):
    query = select(FinancialRecord).where(
        FinancialRecord.id == record_id,
        FinancialRecord.user_id == user_id,
        FinancialRecord.deleted_at.is_(None)
    )

    result = await db.execute(query)
    return result.scalars().first()


async def update_record(db: AsyncSession, record, data):
    for key, value in data.dict(exclude_unset=True).items():
        setattr(record, key, value)
    await db.commit()
    await db.refresh(record)
    return record

    
async def delete_record(db: AsyncSession, record):
    record.deleted_at = func.now()
    await db.commit()
