from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.utils.enums import RecordType


class RecordCreate(BaseModel):
    amount: float = Field(gt=0)
    type: RecordType
    category_id: int
    notes: Optional[str] = None
    date: datetime


class RecordUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    category_id: Optional[int] = None
    notes: Optional[str] = None
    date: Optional[datetime] = None


class RecordResponse(BaseModel):
    id: UUID
    amount: float
    type: RecordType
    category_id: int
    notes: Optional[str]
    date: datetime

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedRecordsResponse(BaseModel):
    items: list[RecordResponse]
    pagination: PaginationMeta
