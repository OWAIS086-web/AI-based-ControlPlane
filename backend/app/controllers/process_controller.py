"""Processes controller — serialisation and delegation."""
import json

from app.config import settings
from app.core.utils import ev
from app.schemas.common import make_paginated
from app.schemas.process import ExcelUploadOut, ProcessOut
from app.schemas.process_version import ProcessVersionOut
from app.schemas.user import UserOut
from app.services import process_service, version_service


def _version_out(v) -> ProcessVersionOut | None:
    if not v:
        return None
    return ProcessVersionOut(
        id=v.id, processId=v.processId, version=v.version,
        fileUrl=v.fileUrl, fileName=getattr(v, "fileName", None),
        fileSize=v.fileSize, commitMessage=v.commitMessage,
        changes=v.changes, uploadedBy=v.uploadedBy,
        diff=v.diff if isinstance(v.diff, list) else [],
        createdAt=v.createdAt,
    )


def _version_out_full(v) -> ProcessVersionOut | None:
    """Version serialiser that includes uploader and extractedData."""
    if not v:
        return None
    uploader = getattr(v, "uploader", None)
    uploader_out = (
        UserOut(
            id=uploader.id, name=uploader.name, email=uploader.email,
            role=ev(uploader.role), status=ev(uploader.status),
            avatar=uploader.avatar,
            createdAt=uploader.createdAt, updatedAt=uploader.updatedAt,
        )
        if uploader else None
    )
    return ProcessVersionOut(
        id=v.id, processId=v.processId, version=v.version,
        fileUrl=v.fileUrl, fileName=getattr(v, "fileName", None),
        fileSize=v.fileSize, commitMessage=v.commitMessage,
        changes=v.changes, uploadedBy=v.uploadedBy,
        uploader=uploader_out,
        extractedData=json.loads(v.extractedData) if isinstance(v.extractedData, str) else v.extractedData,
        diff=v.diff,
        createdAt=v.createdAt,
        deletedAt=v.deletedAt,
    )


def _out(p) -> ProcessOut:
    latest = _version_out(p.versions[0]) if p.versions else None
    assignment = getattr(p, "assignment", None)
    worker_id   = assignment.workerId if assignment else None
    worker_name = assignment.worker.name if (assignment and getattr(assignment, "worker", None)) else None
    return ProcessOut(
        id=p.id, name=p.name, code=p.code,
        extractedCode=getattr(p, "extractedCode", None),
        lineId=p.lineId, stationId=p.stationId, carModelId=p.carModelId,
        status=ev(p.status), hasMissingCp=p.hasMissingCp,
        aiStatus=ev(getattr(p, "aiStatus", "idle")) or "idle",
        versionCount=len(p.versions) if p.versions else 0,
        latestVersion=latest,
        workerId=worker_id,
        workerName=worker_name,
        createdAt=p.createdAt, updatedAt=p.updatedAt,
    )


async def list_processes(line_id, station_id, car_model_id, status, has_missing_cp, search, page, limit) -> dict:
    result = await process_service.list_processes(
        line_id, station_id, car_model_id, status, has_missing_cp, search, page, limit
    )
    return make_paginated([_out(p) for p in result["processes"]], result["total"], page, limit)


async def get_process(process_id: str) -> ProcessOut:
    return _out(await process_service.get_process(process_id))


async def delete_process(process_id: str, actor_id: str) -> None:
    await process_service.delete_process(process_id, actor_id)


async def update_process_status(process_id: str, status: str, actor_id: str) -> ProcessOut:
    return _out(await process_service.update_process_status(process_id, status, actor_id))


async def bulk_update_status(ids: list[str], status: str, actor_id: str) -> int:
    return await process_service.bulk_update_status(ids, status, actor_id)


async def bulk_delete(ids: list[str], actor_id: str) -> int:
    return await process_service.bulk_delete(ids, actor_id)


async def list_line_processes(line_id: str) -> list[ProcessOut]:
    processes = await process_service.list_line_processes(line_id)
    return [_out(p) for p in processes]


async def list_station_processes(line_id, station_id, status, car_model_id, page, limit) -> dict:
    result = await process_service.list_station_processes(
        line_id, station_id, status, car_model_id, page, limit
    )
    return make_paginated([_out(p) for p in result["processes"]], result["total"], page, limit)


async def create_process(line_id, station_id, name, car_model_id, actor_id) -> ProcessOut:
    return _out(
        await process_service.create_process(line_id, station_id, name, car_model_id, actor_id)
    )


async def bulk_create_processes(line_id, station_id, names, car_model_id, actor_id) -> list[ProcessOut]:
    created = await process_service.bulk_create_processes(line_id, station_id, names, car_model_id, actor_id)
    return [_out(p) for p in created]


async def import_processes(line_id, station_id, process_ids, car_model_id, mode, actor_id) -> list[ProcessOut]:
    created = await process_service.import_processes(
        line_id, station_id, process_ids, car_model_id, mode, actor_id
    )
    return [_out(p) for p in created]


async def excel_upload(
    line_id: str,
    station_id: str,
    car_model_id: str,
    file_data: bytes,
    filename: str,
    content_type: str,
    commit_message: str,
    actor_id: str,
) -> ExcelUploadOut:
    result = await version_service.smart_excel_upload(
        line_id=line_id,
        station_id=station_id,
        car_model_id=car_model_id,
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        commit_message=commit_message,
        actor_id=actor_id,
        max_size=settings.max_upload_size_bytes,
    )

    process = _out(result["process"]) if result.get("process") else None
    version = _version_out_full(result.get("version")) if result.get("version") else None

    return ExcelUploadOut(
        status=result["status"],
        message=result["message"],
        extractedCode=result["extractedCode"],
        process=process,
        version=version,
    )
