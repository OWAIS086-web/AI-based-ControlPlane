"""Fault comment routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import forbidden, not_found
from app.maintenance.dependencies import get_maintenance_db, get_current_maintenance_user
from app.maintenance.models import FaultComment, FaultRecord, MaintenanceUser
from app.maintenance.schemas import FaultCommentCreate, FaultCommentOut

router = APIRouter(prefix="/maintenance/faults", tags=["Maintenance Comments"])


@router.get("/{fault_id}/comments", response_model=list[FaultCommentOut])
async def list_comments(
    fault_id: str,
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(get_current_maintenance_user),
):
    fault = await db.get(FaultRecord, fault_id)
    if not fault:
        raise not_found("Fault record")

    result = await db.execute(
        select(FaultComment)
        .options(selectinload(FaultComment.author))
        .where(FaultComment.fault_id == fault_id)
        .order_by(FaultComment.created_at.asc())
    )
    return [FaultCommentOut.from_orm_model(c) for c in result.scalars().all()]


@router.post("/{fault_id}/comments", response_model=FaultCommentOut, status_code=201)
async def add_comment(
    fault_id: str,
    body: FaultCommentCreate,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
):
    fault = await db.get(FaultRecord, fault_id)
    if not fault:
        raise not_found("Fault record")

    comment = FaultComment(fault_id=fault_id, user_id=current_user.id, body=body.body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    result = await db.execute(
        select(FaultComment)
        .options(selectinload(FaultComment.author))
        .where(FaultComment.id == comment.id)
    )
    return FaultCommentOut.from_orm_model(result.scalar_one())


@router.delete("/{fault_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    fault_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
):
    result = await db.execute(
        select(FaultComment).where(
            FaultComment.id == comment_id, FaultComment.fault_id == fault_id
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise not_found("Comment")

    if comment.user_id != current_user.id and current_user.role.value != "admin":
        raise forbidden("Cannot delete another user's comment.")

    await db.delete(comment)
    await db.commit()
