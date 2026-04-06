from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.enums import RecordType
from app.modules.dashboard import repository
from app.modules.dashboard.schemas import (
    CategorySummary,
    DashboardSummary,
    MonthlyTrend,
    RecentRecord,
    TrendsResponse,
    WeeklyTrend,
)


async def get_dashboard_summary(
    db: AsyncSession,
    user_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> DashboardSummary:
    """
    Aggregates total income, total expense, net balance, category breakdown,
    and recent activity into a single summary object for the dashboard.
    """
    type_totals = await repository.get_totals_by_type(db, user_id, start_date, end_date)
    category_rows = await repository.get_totals_by_category(db, user_id, start_date, end_date)
    recent_rows = await repository.get_recent_records(db, user_id, limit=10)

    income_data = type_totals.get(RecordType.INCOME, {"total": 0.0, "count": 0})
    expense_data = type_totals.get(RecordType.EXPENSE, {"total": 0.0, "count": 0})

    total_income: float = income_data["total"]
    total_expense: float = expense_data["total"]

    category_totals = [
        CategorySummary(
            category_id=row.category_id,
            total=float(row.total),
            count=row.count,
        )
        for row in category_rows
    ]

    recent_records = [
        RecentRecord(
            id=str(record.id),
            amount=record.amount,
            type=record.type.value,
            category_id=record.category_id,
            notes=record.notes,
            date=record.date.isoformat(),
        )
        for record in recent_rows
    ]

    return DashboardSummary(
        total_income=total_income,
        total_expense=total_expense,
        net_balance=round(total_income - total_expense, 2),
        record_count=income_data["count"] + expense_data["count"],
        income_count=income_data["count"],
        expense_count=expense_data["count"],
        category_totals=category_totals,
        recent_records=recent_records,
    )


async def get_trends(
    db: AsyncSession,
    user_id: UUID,
    months: int = 6,
    weeks: int = 8,
) -> TrendsResponse:
    """
    Builds monthly and weekly trend series. Each period has separate income,
    expense, and net values so a frontend chart can plot all three lines.
    """
    monthly_rows = await repository.get_monthly_trends(db, user_id, months)
    weekly_rows = await repository.get_weekly_trends(db, user_id, weeks)

    # --- monthly aggregation ------------------------------------------------
    # Each DB row is (year, month, type, total). Pivot into one dict per period.
    monthly_buckets: dict[tuple, dict] = {}
    for row in monthly_rows:
        key = (int(row.year), int(row.month))
        if key not in monthly_buckets:
            monthly_buckets[key] = {"income": 0.0, "expense": 0.0}
        if row.type == RecordType.INCOME:
            monthly_buckets[key]["income"] = float(row.total)
        else:
            monthly_buckets[key]["expense"] = float(row.total)

    monthly = [
        MonthlyTrend(
            year=year,
            month=month,
            income=data["income"],
            expense=data["expense"],
            net=round(data["income"] - data["expense"], 2),
        )
        for (year, month), data in sorted(monthly_buckets.items(), reverse=True)
    ]

    # --- weekly aggregation -------------------------------------------------
    weekly_buckets: dict[tuple, dict] = {}
    for row in weekly_rows:
        key = (int(row.year), int(row.week))
        if key not in weekly_buckets:
            weekly_buckets[key] = {"income": 0.0, "expense": 0.0}
        if row.type == RecordType.INCOME:
            weekly_buckets[key]["income"] = float(row.total)
        else:
            weekly_buckets[key]["expense"] = float(row.total)

    weekly = [
        WeeklyTrend(
            year=year,
            week=week,
            income=data["income"],
            expense=data["expense"],
            net=round(data["income"] - data["expense"], 2),
        )
        for (year, week), data in sorted(weekly_buckets.items(), reverse=True)
    ]

    return TrendsResponse(monthly=monthly, weekly=weekly)