"""Assembly lines controller."""
from app.core.utils import ev
from app.schemas.assembly_line import AssemblyLineOut
from app.schemas.user import UserOut
from app.services import line_service


def _out(line) -> AssemblyLineOut:
    mgr = None
    if line.manager:
        m = line.manager
        mgr = UserOut(
            id=m.id, name=m.name, email=m.email, role=ev(m.role),
            status=ev(m.status), avatar=m.avatar, createdAt=m.createdAt, updatedAt=m.updatedAt,
        )
    return AssemblyLineOut(
        id=line.id, name=line.name, icon=line.icon, color=line.color,
        stationCount=len(line.stations or []),
        managerId=line.managerId,
        manager=mgr,
        lineTypeId=line.lineTypeId,
        order=line.order,
    )


async def list_lines() -> list[AssemblyLineOut]:
    lines = await line_service.list_lines()
    return [_out(l) for l in lines]


async def get_line(line_id: str) -> AssemblyLineOut:
    return _out(await line_service.get_line(line_id))


async def create_line(body, actor_id: str) -> AssemblyLineOut:
    return _out(await line_service.create_line(
        body.name, body.icon, body.color, body.lineTypeId, actor_id
    ))


async def update_line(line_id: str, body, actor_id: str) -> AssemblyLineOut:
    updates = body.model_dump(exclude_unset=True)
    return _out(await line_service.update_line(line_id, updates, actor_id))


async def delete_line(line_id: str, actor_id: str) -> None:
    await line_service.delete_line(line_id, actor_id)


async def reorder_lines(ids: list[str]) -> list[AssemblyLineOut]:
    lines = await line_service.reorder_lines(ids)
    return [_out(l) for l in lines]


async def assign_manager(line_id: str, manager_id: str, actor_id: str) -> AssemblyLineOut:
    return _out(await line_service.assign_manager(line_id, manager_id, actor_id))
