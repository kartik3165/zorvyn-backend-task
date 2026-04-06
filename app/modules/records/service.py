from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from uuid import UUID

from app.modules.records import repository


async def create_record_service(db: AsyncSession, data, user):
    return await repository.create_record(db, data, user.id)


async def get_records_service(db: AsyncSession, user, filters, page: int, page_size: int):
    return await repository.get_records(db, user.id, filters, page, page_size)


async def update_record_service(db: AsyncSession, record_id: UUID, data, user):
    record = await repository.get_record_by_id(db, record_id, user.id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )

    return await repository.update_record(db, record, data)


async def delete_record_service(db: AsyncSession, record_id: UUID, user):
    record = await repository.get_record_by_id(db, record_id, user.id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )

    return await repository.delete_record(db, record)
