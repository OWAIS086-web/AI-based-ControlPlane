"""Migrations routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import migration_controller
from app.dependencies import require_process_manager
from app.schemas.migration import MigrationCreate, MigrationRecordOut

router = APIRouter(prefix="/migrations", tags=["Migrations"])


@router.get("", response_model=dict)
async def list_migrations(
    status: str | None = Query(None),
    fromLineId: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(require_process_manager),
):
    return await migration_controller.list_migrations(status, fromLineId, page, limit)


@router.post("", response_model=MigrationRecordOut, status_code=202)
async def create_migration(body: MigrationCreate, current_user=Depends(require_process_manager)):
    return await migration_controller.create_migration(
        body.fromLineId, body.fromStationId,
        body.toLineId, body.toStationId,
        body.processIds, current_user.id,
    )


@router.get("/{migration_id}", response_model=MigrationRecordOut)
async def get_migration(migration_id: str, _=Depends(require_process_manager)):
    return await migration_controller.get_migration(migration_id)
