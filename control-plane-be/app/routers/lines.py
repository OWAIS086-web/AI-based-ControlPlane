"""Assembly lines routes."""
from fastapi import APIRouter, Depends

from app.controllers import line_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.assembly_line import (
    AssemblyLineCreate,
    AssemblyLineOut,
    AssemblyLineReorderRequest,
    AssemblyLineUpdate,
    AssignManagerRequest,
)

router = APIRouter(prefix="/lines", tags=["Assembly Lines"])


@router.get("", response_model=list[AssemblyLineOut])
async def list_lines(_=Depends(get_current_user)):
    return await line_controller.list_lines()


@router.post("", response_model=AssemblyLineOut, status_code=201)
async def create_line(body: AssemblyLineCreate, current_user=Depends(require_process_manager)):
    return await line_controller.create_line(body, current_user.id)


# /reorder must be before /{line_id} to avoid "reorder" being treated as a line_id
@router.patch("/reorder", response_model=list[AssemblyLineOut])
async def reorder_lines(
    body: AssemblyLineReorderRequest, _=Depends(require_process_manager)
):
    return await line_controller.reorder_lines(body.ids)


@router.get("/{line_id}", response_model=AssemblyLineOut)
async def get_line(line_id: str, _=Depends(get_current_user)):
    return await line_controller.get_line(line_id)


@router.patch("/{line_id}", response_model=AssemblyLineOut)
async def update_line(
    line_id: str, body: AssemblyLineUpdate, current_user=Depends(require_process_manager)
):
    return await line_controller.update_line(line_id, body, current_user.id)


@router.delete("/{line_id}", status_code=204)
async def delete_line(line_id: str, current_user=Depends(require_process_manager)):
    await line_controller.delete_line(line_id, current_user.id)


@router.patch("/{line_id}/manager", response_model=AssemblyLineOut)
async def assign_manager(
    line_id: str,
    body: AssignManagerRequest,
    current_user=Depends(require_process_manager),
):
    return await line_controller.assign_manager(line_id, body.managerId, current_user.id)
