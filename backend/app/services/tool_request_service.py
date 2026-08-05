"""Tool request (faulty report) service."""
from app.core.exceptions import bad_request, not_found
from app.prisma_client import db
from app.utils.audit import write_audit

_INCLUDE = {
    "tool": True,
    "type": True,
    "worker": True,
    "replacementTool": True,
}


async def list_requests(
    status: str | None,
    page: int,
    limit: int,
    reported_by_user_id: str | None = None,
) -> dict:
    where: dict = {}
    if status:
        where["status"] = status
    if reported_by_user_id:
        where["reportedByUserId"] = reported_by_user_id
    total = await db.toolrequest.count(where=where)
    requests = await db.toolrequest.find_many(
        where=where,
        include=_INCLUDE,
        order={"createdAt": "desc"},
        skip=(page - 1) * limit,
        take=limit,
    )
    return {"requests": requests, "total": total}


async def get_request(request_id: str):
    r = await db.toolrequest.find_unique(where={"id": request_id}, include=_INCLUDE)
    if not r:
        raise not_found("Tool request")
    return r


async def create_request(
    reported_tool_id: str,
    type_id: str,
    worker_id: str | None,
    reporter_name: str,
    notes: str | None,
    reported_by_user_id: str | None = None,
):
    # Validate type exists
    tt = await db.tooltype.find_unique(where={"id": type_id})
    if not tt:
        raise not_found("Tool type")

    worker = None
    if worker_id:
        worker = await db.worker.find_unique(where={"id": worker_id})
        if not worker:
            raise not_found("Worker")

    # Try to auto-link to an existing Tool record
    existing_tool = await db.tool.find_unique(where={"toolId": reported_tool_id})
    tool_db_id = existing_tool.id if existing_tool else None

    req = await db.toolrequest.create(
        data={
            "reportedToolId": reported_tool_id,
            "toolDbId": tool_db_id,
            "typeId": type_id,
            "workerId": worker_id,
            "reporterName": reporter_name,
            "reportedByUserId": reported_by_user_id,
            "notes": notes,
        },
        include=_INCLUDE,
    )

    if reported_by_user_id:
        await write_audit(
            type="tool_request",
            action="reported",
            target=reported_tool_id,
            performed_by=reported_by_user_id,
            metadata={
                "requestId": req.id,
                "typeName": tt.name,
                "workerId": worker_id,
                "workerName": worker.name if worker else None,
                "linkedToSystem": tool_db_id is not None,
            },
        )
    return req


async def mark_faulty(request_id: str, note: str | None, performed_by: str):
    """Process manager action: mark the reported tool as faulty.

    If the tool was auto-linked, mark it faulty via tool_service.
    If not found in DB, register it first (status=faulty), then link.
    Updates request status to in_review.
    """
    r = await db.toolrequest.find_unique(where={"id": request_id}, include=_INCLUDE)
    if not r:
        raise not_found("Tool request")

    r_status = r.status.value if hasattr(r.status, "value") else str(r.status)
    if r_status == "resolved":
        raise bad_request("Request is already resolved")

    if r.toolDbId:
        # Tool exists — mark it faulty
        tool = await db.tool.find_unique(where={"id": r.toolDbId})
        if tool:
            t_status = tool.status.value if hasattr(tool.status, "value") else str(tool.status)
            if t_status not in ("faulty",):
                update_data: dict = {"status": "faulty", "workerId": None, "processId": None}
                await db.tool.update(where={"id": r.toolDbId}, data=update_data)
                await db.toolevent.create(data={
                    "toolDbId": r.toolDbId,
                    "action": "marked_faulty",
                    "note": note or "Marked faulty via tool request",
                })
    else:
        # Tool not in DB — register it as faulty
        new_tool = await db.tool.create(
            data={
                "toolId": r.reportedToolId,
                "typeId": r.typeId,
                "status": "faulty",
                "notes": f"Registered via fault report by {r.reporterName}",
            },
        )
        await db.toolevent.create(data={
            "toolDbId": new_tool.id,
            "action": "created",
            "note": f"Registered via fault report. Original notes: {r.notes or '—'}",
        })
        await db.toolevent.create(data={
            "toolDbId": new_tool.id,
            "action": "marked_faulty",
            "note": note or "Registered as faulty via tool request",
        })
        # Link the new tool to the request
        await db.toolrequest.update(
            where={"id": request_id},
            data={"toolDbId": new_tool.id},
        )

    updated = await db.toolrequest.update(
        where={"id": request_id},
        data={"status": "in_review"},
        include=_INCLUDE,
    )
    await write_audit(
        type="tool_request",
        action="marked_faulty",
        target=r.reportedToolId,
        performed_by=performed_by,
        metadata={"requestId": request_id, "note": note},
    )
    return updated


async def resolve_request(
    request_id: str,
    replacement_tool_id: str | None,
    note: str | None,
    performed_by: str,
):
    """Process manager action: resolve a request, optionally assigning a replacement tool."""
    r = await db.toolrequest.find_unique(where={"id": request_id}, include=_INCLUDE)
    if not r:
        raise not_found("Tool request")

    r_status = r.status.value if hasattr(r.status, "value") else str(r.status)
    if r_status == "resolved":
        raise bad_request("Request is already resolved")

    import datetime

    replacement_assigned = False
    if replacement_tool_id:
        replacement = await db.tool.find_unique(where={"id": replacement_tool_id})
        if not replacement:
            raise not_found("Replacement tool")
        t_status = replacement.status.value if hasattr(replacement.status, "value") else str(replacement.status)
        if t_status not in ("available",):
            raise bad_request(f"Replacement tool status is '{t_status}' — must be available")

        # Assign replacement to the worker
        if r.workerId:
            existing_count = await db.tool.count(where={
                "workerId": r.workerId,
                "typeId": replacement.typeId,
                "status": "assigned",
                "id": {"not": replacement_tool_id},
            })
            tool_type = await db.tooltype.find_unique(where={"id": replacement.typeId})
            if tool_type and existing_count >= tool_type.maxPerWorker:
                raise bad_request(
                    f"Worker already has {existing_count}/{tool_type.maxPerWorker} "
                    f"'{tool_type.name}' tool(s) — limit reached"
                )
            await db.tool.update(
                where={"id": replacement_tool_id},
                data={"workerId": r.workerId, "status": "assigned"},
            )
            worker = await db.worker.find_unique(where={"id": r.workerId})
            await db.toolevent.create(data={
                "toolDbId": replacement_tool_id,
                "action": "assigned_worker",
                "workerId": r.workerId,
                "workerName": worker.name if worker else None,
                "note": f"Assigned as replacement via tool request #{request_id[:8]}",
            })
        replacement_assigned = True

    resolve_data: dict = {
        "status": "resolved",
        "resolvedNote": note,
        "resolvedAt": datetime.datetime.now(datetime.UTC),
    }
    if replacement_assigned and replacement_tool_id:
        resolve_data["replacementToolId"] = replacement_tool_id

    await db.toolrequest.update(where={"id": request_id}, data=resolve_data)
    await write_audit(
        type="tool_request",
        action="resolved",
        target=r.reportedToolId,
        performed_by=performed_by,
        metadata={
            "requestId": request_id,
            "replacementToolId": replacement_tool_id,
            "note": note,
        },
    )
    return await db.toolrequest.find_unique(where={"id": request_id}, include=_INCLUDE)
