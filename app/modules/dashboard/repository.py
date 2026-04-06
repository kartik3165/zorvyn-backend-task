from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.records import FinancialRecord
from app.utils.enums import RecordType


async def get_totals_by_type(
    db: AsyncSession,
    user_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """
    Returns total amount and record count grouped by RecordType (INCOME / EXPENSE).
    Excludes soft-deleted records.
    """
    query = (
        select(
            FinancialRecord.type,
            func.coalesce(func.sum(FinancialRecord.amount), 0.0).label("total"),
            func.count(FinancialRecord.id).label("count"),
        )
        .where(
            FinancialRecord.user_id == user_id,
            FinancialRecord.deleted_at.is_(None),
        )
        .group_by(FinancialRecord.type)
    )

    if start_date:
        query = query.where(FinancialRecord.date >= start_date)
    if end_date:
        query = query.where(FinancialRecord.date <= end_date)

    result = await db.execute(query)
    return {row.type: {"total": float(row.total), "count": row.count} for row in result.all()}


async def get_totals_by_category(
    db: AsyncSession,
    user_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list:
    """
    Returns sum and count of records grouped by category_id.
    Excludes soft-deleted records.
    """
    query = (
        select(
            FinancialRecord.category_id,
            func.coalesce(func.sum(FinancialRecord.amount), 0.0).label("total"),
            func.count(FinancialRecord.id).label("count"),
        )
        .where(
            FinancialRecord.user_id == user_id,
            FinancialRecord.deleted_at.is_(None),
        )
        .group_by(FinancialRecord.category_id)
        .order_by(func.sum(FinancialRecord.amount).desc())
    )

    if start_date:
        query = query.where(FinancialRecord.date >= start_date)
    if end_date:
        query = query.where(FinancialRecord.date <= end_date)

    result = await db.execute(query)
    return result.all() # type: ignore


async def get_recent_records(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10,
) -> list:
    """
    Returns the N most recent non-deleted records for the user.
    """
    query = (
        select(FinancialRecord)
        .where(
            FinancialRecord.user_id == user_id,
            FinancialRecord.deleted_at.is_(None),
        )
        .order_by(FinancialRecord.date.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all() # type: ignore


async def get_monthly_trends(
    db: AsyncSession,
    user_id: UUID,
    months: int = 6,
) -> list:
    """
    Returns income and expense totals grouped by year+month for the last N months.
    Uses PostgreSQL extract() — matches the existing TIMESTAMP(timezone=True) columns.
    """
    query = (
        select(
            extract("year", FinancialRecord.date).label("year"),
            extract("month", FinancialRecord.date).label("month"),
            FinancialRecord.type,
            func.coalesce(func.sum(FinancialRecord.amount), 0.0).label("total"),
        )
        .where(
            FinancialRecord.user_id == user_id,
            FinancialRecord.deleted_at.is_(None),
        )
        .group_by(
            extract("year", FinancialRecord.date),
            extract("month", FinancialRecord.date),
            FinancialRecord.type,
        )
        .order_by(
            extract("year", FinancialRecord.date).desc(),
            extract("month", FinancialRecord.date).desc(),
        )
        .limit(months * 2)  
    )

    result = await db.execute(query)
    return result.all() # type: ignore


async def get_weekly_trends(
    db: AsyncSession,
    user_id: UUID,
    weeks: int = 8,
) -> list:
    """
    Returns income and expense totals grouped by year+week for the last N weeks.
    """
    query = (
        select(
            extract("year", FinancialRecord.date).label("year"),
            extract("week", FinancialRecord.date).label("week"),
            FinancialRecord.type,
            func.coalesce(func.sum(FinancialRecord.amount), 0.0).label("total"),
        )
        .where(
            FinancialRecord.user_id == user_id,
            FinancialRecord.deleted_at.is_(None),
        )
        .group_by(
            extract("year", FinancialRecord.date),
            extract("week", FinancialRecord.date),
            FinancialRecord.type,
        )
        .order_by(
            extract("year", FinancialRecord.date).desc(),
            extract("week", FinancialRecord.date).desc(),
        )
        .limit(weeks * 2)  # 2 rows per week (income + expense)
    )

    result = await db.execute(query)
    return result.all() # type: ignore