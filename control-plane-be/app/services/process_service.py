"""Process service."""
import json
from typing import Callable

from prisma import Json

from app.core.exceptions import conflict, not_found
from app.prisma_client import db
from app.utils.audit import write_audit

# ── Shared include dict ───────────────────────────────────────────────────────
_VERSIONS_INCLUDE = {"where": {"deletedAt": None}, "order_by": {"createdAt": "desc"}}
_PROCESS_INCLUDE  = {
    "versions": _VERSIONS_INCLUDE,
    "assignment": {"include": {"worker": True}},
}


async def _next_process_code(line_id: str, station_id: str) -> str:
    """Auto-generate a unique process code like TRIM-S01-P04."""
    import re
    line = await db.assemblyline.find_unique(where={"id": line_id})
    station = await db.station.find_unique(where={"id": station_id})
    count = await db.process.count(where={"stationId": station_id})

    line_prefix = (line.id if line else line_id).upper()[:4]
    num_match = re.search(r"\d+", station.name if station else "")
    stn_num = num_match.group(0).zfill(2) if num_match else "01"

    # Find next available proc number (handles gaps from deletions)
    n = count + 1
    while True:
        candidate = f"{line_prefix}-S{stn_num}-P{str(n).zfill(2)}"
        existing = await db.process.find_first(where={"code": candidate})
        if not existing:
            return candidate
        n += 1


async def _create_process_with_code(
    line_id: str,
    station_id: str,
    make_data: Callable[[], dict],
    include: dict | None = None,
    max_retries: int = 10,
):
    """Create a process, retrying if a concurrent request steals the same code.

    make_data() returns the Prisma create-data dict *without* the 'code' key —
    this function generates the code and injects it.  Retries up to max_retries
    times on a unique-constraint violation on the code column.
    """
    try:
        from prisma.errors import UniqueViolationError
    except ImportError:
        from prisma.errors import PrismaError as UniqueViolationError  # type: ignore

    for attempt in range(max_retries):
        code = await _next_process_code(line_id, station_id)
        try:
            return await db.process.create(
                data={**make_data(), "code": code},
                include=include or _PROCESS_INCLUDE,
            )
        except UniqueViolationError:
            if attempt >= max_retries - 1:
                raise
            import asyncio
            await asyncio.sleep(0)


async def list_processes(
    line_id: str | None,
    station_id: str | None,
    car_model_id: str | None,
    status: str | None,
    has_missing_cp: bool | None,
    search: str | None,
    page: int,
    limit: int,
) -> dict:
    where: dict = {"status": {"in": ["active", "archived"]}}
    if line_id:
        where["lineId"] = line_id
    if station_id:
        where["stationId"] = station_id
    if car_model_id:
        where["carModelId"] = car_model_id
    if status:
        where["status"] = status
    if has_missing_cp is not None:
        where["hasMissingCp"] = has_missing_cp

    if search:
        # Partial substring search on search_text, name, and code (case-insensitive)
        # Also keep FTS for relevance
        fts_rows = await db.query_raw(
            """
            SELECT id FROM processes
            WHERE (
                search_text IS NOT NULL AND (
                    to_tsvector('simple', search_text) @@ plainto_tsquery('simple', $1)
                    OR search_text ILIKE $2
                )
            )
            OR name ILIKE $2
            OR code ILIKE $2
            """,
            search,
            f"%{search}%",
        )
        matched_ids = [r["id"] for r in fts_rows]
        where["id"] = {"in": matched_ids}

    print(f"DEBUG: list_processes where={where}, page={page}, limit={limit}")
    total = await db.process.count(where=where)
    processes = await db.process.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include=_PROCESS_INCLUDE,
        order={"createdAt": "desc"},
    )
    return {"processes": processes, "total": total}


async def list_line_processes(line_id: str) -> list:
    """Return all processes for a line without pagination."""
    return await db.process.find_many(
        where={"lineId": line_id, "status": {"in": ["active", "archived"]}},
        include=_PROCESS_INCLUDE,
        order={"createdAt": "desc"},
    )


async def list_station_processes(
    line_id: str,
    station_id: str,
    status: str | None,
    car_model_id: str | None,
    page: int,
    limit: int,
) -> dict:
    where: dict = {"stationId": station_id, "lineId": line_id, "status": {"in": ["active", "archived"]}}
    if status:
        where["status"] = status
    if car_model_id:
        where["carModelId"] = car_model_id

    total = await db.process.count(where=where)
    processes = await db.process.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include=_PROCESS_INCLUDE,
        order={"createdAt": "desc"},
    )
    return {"processes": processes, "total": total}


async def create_process(
    line_id: str, station_id: str, name: str, car_model_id: str, actor_id: str
):
    if not await db.assemblyline.find_unique(where={"id": line_id}):
        raise not_found("Assembly line")
    if not await db.station.find_first(where={"id": station_id, "lineId": line_id}):
        raise not_found("Station")
    if not await db.carmodel.find_unique(where={"id": car_model_id}):
        raise not_found("Car model")

    process = await _create_process_with_code(
        line_id, station_id,
        lambda: {
            "name": name,
            "lineId": line_id,
            "station": {"connect": {"id": station_id}},
            "carModel": {"connect": {"id": car_model_id}},
        },
    )
    await write_audit("upload", f"Created process: {process.code}", process.code, actor_id)
    return process

async def bulk_create_processes(
    line_id: str,
    station_id: str,
    names: list[str],
    car_model_id: str,
    actor_id: str,
) -> list:
    """
    Create multiple processes for a single station + car model in one call.
    Used when importing process names from another car model on the same station.
    Each process gets its own auto-generated code. Already-existing names for
    the same station + car model are skipped (no duplicates).
    Returns the list of newly created processes.
    """
    if not await db.assemblyline.find_unique(where={"id": line_id}):
        raise not_found("Assembly line")
    station = await db.station.find_first(where={"id": station_id, "lineId": line_id})
    if not station:
        raise not_found("Station")
    if not await db.carmodel.find_unique(where={"id": car_model_id}):
        raise not_found("Car model")

    # Deduplicate names that already exist for this station + car model
    existing = await db.process.find_many(
        where={"stationId": station_id, "carModelId": car_model_id},
        include={"versions": False},
    )
    existing_names = {p.name.strip().lower() for p in existing}
    new_names = [n.strip() for n in names if n.strip().lower() not in existing_names]
 
    if not new_names:
        return []
 
    created = []
    for name in new_names:
        process = await _create_process_with_code(
            line_id, station_id,
            lambda _name=name: {
                "name":     _name,
                "lineId":   line_id,
                "station":  {"connect": {"id": station_id}},
                "carModel": {"connect": {"id": car_model_id}},
            },
        )
        created.append(process)
 
    await write_audit(
        "upload",
        f"Bulk imported {len(created)} process(es) into station {station.name}",
        f"{len(created)} processes",
        actor_id,
    )
    return created


async def bulk_update_status(ids: list[str], status: str, actor_id: str) -> int:
    result = await db.process.update_many(
        where={"id": {"in": ids}, "status": {"not": "deleted"}},
        data={"status": status},
    )
    audit_type = "archive" if status == "archived" else "upload"
    await write_audit(audit_type, f"Bulk {status} {result} process(es)", f"{result} processes", actor_id)
    return result


async def bulk_delete(ids: list[str], actor_id: str) -> int:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    await db.processversion.update_many(
        where={"processId": {"in": ids}},
        data={"deletedAt": now},
    )
    result = await db.process.update_many(
        where={"id": {"in": ids}},
        data={"status": "deleted"},
    )
    await write_audit("delete", f"Bulk deleted {result} process(es)", f"{result} processes", actor_id)
    return result


async def get_process(process_id: str):
    process = await db.process.find_unique(
        where={"id": process_id},
        include=_PROCESS_INCLUDE,
    )
    if not process:
        raise not_found("Process")
    return process


async def delete_process(process_id: str, actor_id: str):
    from datetime import datetime, timezone

    process = await db.process.find_unique(where={"id": process_id})
    if not process or process.status == "deleted":
        raise not_found("Process")

    now = datetime.now(timezone.utc)

    await db.processversion.update_many(
        where={"processId": process_id},
        data={"deletedAt": now},
    )
    await db.process.update(
        where={"id": process_id},
        data={"status": "deleted"},
    )
    await write_audit("delete", f"Deleted process: {process.code}", process.code, actor_id)


async def update_process_status(process_id: str, status: str, actor_id: str):
    process = await db.process.find_unique(where={"id": process_id})
    if not process:
        raise not_found("Process")

    updated = await db.process.update(
        where={"id": process_id},
        data={"status": status},
        include=_PROCESS_INCLUDE,
    )
    audit_type = "archive" if status == "archived" else "upload"
    await write_audit(
        audit_type,
        f"Process {status}: {process.code}",
        process.code,
        actor_id,
    )
    return updated


async def import_processes(
    line_id: str,
    station_id: str,
    process_ids: list[str],
    car_model_id: str,
    mode: str,  # "copy" | "reference"
    actor_id: str,
) -> list:
    """
    Import processes from source process IDs into the target line/station/car model.

    mode='copy'      — duplicates the full version history. The new process is
                       completely independent; file objects in storage are reused
                       (same URLs, no re-upload needed).
    mode='reference' — creates the process shell and copies only the latest version,
                       tagging the commit message to indicate the source. Useful when
                       you just want a snapshot link without bringing over history.

    Skips any source process whose name already exists for the target station+carModel.
    Returns the list of newly created processes.
    """
    if not await db.assemblyline.find_unique(where={"id": line_id}):
        raise not_found("Assembly line")
    station = await db.station.find_first(where={"id": station_id, "lineId": line_id})
    if not station:
        raise not_found("Station")
    if not await db.carmodel.find_unique(where={"id": car_model_id}):
        raise not_found("Car model")

    # Load source processes. For copy we want all versions; for reference, just latest.
    version_include = (
        {"order_by": {"createdAt": "asc"}}          # oldest→newest for copy
        if mode == "copy"
        else {"order_by": {"createdAt": "desc"}, "take": 1}  # latest only for reference
    )
    source_processes = await db.process.find_many(
        where={"id": {"in": process_ids}, "status": {"not": "deleted"}},
        include={"versions": version_include},
    )
    if not source_processes:
        raise not_found("Source processes")

    # Separate active/archived processes from deleted ones at the target station+carModel
    all_existing = await db.process.find_many(
        where={"stationId": station_id, "carModelId": car_model_id},
    )
    active_names = {p.name.strip().lower() for p in all_existing if p.status != "deleted"}
    deleted_by_name = {p.name.strip().lower(): p for p in all_existing if p.status == "deleted"}

    created = []
    for src in source_processes:
        name_key = src.name.strip().lower()
        if name_key in active_names:
            continue

        has_missing_cp = not bool(src.versions)

        if name_key in deleted_by_name:
            # Restore the previously deleted process and replace its version history
            deleted_proc = deleted_by_name[name_key]
            await db.processversion.delete_many(where={"processId": deleted_proc.id})
            target_process = await db.process.update(
                where={"id": deleted_proc.id},
                data={"status": "active", "hasMissingCp": has_missing_cp},
                include=_PROCESS_INCLUDE,
            )
        else:
            target_process = await _create_process_with_code(
                line_id, station_id,
                lambda _src=src, _hmc=has_missing_cp: {
                    "name": _src.name,
                    "lineId": line_id,
                    "station": {"connect": {"id": station_id}},
                    "carModel": {"connect": {"id": car_model_id}},
                    "hasMissingCp": _hmc,
                },
            )

        for i, ver in enumerate(src.versions):
            version_str = f"v{i + 1}.0"

            if mode == "reference":
                commit_msg = f"Linked from {src.code}: {ver.commitMessage}"
                # No meaningful diff — this is a fresh link, not a delta
                diff_value = Json(json.dumps([]))
            else:
                commit_msg = ver.commitMessage
                raw_diff = ver.diff
                # raw_diff may already be a JSON string from the DB; avoid double-encoding
                if raw_diff is None:
                    diff_value = Json(json.dumps([]))
                elif isinstance(raw_diff, str):
                    diff_value = Json(raw_diff)
                else:
                    diff_value = Json(json.dumps(raw_diff))

            # ver.extractedData may already be a JSON string from the DB; avoid double-encoding
            if ver.extractedData is None:
                extracted_value = None
            elif isinstance(ver.extractedData, str):
                extracted_value = Json(ver.extractedData)
            else:
                extracted_value = Json(json.dumps(ver.extractedData))

            await db.processversion.create(
                data={
                    "process": {"connect": {"id": target_process.id}},
                    "version": version_str,
                    "fileUrl": ver.fileUrl,
                    "fileName": ver.fileName,
                    "fileSize": ver.fileSize,
                    "commitMessage": commit_msg,
                    "changes": ver.changes,
                    "uploader": {"connect": {"id": actor_id}},
                    "diff": diff_value,
                    **({"extractedData": extracted_value} if extracted_value is not None else {}),
                }
            )

        # Refresh to pick up the created versions
        target_process = await db.process.find_unique(
            where={"id": target_process.id},
            include=_PROCESS_INCLUDE,
        )
        created.append(target_process)
        active_names.add(name_key)

    await write_audit(
        "upload",
        f"Imported {len(created)} process(es) ({mode}) into station {station.name}",
        f"{len(created)} processes",
        actor_id,
    )
    return created
