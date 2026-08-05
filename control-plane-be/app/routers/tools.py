"""Tool type and tool management routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import tool_controller
from app.dependencies import require_process_manager, get_current_user
from app.schemas.tool import (
    ToolAssignRequest,
    ToolCreate,
    ToolListResponse,
    ToolOut,
    ToolStatusRequest,
    ToolTypeCreate,
    ToolTypeOut,
    ToolTypeUpdate,
    ToolUpdate,
)

router = APIRouter(tags=["Tools"])


# ── Tool Types ────────────────────────────────────────────────────────────────

@router.get("/tool-types", response_model=list[ToolTypeOut])
async def list_tool_types(_=Depends(get_current_user)):
    return await tool_controller.list_tool_types()


@router.post("/tool-types", response_model=ToolTypeOut, status_code=201)
async def create_tool_type(body: ToolTypeCreate, current_user=Depends(require_process_manager)):
    return await tool_controller.create_tool_type(body.name, body.maxPerWorker, current_user.id)


@router.patch("/tool-types/{type_id}", response_model=ToolTypeOut)
async def update_tool_type(type_id: str, body: ToolTypeUpdate, current_user=Depends(require_process_manager)):
    return await tool_controller.update_tool_type(type_id, body.name, body.maxPerWorker, current_user.id)


@router.delete("/tool-types/{type_id}", status_code=204)
async def delete_tool_type(type_id: str, current_user=Depends(require_process_manager)):
    await tool_controller.delete_tool_type(type_id, current_user.id)


# ── Tools ─────────────────────────────────────────────────────────────────────

@router.get("/tools/all", response_model=list[ToolOut])
async def list_all_tools(
    typeId: str | None = Query(None),
    status: str | None = Query(None),
    _=Depends(get_current_user),
):
    return await tool_controller.list_all_tools(typeId, status)


@router.get("/tools", response_model=ToolListResponse)
async def list_tools(
    search: str | None = Query(None),
    typeId: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _=Depends(require_process_manager),
):
    return await tool_controller.list_tools(search, typeId, status, page, limit)


@router.post("/tools", response_model=ToolOut, status_code=201)
async def create_tool(body: ToolCreate, current_user=Depends(require_process_manager)):
    return await tool_controller.create_tool(body.toolId, body.typeId, body.notes, current_user.id)


@router.get("/tools/{tool_db_id}", response_model=ToolOut)
async def get_tool(tool_db_id: str, _=Depends(require_process_manager)):
    return await tool_controller.get_tool(tool_db_id)


@router.patch("/tools/{tool_db_id}", response_model=ToolOut)
async def update_tool(tool_db_id: str, body: ToolUpdate, current_user=Depends(require_process_manager)):
    return await tool_controller.update_tool(tool_db_id, body.toolId, body.notes, current_user.id)


@router.delete("/tools/{tool_db_id}", status_code=204)
async def delete_tool(tool_db_id: str, current_user=Depends(require_process_manager)):
    await tool_controller.delete_tool(tool_db_id, current_user.id)


@router.post("/tools/{tool_db_id}/assign", response_model=ToolOut)
async def assign_tool(tool_db_id: str, body: ToolAssignRequest, current_user=Depends(require_process_manager)):
    return await tool_controller.assign_tool(tool_db_id, body.workerId, body.processId, current_user.id)


@router.post("/tools/{tool_db_id}/status", response_model=ToolOut)
async def set_tool_status(tool_db_id: str, body: ToolStatusRequest, current_user=Depends(require_process_manager)):
    return await tool_controller.set_tool_status(tool_db_id, body.status, body.note, current_user.id)
