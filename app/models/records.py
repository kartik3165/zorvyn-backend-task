from sqlalchemy import TIMESTAMP, Column, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.utils import generate_uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Index

from app.utils.enums import CategoryType, RecordType

class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    amount = Column(Float, nullable=False)
    type = Column(Enum(RecordType), nullable=False) 
    category_id = Column(Integer, ForeignKey("categories.id"))
    notes = Column(Text, nullable=True)
    date = Column(TIMESTAMP(timezone=True), nullable=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="records")

    __table_args__ = (
        Index("idx_records_user_id", "user_id"),
        Index("idx_records_user_date", "user_id", "date"),
        Index("idx_records_type", "type"),
        Index("idx_records_category", "category_id"),
        Index("idx_records_not_deleted", "deleted_at"),
        Index("idx_records_user_type_date", "user_id", "type", "date"),
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    type = Column(Enum(CategoryType), nullable=False) 
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_category_name", "name"),
        Index("idx_category_type", "type"),
    )