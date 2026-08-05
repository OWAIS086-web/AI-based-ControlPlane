"""Assembly line service."""
import uuid

from app.core.exceptions import not_found, unprocessable
from app.core.utils import ev
from app.prisma_client import db
from app.utils.audit import write_audit

_INCLUDE = {"manager": True, "stations": True}


async def list_lines() -> list:
    return await db.assemblyline.find_many(include=_INCLUDE, order={"order": "asc"})


async def get_line(line_id: str):
    line = await db.assemblyline.find_unique(where={"id": line_id}, include=_INCLUDE)
    if not line:
        raise not_found("Assembly line")
    return line


async def create_line(name: str, icon: str, color: str, line_type_id: str | None, actor_id: str):
    count = await db.assemblyline.count()
    line = await db.assemblyline.create(
        data={
            "id": str(uuid.uuid4()),
            "name": name,
            "icon": icon,
            "color": color,
            "lineTypeId": line_type_id,
            "order": count,
        },
        include=_INCLUDE,
    )
    await write_audit("station", f"Created line '{name}'", name, actor_id)
    return line


async def update_line(line_id: str, updates: dict, actor_id: str):
    line = await db.assemblyline.find_unique(where={"id": line_id})
    if not line:
        raise not_found("Assembly line")
    updated = await db.assemblyline.update(
        where={"id": line_id}, data=updates, include=_INCLUDE
    )
    await write_audit("station", f"Updated line '{updated.name}'", updated.name, actor_id)
    return updated


async def delete_line(line_id: str, actor_id: str) -> None:
    line = await db.assemblyline.find_unique(where={"id": line_id}, include={"stations": True})
    if not line:
        raise not_found("Assembly line")
    if line.stations:
        raise unprocessable("Cannot delete a line that has stations. Remove all stations first.")
    await db.assemblyline.delete(where={"id": line_id})
    await write_audit("delete", f"Deleted line '{line.name}'", line.name, actor_id)


async def reorder_lines(ids: list[str]) -> list:
    for idx, line_id in enumerate(ids):
        await db.assemblyline.update(where={"id": line_id}, data={"order": idx})
    return await list_lines()


async def assign_manager(line_id: str, manager_id: str | None, actor_id: str):
    line = await db.assemblyline.find_unique(where={"id": line_id})
    if not line:
        raise not_found("Assembly line")

    if manager_id is not None:
        manager = await db.user.find_unique(where={"id": manager_id})
        if not manager:
            raise not_found("User")
        if ev(manager.role) != "line_manager":
            raise unprocessable("Assigned user must have the line_manager role.")

    updated = await db.assemblyline.update(
        where={"id": line_id},
        data={"managerId": manager_id},
        include=_INCLUDE,
    )
    label = updated.manager.name if updated.manager else "None"
    await write_audit(
        "user", f"Assigned manager '{label}' to line '{updated.name}'", updated.name, actor_id
    )
    return updated
