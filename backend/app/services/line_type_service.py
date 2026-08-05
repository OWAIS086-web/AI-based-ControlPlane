"""Line type service."""
import uuid

from app.core.exceptions import not_found
from app.prisma_client import db


async def list_line_types() -> list:
    return await db.linetype.find_many(order={"order": "asc"})


async def get_line_type(type_id: str):
    lt = await db.linetype.find_unique(where={"id": type_id})
    if not lt:
        raise not_found("Line type")
    return lt


async def create_line_type(name: str, icon: str, color: str):
    count = await db.linetype.count()
    return await db.linetype.create(
        data={
            "id": str(uuid.uuid4()),
            "name": name,
            "icon": icon,
            "color": color,
            "order": count,
        }
    )


async def update_line_type(type_id: str, updates: dict):
    lt = await db.linetype.find_unique(where={"id": type_id})
    if not lt:
        raise not_found("Line type")
    return await db.linetype.update(where={"id": type_id}, data=updates)


async def delete_line_type(type_id: str) -> None:
    lt = await db.linetype.find_unique(where={"id": type_id})
    if not lt:
        raise not_found("Line type")
    # Unlink all lines before deleting
    await db.assemblyline.update_many(
        where={"lineTypeId": type_id},
        data={"lineTypeId": None},
    )
    await db.linetype.delete(where={"id": type_id})


async def reorder_line_types(ids: list[str]) -> list:
    for idx, type_id in enumerate(ids):
        await db.linetype.update(where={"id": type_id}, data={"order": idx})
    return await list_line_types()
