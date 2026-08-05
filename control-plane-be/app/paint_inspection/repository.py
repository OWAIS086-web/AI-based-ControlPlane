from datetime import date
from typing import Optional

from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.paint_inspection.models import PaintInspection, InspectionDefect, VehiclePart
from app.paint_inspection.schemas import PaintInspectionCreate, PaintInspectionUpdate


class PaintInspectionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: PaintInspectionCreate, user_id: str) -> PaintInspection:
        total_problems = sum(d.total_qty or 0 for d in data.defects)
        inspection = PaintInspection(
            inspection_date=data.inspection_date,
            painting_date=data.painting_date,
            oven_out_time=data.oven_out_time,
            color=data.color,
            vin_no=data.vin_no,
            total_problems=total_problems,
            checked_by=data.checked_by,
            confirmed_by=data.confirmed_by,
            approved_by=data.approved_by,
            created_by_id=user_id,
        )
        self.db.add(inspection)
        await self.db.flush()

        for defect_data in data.defects:
            defect = InspectionDefect(inspection_id=inspection.id, **defect_data.model_dump())
            self.db.add(defect)

        for part_data in data.vehicle_parts:
            part = VehiclePart(inspection_id=inspection.id, **part_data.model_dump())
            self.db.add(part)

        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def get_by_id(self, inspection_id: int) -> Optional[PaintInspection]:
        result = await self.db.execute(
            select(PaintInspection).where(PaintInspection.id == inspection_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 20,
        vin_no: Optional[str] = None,
        color: Optional[str] = None,
        inspection_date_from: Optional[date] = None,
        inspection_date_to: Optional[date] = None,
        checked_by: Optional[str] = None,
    ):
        conditions = []
        if vin_no:
            conditions.append(PaintInspection.vin_no.ilike(f"%{vin_no}%"))
        if color:
            conditions.append(PaintInspection.color.ilike(f"%{color}%"))
        if inspection_date_from:
            conditions.append(PaintInspection.inspection_date >= inspection_date_from)
        if inspection_date_to:
            conditions.append(PaintInspection.inspection_date <= inspection_date_to)
        if checked_by:
            conditions.append(PaintInspection.checked_by.ilike(f"%{checked_by}%"))

        query = select(PaintInspection)
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(PaintInspection.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        import math
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return items, total, total_pages

    async def update(self, inspection: PaintInspection, data: PaintInspectionUpdate) -> PaintInspection:
        inspection.inspection_date = data.inspection_date
        inspection.painting_date = data.painting_date
        inspection.oven_out_time = data.oven_out_time
        inspection.color = data.color
        inspection.vin_no = data.vin_no
        inspection.total_problems = sum(d.total_qty or 0 for d in data.defects)
        inspection.checked_by = data.checked_by
        inspection.confirmed_by = data.confirmed_by
        inspection.approved_by = data.approved_by

        await self.db.execute(
            delete(InspectionDefect).where(InspectionDefect.inspection_id == inspection.id)
        )
        await self.db.execute(
            delete(VehiclePart).where(VehiclePart.inspection_id == inspection.id)
        )

        for defect_data in data.defects:
            defect = InspectionDefect(inspection_id=inspection.id, **defect_data.model_dump())
            self.db.add(defect)

        for part_data in data.vehicle_parts:
            part = VehiclePart(inspection_id=inspection.id, **part_data.model_dump())
            self.db.add(part)

        await self.db.commit()
        await self.db.refresh(inspection)
        return inspection

    async def delete(self, inspection: PaintInspection) -> None:
        await self.db.delete(inspection)
        await self.db.commit()

    async def search(self, q: str) -> list[PaintInspection]:
        result = await self.db.execute(
            select(PaintInspection).where(
                PaintInspection.vin_no.ilike(f"%{q}%")
            ).limit(20)
        )
        return list(result.scalars().all())
