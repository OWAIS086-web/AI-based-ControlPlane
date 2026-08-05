"""Car models controller."""
from app.core.utils import ev
from app.schemas.car_model import CarModelOut
from app.schemas.common import make_paginated
from app.services import car_model_service


def _out(m) -> CarModelOut:
    return CarModelOut(
        id=m.id, name=m.name, code=m.code, color=m.color,
        status=ev(m.status), createdAt=m.createdAt, updatedAt=m.updatedAt,
    )


async def list_car_models(status, page, limit) -> dict:
    result = await car_model_service.list_car_models(status, page, limit)
    return make_paginated([_out(m) for m in result["models"]], result["total"], page, limit)


async def create_car_model(name, code, color, actor_id) -> CarModelOut:
    return _out(await car_model_service.create_car_model(name, code, color, actor_id))


async def update_car_model(model_id, name, code, color, actor_id) -> CarModelOut:
    return _out(await car_model_service.update_car_model(model_id, name, code, color, actor_id))


async def update_car_model_status(model_id, status, actor_id) -> CarModelOut:
    return _out(await car_model_service.update_car_model_status(model_id, status, actor_id))
