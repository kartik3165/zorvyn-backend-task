from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.database.session import get_db
from app.modules.records import service, schemas
from app.modules.auth.permission import get_current_user, require_permission
from app.modules.auth.schemas import StandardResponse
from app.utils.enums import PermissionAction, RecordType

router = APIRouter(prefix="/records", tags=["Records"])

_can_view_records = Depends(require_permission(PermissionAction.VIEW_RECORDS))
_can_create_records = Depends(require_permission(PermissionAction.CREATE_RECORDS))
_can_update_records = Depends(require_permission(PermissionAction.UPDATE_RECORDS))
_can_delete_records = Depends(require_permission(PermissionAction.DELETE_RECORDS))

    
@router.get(
    "/",
    response_model=StandardResponse[schemas.PaginatedRecordsResponse],
    dependencies=[_can_view_records],
)
async def get_records(
    type: Optional[RecordType] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    filters = {
        "type": type,
        "category_id": category_id,
        "search": search,
        "start_date": start_date,
        "end_date": end_date
    }

    records = await service.get_records_service(db, user, filters, page, page_size)
    return StandardResponse(
        message="Records fetched successfully",
        data=records
    )

@router.post(
    "/",
    response_model=StandardResponse[schemas.RecordResponse],
    dependencies=[_can_create_records],
)
async def create_record(
    payload: schemas.RecordCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    record = await service.create_record_service(db, payload, user)

    return StandardResponse(
        message="Record created successfully",
        data=record
    )


@router.put(
    "/{record_id}",
    response_model=StandardResponse[schemas.RecordResponse],
    dependencies=[_can_update_records],
)
async def update_record(
    record_id: UUID,
    payload: schemas.RecordUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    record =  await service.update_record_service(db, record_id, payload, user)

    return StandardResponse(
        message="Record updated successfully",
        data=record
    )


@router.delete(
    "/{record_id}",
    response_model=StandardResponse[None],
    dependencies=[_can_delete_records],
)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    await service.delete_record_service(db, record_id, user)
    return StandardResponse(
        message="Record deleted successfully",
        data=None
    )
