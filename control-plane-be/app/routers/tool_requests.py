"""Tool fault report / request routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import tool_request_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.tool_request import (
    ToolRequestCreate,
    ToolRequestListResponse,
    ToolRequestMarkFaulty,
    ToolRequestOut,
    ToolRequestResolve,
)

router = APIRouter(tags=["Tool Requests"])


@router.get("/tool-requests", response_model=ToolRequestListResponse)
async def list_requests(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    # Line managers only see their own requests; process managers see all
    user_id = current_user.id if current_user.role == "line_manager" else None
    return await tool_request_controller.list_requests(status, page, limit, reported_by_user_id=user_id)


@router.get("/tool-requests/{request_id}", response_model=ToolRequestOut)
async def get_request(request_id: str, _=Depends(get_current_user)):
    return await tool_request_controller.get_request(request_id)


@router.post("/tool-requests", response_model=ToolRequestOut, status_code=201)
async def create_request(body: ToolRequestCreate, current_user=Depends(get_current_user)):
    return await tool_request_controller.create_request(
        body.reportedToolId,
        body.typeId,
        body.workerId,
        current_user.name,          # Always use the authenticated user's name
        body.notes,
        reported_by_user_id=current_user.id,
    )


@router.post("/tool-requests/{request_id}/mark-faulty", response_model=ToolRequestOut)
async def mark_faulty(
    request_id: str,
    body: ToolRequestMarkFaulty,
    current_user=Depends(require_process_manager),
):
    return await tool_request_controller.mark_faulty(request_id, body.note, current_user.id)


@router.post("/tool-requests/{request_id}/resolve", response_model=ToolRequestOut)
async def resolve_request(
    request_id: str,
    body: ToolRequestResolve,
    current_user=Depends(require_process_manager),
):
    return await tool_request_controller.resolve_request(
        request_id, body.replacementToolId, body.note, current_user.id
    )
