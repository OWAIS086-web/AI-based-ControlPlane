"""Line type controller."""
from app.schemas.line_type import LineTypeOut
from app.services import line_type_service


def _out(lt) -> LineTypeOut:
    return LineTypeOut(id=lt.id, name=lt.name, icon=lt.icon, color=lt.color, order=lt.order)


async def list_line_types() -> list[LineTypeOut]:
    types = await line_type_service.list_line_types()
    return [_out(t) for t in types]


async def create_line_type(name: str, icon: str, color: str) -> LineTypeOut:
    return _out(await line_type_service.create_line_type(name, icon, color))


async def update_line_type(type_id: str, body) -> LineTypeOut:
    updates = body.model_dump(exclude_unset=True)
    return _out(await line_type_service.update_line_type(type_id, updates))


async def delete_line_type(type_id: str) -> None:
    await line_type_service.delete_line_type(type_id)


async def reorder_line_types(ids: list[str]) -> list[LineTypeOut]:
    types = await line_type_service.reorder_line_types(ids)
    return [_out(t) for t in types]
