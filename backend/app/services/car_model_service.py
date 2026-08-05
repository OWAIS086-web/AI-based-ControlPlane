"""Car model service."""
from app.core.exceptions import conflict, not_found, unprocessable
from app.prisma_client import db
from app.utils.audit import write_audit

VALID_STATUSES = {"active", "archived"}


async def list_car_models(status: str | None, page: int, limit: int) -> dict:
    where: dict = {}
    if status:
        where["status"] = status
    total = await db.carmodel.count(where=where)
    models = await db.carmodel.find_many(
        where=where, skip=(page - 1) * limit, take=limit, order={"createdAt": "desc"}
    )
    return {"models": models, "total": total}


async def create_car_model(name: str, code: str, color: str, actor_id: str):
    if await db.carmodel.find_unique(where={"code": code}):
        raise conflict(f"A car model with code '{code}' already exists.")

    model = await db.carmodel.create(data={"name": name, "code": code, "color": color})
    await write_audit("model", f"Created car model: {model.code}", model.code, actor_id)
    return model


async def update_car_model(model_id: str, name: str | None, code: str | None, color: str | None, actor_id: str):
    model = await db.carmodel.find_unique(where={"id": model_id})
    if not model:
        raise not_found("Car model")

    if code is not None and code != model.code:
        existing = await db.carmodel.find_unique(where={"code": code})
        if existing:
            raise conflict(f"A car model with code '{code}' already exists.")

    data: dict = {}
    if name is not None:
        data["name"] = name
    if code is not None:
        data["code"] = code
    if color is not None:
        data["color"] = color

    updated = await db.carmodel.update(where={"id": model_id}, data=data)
    await write_audit("model", f"Updated car model: {updated.code}", updated.code, actor_id)
    return updated


async def update_car_model_status(model_id: str, status: str, actor_id: str):
    if status not in VALID_STATUSES:
        raise unprocessable(f"status must be one of {sorted(VALID_STATUSES)}")

    model = await db.carmodel.find_unique(where={"id": model_id})
    if not model:
        raise not_found("Car model")

    if status == "archived":
        active_procs = await db.process.count(
            where={"carModelId": model_id, "status": "active"}
        )
        if active_procs:
            raise conflict("Cannot archive: car model has active processes.")

    updated = await db.carmodel.update(where={"id": model_id}, data={"status": status})
    await write_audit(
        "model", f"Car model {status}: {updated.code}", updated.code, actor_id,
        {"modelId": model_id}
    )
    return updated
