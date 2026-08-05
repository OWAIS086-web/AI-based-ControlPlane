"""Line type routes."""
from fastapi import APIRouter, Depends

from app.controllers import line_type_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.line_type import (
    LineTypeCreate,
    LineTypeOut,
    LineTypeReorderRequest,
    LineTypeUpdate,
)

router = APIRouter(prefix="/line-types", tags=["Line Types"])


@router.get("", response_model=list[LineTypeOut])
async def list_line_types(_=Depends(get_current_user)):
    return await line_type_controller.list_line_types()


@router.post("", response_model=LineTypeOut, status_code=201)
async def create_line_type(body: LineTypeCreate, _=Depends(require_process_manager)):
    return await line_type_controller.create_line_type(body.name, body.icon, body.color)


# /reorder must be defined BEFORE /{type_id} so FastAPI doesn't treat "reorder"
# as a type_id path parameter.
@router.patch("/reorder", response_model=list[LineTypeOut])
async def reorder_line_types(body: LineTypeReorderRequest, _=Depends(require_process_manager)):
    return await line_type_controller.reorder_line_types(body.ids)


@router.patch("/{type_id}", response_model=LineTypeOut)
async def update_line_type(
    type_id: str, body: LineTypeUpdate, _=Depends(require_process_manager)
):
    return await line_type_controller.update_line_type(type_id, body)


@router.delete("/{type_id}", status_code=204)
async def delete_line_type(type_id: str, _=Depends(require_process_manager)):
    await line_type_controller.delete_line_type(type_id)
