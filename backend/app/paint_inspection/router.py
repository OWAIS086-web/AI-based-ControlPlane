from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.maintenance.dependencies import get_maintenance_db, get_current_maintenance_user
from app.paint_inspection.repository import PaintInspectionRepository
from app.paint_inspection.schemas import (
    PaintInspectionCreate,
    PaintInspectionUpdate,
    PaintInspectionResponse,
    PaintInspectionListResponse,
)

router = APIRouter(prefix="/paint-inspections", tags=["Paint Inspections"])


@router.post("", response_model=PaintInspectionResponse, status_code=201)
async def create_inspection(
    data: PaintInspectionCreate,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user=Depends(get_current_maintenance_user),
):
    repo = PaintInspectionRepository(db)
    return await repo.create(data, str(current_user.id))


@router.get("", response_model=PaintInspectionListResponse)
async def list_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vin_no: Optional[str] = None,
    color: Optional[str] = None,
    inspection_date_from: Optional[date] = None,
    inspection_date_to: Optional[date] = None,
    checked_by: Optional[str] = None,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user=Depends(get_current_maintenance_user),
):
    repo = PaintInspectionRepository(db)
    items, total, total_pages = await repo.get_list(
        page=page,
        page_size=page_size,
        vin_no=vin_no,
        color=color,
        inspection_date_from=inspection_date_from,
        inspection_date_to=inspection_date_to,
        checked_by=checked_by,
    )
    return PaintInspectionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search/query", response_model=list[PaintInspectionResponse])
async def search_inspections(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_maintenance_db),
    current_user=Depends(get_current_maintenance_user),
):
    repo = PaintInspectionRepository(db)
    return await repo.search(q)


@router.get("/{inspection_id}", response_model=PaintInspectionResponse)
async def get_inspection(
    inspection_id: int,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user=Depends(get_current_maintenance_user),
):
    repo = PaintInspectionRepository(db)
    inspection = await repo.get_by_id(inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return inspection


@router.put("/{inspection_id}", response_model=PaintInspectionResponse)
async def update_inspection(
    inspection_id: int,
    data: PaintInspectionUpdate,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user=Depends(get_current_maintenance_user),
):
    repo = PaintInspectionRepository(db)
    inspection = await repo.get_by_id(inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return await repo.update(inspection, data)


@router.delete("/{inspection_id}", status_code=204)
async def delete_inspection(
    inspection_id: int,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user=Depends(get_current_maintenance_user),
):
    repo = PaintInspectionRepository(db)
    inspection = await repo.get_by_id(inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    await repo.delete(inspection)
