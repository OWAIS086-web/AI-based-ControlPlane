"""Process version service — upload, diff, compare."""
import asyncio
import json
import logging
from collections import defaultdict

from prisma import Json

from app.core.exceptions import conflict, not_found, unprocessable
from app.prisma_client import db
from app.helpers.diff import compute_deep_diff
from app.helpers.metadata import extract_all_text, extract_excel_metadata
from app.utils.audit import write_audit
from app.utils.storage import download_file, get_presigned_download_url, upload_file
from app.websocket.manager import ws_manager
from app.sse.manager import ai_sse

_log = logging.getLogger("app")

ALLOWED_TYPES = {"text/csv", "application/vnd.ms-excel",
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}

# Guards check-then-create: prevents two concurrent uploads with the same extracted
# code from each creating a separate process. Released before upload_version runs.
_smart_upload_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# Guards version number assignment inside upload_version. Held only for the fast
# count+create DB ops — NOT during S3 upload or metadata extraction.
_version_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def list_versions(process_id: str, page: int, limit: int) -> dict:
    if not await db.process.find_unique(where={"id": process_id}):
        raise not_found("Process")

    where = {"processId": process_id, "deletedAt": None}
    total = await db.processversion.count(where=where)
    versions = await db.processversion.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include={"uploader": True},
        order={"createdAt": "desc"},
    )
    return {"versions": versions, "total": total}


async def upload_version(
    process_id: str,
    file_data: bytes,
    filename: str,
    content_type: str,
    commit_message: str,
    actor_id: str,
    max_size: int,
):
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise unprocessable(f"File must be one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if len(file_data) > max_size:
        raise unprocessable(f"File exceeds maximum size of {max_size // (1024*1024)}MB.")

    process = await db.process.find_unique(
        where={"id": process_id},
        include={"versions": {"where": {"deletedAt": None}, "order_by": {"createdAt": "desc"}, "take": 1}},
    )
    if not process:
        raise not_found("Process")

    # ── Slow ops — run concurrently, NO lock held ────────────────────────────
    # Extract metadata and validate process code (XLSX only — CSV/XLS skip silently)
    extracted = await asyncio.to_thread(extract_excel_metadata, file_data)
    file_extracted_code = extracted.get("extractedCode", "")

    if file_extracted_code:
        stored_code = getattr(process, "extractedCode", None)
        if stored_code and stored_code != file_extracted_code:
            raise unprocessable(
                f"File process code '{file_extracted_code}' does not match "
                f"the expected code for this process ('{stored_code}'). "
                "Upload rejected — wrong control plan file."
            )
        if not stored_code:
            await db.process.update(
                where={"id": process_id},
                data={"extractedCode": file_extracted_code},
            )

    # Capture previous version info before uploading
    prev_version = process.versions[0] if process.versions else None

    # S3 upload and full-text extraction — both slow, run without holding any lock
    file_url, file_size = await upload_file(file_data, filename, content_type)
    search_text = await asyncio.to_thread(extract_all_text, file_data)

    # ── Fast DB ops — hold per-process lock only here to assign version number ─
    async with _version_locks[process_id]:
        existing_count = await db.processversion.count(where={"processId": process_id})
        version_str = f"v{existing_count + 1}.0"

        version = await db.processversion.create(
            data={
                "process": {"connect": {"id": process_id}},
                "version": version_str,
                "fileUrl": file_url,
                "fileName": filename,
                "fileSize": file_size,
                "commitMessage": commit_message,
                "changes": 0,
                "uploader": {"connect": {"id": actor_id}},
                "diff": Json(json.dumps([])),
                "extractedData": Json(json.dumps(extracted)),
            },
            include={"uploader": True},
        )

    import datetime as _dt
    process_update: dict = {
        "hasMissingCp": False,
        "aiStatus": "ai_running",
        "aiUpdatedAt": _dt.datetime.now(_dt.UTC),
    }
    if search_text:
        process_update["searchText"] = search_text
    await db.process.update(where={"id": process_id}, data=process_update)

    await write_audit(
        "upload",
        f"Uploaded version {version_str} for process {process.code}",
        process.code,
        actor_id,
        {"versionId": version.id},
    )
    await ws_manager.broadcast("process.version.uploaded", {
        "id": version.id, "processId": process_id, "version": version_str,
    })
    await ai_sse.publish("ai.status", {"processId": process_id, "status": "ai_running"})

    # Fire-and-forget background diff task
    asyncio.create_task(
        _run_diff_background(
            process_id=process_id,
            version_id=version.id,
            version_str=version_str,
            process_code=process.code,
            actor_id=actor_id,
            prev_version_url=prev_version.fileUrl if prev_version else None,
            prev_version_name=prev_version.fileUrl.split("/")[-1] if prev_version else None,
            new_file_data=file_data,
            new_filename=filename,
        )
    )

    return version


async def _run_diff_background(
    process_id: str,
    version_id: str,
    version_str: str,
    process_code: str,
    actor_id: str,
    prev_version_url: str | None,
    prev_version_name: str | None,
    new_file_data: bytes,
    new_filename: str,
) -> None:
    """Compute diff against previous version, update the version record, push SSE."""
    import datetime
    try:
        diff_data: dict | list = []
        change_count = 0

        if prev_version_url:
            old_data = await download_file(prev_version_url)
            diff_data, change_count = await asyncio.to_thread(
                compute_deep_diff, old_data, prev_version_name, new_file_data, new_filename
            )

        await db.processversion.update(
            where={"id": version_id},
            data={"diff": Json(json.dumps(diff_data)), "changes": change_count},
        )
        await db.process.update(
            where={"id": process_id},
            data={"aiStatus": "completed", "aiUpdatedAt": datetime.datetime.now(datetime.UTC)},
        )
        await ai_sse.publish("ai.status", {"processId": process_id, "status": "completed", "changes": change_count})
        await ws_manager.broadcast("process.diff.completed", {
            "processId": process_id, "versionId": version_id, "changes": change_count,
        })
        await write_audit(
            "upload",
            f"Diff completed for version {version_str} of process {process_code}",
            process_code,
            actor_id,
            {"versionId": version_id, "changes": change_count},
        )

    except Exception as exc:
        _log.error("Background diff failed for version %s: %s", version_id, exc)
        import datetime as dt
        await db.process.update(
            where={"id": process_id},
            data={"aiStatus": "failed", "aiUpdatedAt": dt.datetime.now(dt.UTC)},
        )
        await ai_sse.publish("ai.status", {"processId": process_id, "status": "failed", "error": str(exc)})


async def get_version(process_id: str, version_id: str):
    version = await db.processversion.find_first(
        where={"id": version_id, "processId": process_id, "deletedAt": None}, include={"uploader": True}
    )
    if not version:
        raise not_found("Version")
    return version


async def restore_version(process_id: str, version_id: str, actor_id: str):
    """Restore a version by soft-deleting all non-deleted versions created after it."""
    from datetime import datetime, timezone

    process = await db.process.find_unique(where={"id": process_id})
    if not process:
        raise not_found("Process")

    target = await db.processversion.find_first(
        where={"id": version_id, "processId": process_id, "deletedAt": None}
    )
    if not target:
        raise not_found("Version")

    now = datetime.now(timezone.utc)
    deleted_count = await db.processversion.update_many(
        where={
            "processId": process_id,
            "deletedAt": None,
            "createdAt": {"gt": target.createdAt},
        },
        data={"deletedAt": now},
    )

    await write_audit(
        "restore",
        f"Restored version {target.version} for process {process.code}, soft-deleted {deleted_count} subsequent version(s)",
        process.code,
        actor_id,
        {"versionId": version_id, "deletedCount": deleted_count},
    )
    await ws_manager.broadcast("process.version.restored", {
        "id": version_id, "processId": process_id, "version": target.version,
    })

    return await db.processversion.find_first(
        where={"id": version_id}, include={"uploader": True}
    )


async def compare_versions(process_id: str, v1_id: str, v2_id: str) -> dict:
    v1 = await db.processversion.find_first(
        where={"id": v1_id, "processId": process_id}, include={"uploader": True}
    )
    v2 = await db.processversion.find_first(
        where={"id": v2_id, "processId": process_id}, include={"uploader": True}
    )
    if not v1 or not v2:
        raise not_found("One or both versions not found.")

    v2_diff = v2.diff
    if isinstance(v2_diff, str):
        try:
            v2_diff = json.loads(v2_diff)
        except Exception:
            v2_diff = None

    # Build summary depending on whether diff is the rich dict or the legacy list
    if isinstance(v2_diff, dict) and "summary" in v2_diff:
        s = v2_diff["summary"]
        summary = {
            "added": s.get("total_added", 0),
            "modified": s.get("total_modified", 0),
            "removed": s.get("total_removed", 0),
            "total_shape_added": s.get("total_shape_added", 0),
            "total_shape_removed": s.get("total_shape_removed", 0),
            "total_new_images": s.get("total_new_images", 0),
            "total_removed_images": s.get("total_removed_images", 0),
            "total_sheets_compared": s.get("total_sheets_compared", 0),
            "new_sheets": s.get("new_sheets", 0),
            "removed_sheets": s.get("removed_sheets", 0),
        }
    elif isinstance(v2_diff, list):
        added = sum(1 for d in v2_diff if d.get("oldValue") == "")
        removed = sum(1 for d in v2_diff if d.get("newValue") == "")
        modified = max(0, len(v2_diff) - added - removed)
        summary = {"added": added, "modified": modified, "removed": removed}
    else:
        summary = {"added": 0, "modified": 0, "removed": 0}

    return {
        "v1": v1,
        "v2": v2,
        "diff": v2_diff,
        "summary": summary,
    }


async def smart_excel_upload(
    line_id: str,
    station_id: str,
    car_model_id: str,
    file_data: bytes,
    filename: str,
    content_type: str,
    commit_message: str,
    actor_id: str,
    max_size: int,
) -> dict:
    """Smart upload: auto-create or auto-version a process from an Excel file.

    Flow:
    1. Validate file type / size.
    2. Validate line, station, and car model exist.
    3. Extract the process code from H9 (spaces stripped, CJK preserved).
    4. If H9 yields no code → return "rejected" response.
    5. Search for an active/archived process with matching
       lineId + stationId + carModelId + extractedCode.
       - Found  → upload a new version  → status "matched"
       - Not found → create a new process (name = H9 with CJK stripped)
                     then upload v1.0    → status "created"

    Returns a dict with keys: status, message, extractedCode, process, version.
    """
    import os
    from app.services.process_service import _create_process_with_code

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise unprocessable(f"File must be one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if len(file_data) > max_size:
        raise unprocessable(f"File exceeds maximum size of {max_size // (1024 * 1024)}MB.")

    if not await db.assemblyline.find_unique(where={"id": line_id}):
        raise not_found("Assembly line")
    station = await db.station.find_first(where={"id": station_id, "lineId": line_id})
    if not station:
        raise not_found("Station")
    if not await db.carmodel.find_unique(where={"id": car_model_id}):
        raise not_found("Car model")

    # Extract identifying code from H9
    extracted = await asyncio.to_thread(extract_excel_metadata, file_data)
    extracted_code = extracted.get("extractedCode", "")

    if not extracted_code:
        return {
            "status": "rejected",
            "message": (
                "Could not extract a process identifier from cell H9 of the uploaded file. "
                "Ensure H9 contains a non-empty value that is not purely Chinese characters."
            ),
            "extractedCode": "",
            "process": None,
            "version": None,
        }

    # Serialize find-then-create per (line, station, car, code) so concurrent
    # uploads with the same extracted code don't both pass the find_first check
    # empty-handed and each create a separate process.
    # Phase 1: find-or-create process — lock guards check-then-create only
    lock_key = f"{line_id}:{station_id}:{car_model_id}:{extracted_code}"
    process_name = None
    async with _smart_upload_locks[lock_key]:
        existing = await db.process.find_first(
            where={
                "lineId": line_id,
                "stationId": station_id,
                "carModelId": car_model_id,
                "extractedCode": extracted_code,
                "status": {"in": ["active", "archived"]},
            },
            include={
                "versions": {
                    "where": {"deletedAt": None},
                    "order_by": {"createdAt": "desc"},
                    "take": 1,
                }
            },
        )

        if existing:
            target_process_id = existing.id
            upload_status = "matched"
        else:
            process_name = extracted.get("processName", "").strip() or extracted_code
            new_process = await _create_process_with_code(
                line_id, station_id,
                lambda _name=process_name, _ec=extracted_code: {
                    "name": _name,
                    "extractedCode": _ec,
                    "lineId": line_id,
                    "station": {"connect": {"id": station_id}},
                    "carModel": {"connect": {"id": car_model_id}},
                },
            )
            target_process_id = new_process.id
            upload_status = "created"
    # ↑ Lock released — S3 upload + version creation now run concurrently

    # Phase 2: upload version (slow — runs without the process-creation lock)
    version = await upload_version(
        process_id=target_process_id,
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        commit_message=commit_message,
        actor_id=actor_id,
        max_size=max_size,
    )

    if upload_status == "created" and process_name:
        await write_audit(
            "upload",
            f"Auto-created process '{process_name}' via Excel upload",
            process_name,
            actor_id,
            {"extractedCode": extracted_code},
        )

    if upload_status == "matched":
        assert existing is not None
        process = await db.process.find_unique(
            where={"id": existing.id},
            include={"versions": {"where": {"deletedAt": None}, "order_by": {"createdAt": "desc"}}},
        )
        return {
            "status": "matched",
            "message": f"New version uploaded for existing process '{existing.name}'.",
            "extractedCode": extracted_code,
            "process": process,
            "version": version,
        }
    else:
        process = await db.process.find_unique(
            where={"id": target_process_id},
            include={"versions": {"where": {"deletedAt": None}, "order_by": {"createdAt": "desc"}}},
        )
        return {
            "status": "created",
            "message": f"New process '{process_name}' created and first version uploaded.",
            "extractedCode": extracted_code,
            "process": process,
            "version": version,
        }


async def get_raw_bytes(version) -> bytes:
    """Download the raw file bytes for a version from object storage."""
    return await download_file(version.fileUrl)


def get_download_url(version) -> str:
    """Return a presigned download URL for a version's raw file."""
    return get_presigned_download_url(version.fileUrl)


async def get_highlighted_xlsx(process_id: str, version_id: str) -> tuple[bytes, str]:
    """
    Download the version's xlsx from storage, apply diff highlights, and return
    (highlighted_bytes, suggested_filename).

    Delegates all ZIP+XML manipulation to highlighting_service.apply_highlights_to_xlsx
    so complex files with hidden sheets, VBA, or non-standard structures are safe.

    Highlight legend:
      Green (#92D050) — modified cells, added cells, newly added rows, added shapes
      (removed items are not highlighted)
    """
    from app.helpers.highlighting_service import apply_highlights_to_xlsx

    version = await get_version(process_id, version_id)
    raw_bytes = await download_file(version.fileUrl)

    diff_data = version.diff
    if isinstance(diff_data, str):
        try:
            diff_data = json.loads(diff_data)
        except Exception:
            diff_data = None
    if not isinstance(diff_data, dict) or "sheets" not in diff_data:
        return raw_bytes, version.fileUrl.split("/")[-1]

    highlighted = apply_highlights_to_xlsx(raw_bytes, diff_data)
    base_name = version.fileUrl.split("/")[-1]
    return highlighted, f"highlighted_{version.version}_{base_name}"
