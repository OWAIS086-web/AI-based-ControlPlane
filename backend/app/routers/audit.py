"""Audit routes."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.controllers import audit_controller
from app.dependencies import require_process_manager
from app.schemas.audit import AuditStatsOut

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=dict)
async def list_audit(
    type: str | None = Query(None),
    performedBy: str | None = Query(None),
    search: str | None = Query(None),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(require_process_manager),
):
    return await audit_controller.list_audit(type, performedBy, search, from_, to, page, limit)


@router.get("/stats", response_model=AuditStatsOut)
async def audit_stats(_=Depends(require_process_manager)):
    return await audit_controller.get_stats()
