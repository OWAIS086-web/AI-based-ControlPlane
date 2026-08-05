"""Tool request controller — serialisation helpers."""
from app.schemas.tool_request import ToolRequestOut
from app.services import tool_request_service


def _out(r) -> dict:
    def _str(v):
        return v.value if hasattr(v, "value") else str(v) if v is not None else None

    return ToolRequestOut(
        id=r.id,
        reportedToolId=r.reportedToolId,
        toolDbId=r.toolDbId,
        faultyToolRef=r.tool.toolId if r.tool else None,
        typeId=r.typeId,
        typeName=r.type.name if r.type else "",
        workerId=r.workerId,
        workerName=r.worker.name if r.worker else None,
        workerExternalId=r.worker.workerId if r.worker else None,
        reporterName=r.reporterName,
        notes=r.notes,
        status=_str(r.status),
        replacementToolId=r.replacementToolId,
        replacementToolRef=r.replacementTool.toolId if r.replacementTool else None,
        resolvedNote=r.resolvedNote,
        resolvedAt=r.resolvedAt.isoformat() if r.resolvedAt else None,
        createdAt=r.createdAt.isoformat(),
        updatedAt=r.updatedAt.isoformat(),
    ).model_dump()


async def list_requests(status, page, limit, reported_by_user_id=None):
    result = await tool_request_service.list_requests(
        status, page, limit, reported_by_user_id=reported_by_user_id
    )
    return {
        "requests": [_out(r) for r in result["requests"]],
        "total": result["total"],
    }


async def get_request(request_id: str):
    r = await tool_request_service.get_request(request_id)
    return _out(r)


async def create_request(reported_tool_id, type_id, worker_id, reporter_name, notes, reported_by_user_id=None):
    r = await tool_request_service.create_request(
        reported_tool_id, type_id, worker_id, reporter_name, notes,
        reported_by_user_id=reported_by_user_id,
    )
    return _out(r)


async def mark_faulty(request_id: str, note, performed_by: str):
    r = await tool_request_service.mark_faulty(request_id, note, performed_by)
    return _out(r)


async def resolve_request(request_id: str, replacement_tool_id, note, performed_by: str):
    r = await tool_request_service.resolve_request(request_id, replacement_tool_id, note, performed_by)
    return _out(r)
