"""Tool service — CRUD, assignment, status management."""
from app.core.exceptions import bad_request, conflict, not_found
from app.prisma_client import db
from app.utils.audit import write_audit

_TOOL_INCLUDE = {
    "type": True,
    "worker": True,
    "process": True,
    "events": {"order_by": {"createdAt": "desc"}, "take": 50},
}

_TOOL_INCLUDE_NO_EVENTS = {
    "type": True,
    "worker": True,
    "process": True,
}


async def list_tool_types() -> list:
    return await db.tooltype.find_many(
        include={"tools": True},
        order={"name": "asc"},
    )


async def create_tool_type(name: str, max_per_worker: int, performed_by: str):
    existing = await db.tooltype.find_unique(where={"name": name})
    if existing:
        raise conflict("Tool type name already exists")
    tt = await db.tooltype.create(
        data={"name": name, "maxPerWorker": max_per_worker},
        include={"tools": True},
    )
    await write_audit(
        type="tool",
        action="type_created",
        target=name,
        performed_by=performed_by,
        metadata={"typeId": tt.id, "maxPerWorker": max_per_worker},
    )
    return tt


async def update_tool_type(type_id: str, name: str | None, max_per_worker: int | None, performed_by: str):
    tt = await db.tooltype.find_unique(where={"id": type_id})
    if not tt:
        raise not_found("Tool type")
    data: dict = {}
    if name is not None:
        data["name"] = name
    if max_per_worker is not None:
        data["maxPerWorker"] = max_per_worker
    updated = await db.tooltype.update(
        where={"id": type_id},
        data=data,
        include={"tools": True},
    )
    await write_audit(
        type="tool",
        action="type_updated",
        target=updated.name,
        performed_by=performed_by,
        metadata={"typeId": type_id, "changes": data},
    )
    return updated


async def delete_tool_type(type_id: str, performed_by: str) -> None:
    tt = await db.tooltype.find_unique(where={"id": type_id}, include={"tools": True})
    if not tt:
        raise not_found("Tool type")
    if tt.tools:
        raise bad_request("Cannot delete a tool type that has registered tools")
    await db.tooltype.delete(where={"id": type_id})
    await write_audit(
        type="tool",
        action="type_deleted",
        target=tt.name,
        performed_by=performed_by,
        metadata={"typeId": type_id},
    )


async def list_tools(
    search: str | None,
    type_id: str | None,
    status: str | None,
    page: int,
    limit: int,
) -> dict:
    where: dict = {}
    if search:
        where["OR"] = [
            {"toolId": {"contains": search, "mode": "insensitive"}},
        ]
    if type_id:
        where["typeId"] = type_id
    if status:
        where["status"] = status

    total = await db.tool.count(where=where)
    tools = await db.tool.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include=_TOOL_INCLUDE_NO_EVENTS,
        order=[{"workerId": "asc"}, {"toolId": "asc"}],
    )
    return {"tools": tools, "total": total}


async def list_all_tools(type_id: str | None = None, status: str | None = None) -> list:
    where: dict = {}
    if type_id:
        where["typeId"] = type_id
    if status:
        where["status"] = status
    return await db.tool.find_many(
        where=where,
        include=_TOOL_INCLUDE_NO_EVENTS,
        order=[{"workerId": "asc"}, {"toolId": "asc"}],
    )


async def get_tool(tool_db_id: str):
    tool = await db.tool.find_unique(where={"id": tool_db_id}, include=_TOOL_INCLUDE)
    if not tool:
        raise not_found("Tool")
    return tool


async def create_tool(tool_id: str, type_id: str, notes: str | None, performed_by: str):
    existing = await db.tool.find_unique(where={"toolId": tool_id})
    if existing:
        raise conflict("Tool ID already exists")
    tt = await db.tooltype.find_unique(where={"id": type_id})
    if not tt:
        raise not_found("Tool type")
    tool = await db.tool.create(
        data={"toolId": tool_id, "typeId": type_id, "notes": notes},
        include=_TOOL_INCLUDE,
    )
    await db.toolevent.create(data={
        "toolDbId": tool.id,
        "action": "created",
        "note": f"Tool {tool_id} registered",
    })
    await write_audit(
        type="tool",
        action="registered",
        target=tool_id,
        performed_by=performed_by,
        metadata={"toolDbId": tool.id, "typeId": type_id, "typeName": tt.name},
    )
    return await db.tool.find_unique(where={"id": tool.id}, include=_TOOL_INCLUDE)


async def update_tool(tool_db_id: str, tool_id: str | None, notes: str | None, performed_by: str):
    tool = await db.tool.find_unique(where={"id": tool_db_id})
    if not tool:
        raise not_found("Tool")
    if tool_id and tool_id != tool.toolId:
        existing = await db.tool.find_unique(where={"toolId": tool_id})
        if existing:
            raise conflict("Tool ID already in use")
    data: dict = {}
    if tool_id is not None:
        data["toolId"] = tool_id
    if notes is not None:
        data["notes"] = notes
    updated = await db.tool.update(
        where={"id": tool_db_id},
        data=data,
        include=_TOOL_INCLUDE,
    )
    await write_audit(
        type="tool",
        action="updated",
        target=updated.toolId,
        performed_by=performed_by,
        metadata={"toolDbId": tool_db_id, "changes": data},
    )
    return updated


async def delete_tool(tool_db_id: str, performed_by: str) -> None:
    tool = await db.tool.find_unique(where={"id": tool_db_id})
    if not tool:
        raise not_found("Tool")
    tool_label = tool.toolId
    await db.tool.delete(where={"id": tool_db_id})
    await write_audit(
        type="tool",
        action="deleted",
        target=tool_label,
        performed_by=performed_by,
        metadata={"toolDbId": tool_db_id},
    )


async def assign_tool(tool_db_id: str, worker_id: str | None, process_id: str | None, performed_by: str):
    """Assign tool to a worker or control plan. Validates maxPerWorker limit."""
    tool = await db.tool.find_unique(where={"id": tool_db_id}, include={"type": True})
    if not tool:
        raise not_found("Tool")

    tool_status = tool.status.value if hasattr(tool.status, "value") else str(tool.status)
    if tool_status in ("faulty", "in_repair"):
        raise bad_request(f"Cannot assign a tool with status '{tool_status}'")

    target_worker_id = worker_id
    target_process_name = None

    if process_id:
        process = await db.process.find_unique(
            where={"id": process_id},
            include={"assignment": {"include": {"worker": True}}},
        )
        if not process:
            raise not_found("Process")
        if not process.assignment:
            raise bad_request("This control plan has no worker assigned — assign a worker first")
        target_worker_id = process.assignment.workerId
        target_process_name = process.name

    if target_worker_id:
        worker = await db.worker.find_unique(where={"id": target_worker_id})
        if not worker:
            raise not_found("Worker")

        current_count = await db.tool.count(where={
            "workerId": target_worker_id,
            "typeId": tool.typeId,
            "status": "assigned",
            "id": {"not": tool_db_id},
        })
        if current_count >= tool.type.maxPerWorker:
            raise bad_request(
                f"Worker already has {current_count}/{tool.type.maxPerWorker} "
                f"'{tool.type.name}' tool(s) — limit reached"
            )

    if target_worker_id:
        update_data = {
            "workerId": target_worker_id,
            "processId": process_id,
            "status": "assigned",
        }
        action = "assigned_process" if process_id else "assigned_worker"
        note = f"Assigned to process '{target_process_name}'" if process_id else "Assigned to worker"
    else:
        update_data = {"workerId": None, "processId": None, "status": "available"}
        action = "unassigned"
        note = "Unassigned"

    updated = await db.tool.update(
        where={"id": tool_db_id},
        data=update_data,
        include={"worker": True, "process": True},
    )

    worker_name = updated.worker.name if updated.worker else None
    await db.toolevent.create(data={
        "toolDbId": tool_db_id,
        "action": action,
        "workerId": updated.workerId,
        "workerName": worker_name,
        "processId": process_id,
        "processName": target_process_name,
        "note": note,
    })

    audit_action = "unassigned" if action == "unassigned" else "assigned"
    await write_audit(
        type="tool",
        action=audit_action,
        target=tool.toolId,
        performed_by=performed_by,
        metadata={
            "toolDbId": tool_db_id,
            "workerId": target_worker_id,
            "workerName": worker_name,
            "processId": process_id,
            "processName": target_process_name,
        },
    )

    return await db.tool.find_unique(where={"id": tool_db_id}, include=_TOOL_INCLUDE)


async def set_tool_status(tool_db_id: str, status: str, note: str | None, performed_by: str):
    """Change tool status (available / faulty / in_repair). Unassigns if needed."""
    tool = await db.tool.find_unique(where={"id": tool_db_id}, include={"worker": True})
    if not tool:
        raise not_found("Tool")

    allowed = {"available", "faulty", "in_repair"}
    if status not in allowed:
        raise bad_request(f"Invalid status. Must be one of: {', '.join(allowed)}")

    prev_status = tool.status.value if hasattr(tool.status, "value") else str(tool.status)
    update_data: dict = {"status": status}
    if status in ("faulty", "in_repair"):
        update_data["workerId"] = None
        update_data["processId"] = None

    await db.tool.update(where={"id": tool_db_id}, data=update_data)

    action_map = {
        "available": "marked_available",
        "faulty": "marked_faulty",
        "in_repair": "sent_for_repair",
    }
    await db.toolevent.create(data={
        "toolDbId": tool_db_id,
        "action": action_map[status],
        "note": note or action_map[status].replace("_", " ").title(),
    })
    await write_audit(
        type="tool",
        action="status_changed",
        target=tool.toolId,
        performed_by=performed_by,
        metadata={"toolDbId": tool_db_id, "from": prev_status, "to": status, "note": note},
    )

    return await db.tool.find_unique(where={"id": tool_db_id}, include=_TOOL_INCLUDE)
