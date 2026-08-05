"""Process versions controller — serialisation, streaming, delegation."""
import json
import os
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.core.exceptions import unprocessable
from app.core.utils import ev
from app.schemas.common import make_paginated
from app.schemas.process_version import ProcessVersionOut, VersionCompareOut
from app.schemas.user import UserOut
from app.services import version_service


_CONTENT_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
}


def _content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Build a Content-Disposition header safe for non-ASCII filenames (RFC 5987)."""
    try:
        filename.encode("latin-1")
        return f'{disposition}; filename="{filename}"'
    except UnicodeEncodeError:
        encoded = quote(filename, safe="")
        ascii_fallback = filename.encode("ascii", "ignore").decode() or "download"
        return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _user_out(u) -> UserOut | None:
    if not u:
        return None
    return UserOut(
        id=u.id, name=u.name, email=u.email, role=ev(u.role),
        status=ev(u.status), avatar=u.avatar, createdAt=u.createdAt, updatedAt=u.updatedAt,
    )


def _out(v) -> ProcessVersionOut:
    return ProcessVersionOut(
        id=v.id, processId=v.processId, version=v.version,
        fileUrl=v.fileUrl, fileName=getattr(v, "fileName", None),
        fileSize=v.fileSize, commitMessage=v.commitMessage,
        changes=v.changes, uploadedBy=v.uploadedBy,
        uploader=_user_out(getattr(v, "uploader", None)),
        extractedData=json.loads(v.extractedData) if isinstance(v.extractedData, str) else v.extractedData,
        diff=v.diff,
        createdAt=v.createdAt,
        deletedAt=v.deletedAt,
    )


async def list_versions(process_id: str, page: int, limit: int) -> dict:
    result = await version_service.list_versions(process_id, page, limit)
    return make_paginated([_out(v) for v in result["versions"]], result["total"], page, limit)


async def upload_version(
    process_id: str,
    file_data: bytes,
    filename: str,
    content_type: str,
    commit_message: str,
    actor_id: str,
) -> ProcessVersionOut:
    if not commit_message.strip():
        raise unprocessable("commitMessage cannot be empty.")
    version = await version_service.upload_version(
        process_id=process_id,
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        commit_message=commit_message.strip(),
        actor_id=actor_id,
        max_size=settings.max_upload_size_bytes,
    )
    return _out(version)


async def compare_versions(process_id: str, v1: str, v2: str) -> VersionCompareOut:
    result = await version_service.compare_versions(process_id, v1, v2)
    return VersionCompareOut(
        v1=_out(result["v1"]),
        v2=_out(result["v2"]),
        diff=result["diff"],
        summary=result["summary"],
    )


async def download_version(process_id: str, version_id: str) -> StreamingResponse:
    version = await version_service.get_version(process_id, version_id)
    raw_bytes = await version_service.get_raw_bytes(version)
    filename = version.fileUrl.split("/")[-1]
    ext = os.path.splitext(filename)[1].lower()
    media_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    return StreamingResponse(
        iter([raw_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


async def get_version_pdf(process_id: str, version_id: str) -> StreamingResponse:
    from app.helpers.pdf_service import xlsx_to_pdf
    version = await version_service.get_version(process_id, version_id)
    raw_bytes = await version_service.get_raw_bytes(version)
    try:
        pdf_bytes = xlsx_to_pdf(raw_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    base_name = version.fileUrl.split("/")[-1].rsplit(".", 1)[0]
    filename = f"{base_name}_{version.version}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(filename, "inline")},
    )


async def get_highlighted_version_pdf(process_id: str, version_id: str) -> StreamingResponse:
    from app.helpers.pdf_service import xlsx_to_pdf
    xlsx_bytes, xlsx_name = await version_service.get_highlighted_xlsx(process_id, version_id)
    try:
        pdf_bytes = xlsx_to_pdf(xlsx_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    base_name = xlsx_name.rsplit(".", 1)[0]
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(f"{base_name}.pdf", "inline")},
    )


async def get_highlighted_version(process_id: str, version_id: str) -> StreamingResponse:
    xlsx_bytes, filename = await version_service.get_highlighted_xlsx(process_id, version_id)
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


async def restore_version(process_id: str, version_id: str, actor_id: str) -> ProcessVersionOut:
    version = await version_service.restore_version(process_id, version_id, actor_id)
    return _out(version)


async def get_version(process_id: str, version_id: str) -> ProcessVersionOut:
    return _out(await version_service.get_version(process_id, version_id))
