"""Tool controller — serialisation and delegation."""
from app.schemas.common import make_paginated
from app.schemas.tool import ToolEventOut, ToolOut, ToolTypeOut
from app.services import tool_service


def _event_out(e) -> ToolEventOut:
    return ToolEventOut(
        id=e.id,
        action=e.action,
        workerId=e.workerId,
        workerName=e.workerName,
        processId=e.processId,
        processName=e.processName,
        note=e.note,
        createdAt=e.createdAt,
    )


def _tool_out(t) -> ToolOut:
    return ToolOut(
        id=t.id,
        toolId=t.toolId,
        typeId=t.typeId,
        typeName=t.type.name if t.type else "",
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        workerId=t.workerId,
        workerName=t.worker.name if t.worker else None,
        processId=t.processId,
        processName=t.process.name if t.process else None,
        notes=t.notes,
        events=[_event_out(e) for e in (getattr(t, "events", None) or [])],
        createdAt=t.createdAt,
        updatedAt=t.updatedAt,
    )


def _type_out(tt) -> ToolTypeOut:
    return ToolTypeOut(
        id=tt.id,
        name=tt.name,
        maxPerWorker=tt.maxPerWorker,
        toolCount=len(tt.tools) if tt.tools else 0,
        createdAt=tt.createdAt,
        updatedAt=tt.updatedAt,
    )


async def list_tool_types() -> list[ToolTypeOut]:
    types = await tool_service.list_tool_types()
    return [_type_out(tt) for tt in types]


async def create_tool_type(name: str, max_per_worker: int, performed_by: str) -> ToolTypeOut:
    return _type_out(await tool_service.create_tool_type(name, max_per_worker, performed_by))


async def update_tool_type(type_id: str, name, max_per_worker, performed_by: str) -> ToolTypeOut:
    return _type_out(await tool_service.update_tool_type(type_id, name, max_per_worker, performed_by))


async def delete_tool_type(type_id: str, performed_by: str) -> None:
    await tool_service.delete_tool_type(type_id, performed_by)


async def list_tools(search, type_id, status, page, limit) -> dict:
    result = await tool_service.list_tools(search, type_id, status, page, limit)
    return make_paginated([_tool_out(t) for t in result["tools"]], result["total"], page, limit)


async def list_all_tools(type_id=None, status=None) -> list[ToolOut]:
    tools = await tool_service.list_all_tools(type_id, status)
    return [_tool_out(t) for t in tools]


async def get_tool(tool_db_id: str) -> ToolOut:
    return _tool_out(await tool_service.get_tool(tool_db_id))


async def create_tool(tool_id: str, type_id: str, notes, performed_by: str) -> ToolOut:
    return _tool_out(await tool_service.create_tool(tool_id, type_id, notes, performed_by))


async def update_tool(tool_db_id: str, tool_id, notes, performed_by: str) -> ToolOut:
    return _tool_out(await tool_service.update_tool(tool_db_id, tool_id, notes, performed_by))


async def delete_tool(tool_db_id: str, performed_by: str) -> None:
    await tool_service.delete_tool(tool_db_id, performed_by)


async def assign_tool(tool_db_id: str, worker_id, process_id, performed_by: str) -> ToolOut:
    return _tool_out(await tool_service.assign_tool(tool_db_id, worker_id, process_id, performed_by))


async def set_tool_status(tool_db_id: str, status: str, note, performed_by: str) -> ToolOut:
    return _tool_out(await tool_service.set_tool_status(tool_db_id, status, note, performed_by))
