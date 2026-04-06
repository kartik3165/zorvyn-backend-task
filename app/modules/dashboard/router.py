from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.auth import User
from app.modules.auth.permission import get_current_user, require_permission
from app.modules.dashboard import service
from app.modules.dashboard.schemas import DashboardSummary, TrendsResponse
from app.utils.enums import PermissionAction


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_can_view_analytics = Depends(require_permission(PermissionAction.VIEW_ANALYTICS))
_can_run_advanced_analysis = Depends(require_permission(PermissionAction.ADVANCED_ANALYSIS))

@router.get(
    "/summary",
    response_model=DashboardSummary,
    dependencies=[_can_view_analytics],
    summary="Dashboard summary",
    description=(
        "Returns total income, total expense, net balance, record counts, "
        "category-wise totals, and the 10 most recent records. "
        "Optionally filter by date range."
    ),
)
async def get_summary(
    start_date: Optional[datetime] = Query(default=None, description="ISO 8601 start date"),
    end_date: Optional[datetime] = Query(default=None, description="ISO 8601 end date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    return await service.get_dashboard_summary(
        db=db,
        user_id=current_user.id, # type: ignore
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    dependencies=[_can_run_advanced_analysis],
    summary="Income and expense trends",
    description=(
        "Returns income, expense, and net values grouped by month and by week. "
        "Use the 'months' and 'weeks' query params to control how far back to look."
    ),
)
async def get_trends(
    months: int = Query(default=6, ge=1, le=24, description="Number of months to include"),
    weeks: int = Query(default=8, ge=1, le=52, description="Number of weeks to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrendsResponse:
    return await service.get_trends(
        db=db,
        user_id=current_user.id, # type: ignore
        months=months,
        weeks=weeks,
    )
