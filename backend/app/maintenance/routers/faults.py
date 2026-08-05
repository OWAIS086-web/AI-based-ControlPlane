"""Fault record routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import forbidden, not_found
from app.maintenance.dependencies import get_maintenance_db, get_current_maintenance_user
from app.maintenance.models import FaultRecord, FaultSeverity, FaultStatus, MaintenanceUser
from app.maintenance.schemas import (
    FaultListResponse,
    FaultRecordCreate,
    FaultRecordOut,
    FaultRecordUpdate,
)

router = APIRouter(prefix="/maintenance/faults", tags=["Maintenance Faults"])

_LOAD = [
    selectinload(FaultRecord.reporter),
    selectinload(FaultRecord.assignee),
]


@router.get("", response_model=FaultListResponse)
async def list_faults(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(get_current_maintenance_user),
):
    q = select(FaultRecord).options(*_LOAD)
    if status:
        q = q.where(FaultRecord.status == FaultStatus(status))
    if severity:
        q = q.where(FaultRecord.severity == FaultSeverity(severity))

    count_result = await db.execute(select(FaultRecord.id).filter(q.whereclause) if q.whereclause is not None else select(FaultRecord.id))
    total = len(count_result.scalars().all())

    q = q.order_by(FaultRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    faults = result.scalars().all()

    total_pages = max(1, (total + page_size - 1) // page_size)
    return FaultListResponse(
        data=[FaultRecordOut.from_orm_model(f) for f in faults],
        meta={"total": total, "page": page, "pageSize": page_size, "totalPages": total_pages},
    )


@router.post("", response_model=FaultRecordOut, status_code=201)
async def create_fault(
    body: FaultRecordCreate,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
):
    fault = FaultRecord(
        title=body.title,
        description=body.description,
        location=body.location,
        severity=FaultSeverity(body.severity),
        reported_by=current_user.id,
    )
    db.add(fault)
    await db.commit()
    await db.refresh(fault)

    result = await db.execute(
        select(FaultRecord).options(*_LOAD).where(FaultRecord.id == fault.id)
    )
    return FaultRecordOut.from_orm_model(result.scalar_one())


@router.get("/{fault_id}", response_model=FaultRecordOut)
async def get_fault(
    fault_id: str,
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(get_current_maintenance_user),
):
    result = await db.execute(
        select(FaultRecord).options(*_LOAD).where(FaultRecord.id == fault_id)
    )
    fault = result.scalar_one_or_none()
    if not fault:
        raise not_found("Fault record")
    return FaultRecordOut.from_orm_model(fault)


@router.patch("/{fault_id}", response_model=FaultRecordOut)
async def update_fault(
    fault_id: str,
    body: FaultRecordUpdate,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
):
    result = await db.execute(
        select(FaultRecord).options(*_LOAD).where(FaultRecord.id == fault_id)
    )
    fault = result.scalar_one_or_none()
    if not fault:
        raise not_found("Fault record")

    # Technicians can only update faults they reported
    if current_user.role.value == "technician" and fault.reported_by != current_user.id:
        raise forbidden("Cannot update fault reported by another user.")

    if body.title is not None:
        fault.title = body.title
    if body.description is not None:
        fault.description = body.description
    if body.location is not None:
        fault.location = body.location
    if body.severity is not None:
        fault.severity = FaultSeverity(body.severity)
    if body.status is not None:
        fault.status = FaultStatus(body.status)
        if body.status == "resolved" and fault.resolved_at is None:
            fault.resolved_at = datetime.now(timezone.utc)
        elif body.status != "resolved":
            fault.resolved_at = None
    if body.assigned_to is not None:
        fault.assigned_to = body.assigned_to

    await db.commit()
    await db.refresh(fault)

    result = await db.execute(
        select(FaultRecord).options(*_LOAD).where(FaultRecord.id == fault.id)
    )
    return FaultRecordOut.from_orm_model(result.scalar_one())


@router.delete("/{fault_id}", status_code=204)
async def delete_fault(
    fault_id: str,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
):
    result = await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))
    fault = result.scalar_one_or_none()
    if not fault:
        raise not_found("Fault record")

    if current_user.role.value == "technician" and fault.reported_by != current_user.id:
        raise forbidden("Cannot delete fault reported by another user.")

    await db.delete(fault)
    await db.commit()
