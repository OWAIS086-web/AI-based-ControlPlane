"""Processes routes."""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.controllers import process_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.process import ExcelUploadOut, ProcessBulkCreate, ProcessBulkDelete, ProcessBulkStatusUpdate, ProcessCreate, ProcessImport, ProcessOut, ProcessStatusUpdate
from app.sse.manager import ai_sse
from app.prisma_client import db

router = APIRouter(tags=["Processes"])


# ── AI status SSE stream ──────────────────────────────────────────────────────

@router.get("/processes/ai-status/stream")
async def ai_status_stream(token: str = Query(...)):
    """SSE stream — authenticates via ?token= query param (EventSource can't send headers)."""
    from jose import JWTError
    from app.core.security import decode_token
    from app.core.exceptions import unauthorized
    try:
        payload = decode_token(token)
    except JWTError:
        raise unauthorized()
    if payload.get("type") != "access":
        raise unauthorized("Invalid token type.")
    user = await db.user.find_unique(where={"id": payload.get("sub", "")})
    if not user or str(getattr(user, "status", "")) == "inactive":
        raise unauthorized()

    return StreamingResponse(
        ai_sse.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Global process list ───────────────────────────────────────────────────────

@router.get("/processes", response_model=dict)
async def list_processes(
    lineId: str | None = Query(None),
    stationId: str | None = Query(None),
    carModelId: str | None = Query(None),
    status: str | None = Query(None),
    hasMissingCP: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(get_current_user),
):
    return await process_controller.list_processes(
        lineId, stationId, carModelId, status, hasMissingCP, search, page, limit
    )


@router.get("/processes/{process_id}", response_model=ProcessOut)
async def get_process(process_id: str, _=Depends(get_current_user)):
    return await process_controller.get_process(process_id)


@router.patch("/processes/bulk/status", response_model=dict)
async def bulk_update_status(body: ProcessBulkStatusUpdate, current_user=Depends(require_process_manager)):
    count = await process_controller.bulk_update_status(body.ids, body.status, current_user.id)
    return {"updated": count}


@router.post("/processes/bulk/delete", response_model=dict)
async def bulk_delete_processes(body: ProcessBulkDelete, current_user=Depends(require_process_manager)):
    count = await process_controller.bulk_delete(body.ids, current_user.id)
    return {"deleted": count}


@router.delete("/processes/{process_id}", status_code=204)
async def delete_process(process_id: str, current_user=Depends(require_process_manager)):
    await process_controller.delete_process(process_id, current_user.id)


@router.patch("/processes/{process_id}/status", response_model=ProcessOut)
async def update_process_status(
    process_id: str,
    body: ProcessStatusUpdate,
    current_user=Depends(require_process_manager),
):
    return await process_controller.update_process_status(process_id, body.status, current_user.id)


# ── Line-scoped process list (no pagination) ──────────────────────────────────

@router.get("/lines/{line_id}/processes", response_model=list[ProcessOut])
async def list_line_processes(line_id: str, _=Depends(get_current_user)):
    return await process_controller.list_line_processes(line_id)


# ── Station-scoped process list / create ─────────────────────────────────────

@router.get("/lines/{line_id}/stations/{station_id}/processes", response_model=dict)
async def list_station_processes(
    line_id: str,
    station_id: str,
    status: str | None = Query(None),
    carModelId: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(get_current_user),
):
    return await process_controller.list_station_processes(
        line_id, station_id, status, carModelId, page, limit
    )


@router.post("/lines/{line_id}/stations/{station_id}/processes", response_model=ProcessOut, status_code=201)
async def create_process(
    line_id: str,
    station_id: str,
    body: ProcessCreate,
    current_user=Depends(require_process_manager),
):
    return await process_controller.create_process(
        line_id, station_id, body.name, body.carModelId, current_user.id
    )


@router.post(
    "/lines/{line_id}/stations/{station_id}/processes/bulk",
    response_model=list[ProcessOut],
    status_code=201,
)
async def bulk_create_processes(
    line_id: str,
    station_id: str,
    body: ProcessBulkCreate,
    current_user=Depends(require_process_manager),
):
    return await process_controller.bulk_create_processes(
        line_id, station_id, body.names, body.carModelId, current_user.id
    )


@router.post(
    "/lines/{line_id}/stations/{station_id}/processes/import",
    response_model=list[ProcessOut],
    status_code=201,
)
async def import_processes(
    line_id: str,
    station_id: str,
    body: ProcessImport,
    current_user=Depends(require_process_manager),
):
    return await process_controller.import_processes(
        line_id, station_id, body.processIds, body.carModelId, body.mode, current_user.id
    )


# ── Smart Excel upload ────────────────────────────────────────────────────────

@router.post(
    "/lines/{line_id}/stations/{station_id}/excel-upload",
    response_model=ExcelUploadOut,
    status_code=201,
)
async def excel_upload(
    line_id: str,
    station_id: str,
    file: UploadFile = File(...),
    carModelId: str = Form(...),
    commitMessage: str = Form("Auto-uploaded"),
    current_user=Depends(require_process_manager),
):
    if not commitMessage.strip():
        commitMessage = "Auto-uploaded"
    file_data = await file.read()
    return await process_controller.excel_upload(
        line_id=line_id,
        station_id=station_id,
        car_model_id=carModelId,
        file_data=file_data,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        commit_message=commitMessage.strip(),
        actor_id=current_user.id,
    )
