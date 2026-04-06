from pydantic import BaseModel
from typing import Optional


class CategorySummary(BaseModel):
    category_id: int
    total: float
    count: int


class MonthlyTrend(BaseModel):
    year: int
    month: int
    income: float
    expense: float
    net: float


class WeeklyTrend(BaseModel):
    year: int
    week: int
    income: float
    expense: float
    net: float


class RecentRecord(BaseModel):
    id: str
    amount: float
    type: str
    category_id: int
    notes: Optional[str]
    date: str

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    total_income: float
    total_expense: float
    net_balance: float
    record_count: int
    income_count: int
    expense_count: int
    category_totals: list[CategorySummary]
    recent_records: list[RecentRecord]


class TrendsResponse(BaseModel):
    monthly: list[MonthlyTrend]
    weekly: list[WeeklyTrend]