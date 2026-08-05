"""Process versions routes."""
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.controllers import version_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.process_version import ProcessVersionOut, VersionCompareOut

router = APIRouter(prefix="/processes/{process_id}/versions", tags=["Process Versions"])


@router.get("", response_model=dict)
async def list_versions(
    process_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(get_current_user),
):
    return await version_controller.list_versions(process_id, page, limit)


@router.post("", response_model=ProcessVersionOut, status_code=201)
async def upload_version(
    process_id: str,
    file: UploadFile = File(...),
    commitMessage: str = Form(...),
    current_user=Depends(require_process_manager),
):
    file_data = await file.read()
    return await version_controller.upload_version(
        process_id=process_id,
        file_data=file_data,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        commit_message=commitMessage,
        actor_id=current_user.id,
    )


@router.get("/compare", response_model=VersionCompareOut)
async def compare_versions(
    process_id: str,
    v1: str = Query(...),
    v2: str = Query(...),
    _=Depends(get_current_user),
):
    return await version_controller.compare_versions(process_id, v1, v2)


@router.get("/{version_id}/download")
async def download_version(process_id: str, version_id: str, _=Depends(get_current_user)):
    return await version_controller.download_version(process_id, version_id)


@router.get("/{version_id}/pdf")
async def get_version_pdf(process_id: str, version_id: str, _=Depends(get_current_user)):
    return await version_controller.get_version_pdf(process_id, version_id)


@router.get("/{version_id}/highlighted-pdf")
async def get_highlighted_version_pdf(process_id: str, version_id: str, _=Depends(get_current_user)):
    return await version_controller.get_highlighted_version_pdf(process_id, version_id)


@router.get("/{version_id}/highlighted")
async def get_highlighted_version(process_id: str, version_id: str, _=Depends(get_current_user)):
    return await version_controller.get_highlighted_version(process_id, version_id)


@router.post("/{version_id}/restore", response_model=ProcessVersionOut)
async def restore_version(
    process_id: str,
    version_id: str,
    current_user=Depends(require_process_manager),
):
    return await version_controller.restore_version(process_id, version_id, current_user.id)


@router.get("/{version_id}", response_model=ProcessVersionOut)
async def get_version(process_id: str, version_id: str, _=Depends(get_current_user)):
    return await version_controller.get_version(process_id, version_id)
