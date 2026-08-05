"""Worker service — CRUD and assignment operations."""
from app.core.exceptions import conflict, not_found
from app.prisma_client import db
from app.utils.audit import write_audit

_PROCESS_INCLUDE = {
    "carModel": True,
}

_WORKER_INCLUDE = {
    "assignments": {
        "include": {"process": {"include": _PROCESS_INCLUDE}},
    }
}


async def list_workers(
    search: str | None,
    page: int,
    limit: int,
) -> dict:
    where: dict = {}
    if search:
        where["OR"] = [
            {"name": {"contains": search, "mode": "insensitive"}},
            {"workerId": {"contains": search, "mode": "insensitive"}},
        ]

    total = await db.worker.count(where=where)
    workers = await db.worker.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include=_WORKER_INCLUDE,
        order={"name": "asc"},
    )
    return {"workers": workers, "total": total}


async def list_all_workers() -> list:
    """Return all workers without pagination — used for dropdowns."""
    return await db.worker.find_many(
        include=_WORKER_INCLUDE,
        order={"name": "asc"},
    )


async def get_worker(worker_id: str):
    worker = await db.worker.find_unique(
        where={"id": worker_id},
        include=_WORKER_INCLUDE,
    )
    if not worker:
        raise not_found("Worker")
    return worker


async def create_worker(name: str, worker_id: str, performed_by: str):
    existing = await db.worker.find_unique(where={"workerId": worker_id})
    if existing:
        raise conflict("Worker ID already exists")
    worker = await db.worker.create(
        data={"name": name, "workerId": worker_id},
        include=_WORKER_INCLUDE,
    )
    await write_audit(
        type="worker",
        action="created",
        target=name,
        performed_by=performed_by,
        metadata={"workerId": worker_id, "workerDbId": worker.id},
    )
    return worker


async def update_worker(worker_id: str, name: str | None, manual_id: str | None, performed_by: str):
    worker = await db.worker.find_unique(where={"id": worker_id})
    if not worker:
        raise not_found("Worker")

    if manual_id and manual_id != worker.workerId:
        existing = await db.worker.find_unique(where={"workerId": manual_id})
        if existing:
            raise conflict("Worker ID already in use")

    data: dict = {}
    if name is not None:
        data["name"] = name
    if manual_id is not None:
        data["workerId"] = manual_id

    updated = await db.worker.update(
        where={"id": worker_id},
        data=data,
        include=_WORKER_INCLUDE,
    )
    await write_audit(
        type="worker",
        action="updated",
        target=updated.name,
        performed_by=performed_by,
        metadata={"workerDbId": worker_id, "changes": data},
    )
    return updated


async def delete_worker(worker_id: str, performed_by: str) -> None:
    worker = await db.worker.find_unique(where={"id": worker_id})
    if not worker:
        raise not_found("Worker")
    worker_label = worker.name
    worker_ext_id = worker.workerId
    # Assignments cascade-delete via FK
    await db.worker.delete(where={"id": worker_id})
    await write_audit(
        type="worker",
        action="deleted",
        target=worker_label,
        performed_by=performed_by,
        metadata={"workerDbId": worker_id, "workerId": worker_ext_id},
    )


async def assign_workers(process_ids: list[str], worker_id: str | None, performed_by: str) -> None:
    """Assign or unassign a worker across a list of processes."""
    worker_name = None
    worker_ext_id = None
    if worker_id:
        worker = await db.worker.find_unique(where={"id": worker_id})
        if not worker:
            raise not_found("Worker")
        worker_name = worker.name
        worker_ext_id = worker.workerId

    for pid in process_ids:
        process = await db.process.find_unique(where={"id": pid})
        if not process:
            raise not_found(f"Process {pid}")

        existing = await db.workerassignment.find_unique(where={"processId": pid})

        if worker_id is None:
            if existing:
                await db.workerassignment.delete(where={"processId": pid})
        else:
            if existing:
                await db.workerassignment.update(
                    where={"processId": pid},
                    data={"workerId": worker_id},
                )
            else:
                await db.workerassignment.create(
                    data={"workerId": worker_id, "processId": pid},
                )

    audit_action = "unassigned_processes" if worker_id is None else "assigned_processes"
    await write_audit(
        type="worker",
        action=audit_action,
        target=worker_name or "unassigned",
        performed_by=performed_by,
        metadata={
            "workerDbId": worker_id,
            "workerId": worker_ext_id,
            "processIds": process_ids,
            "processCount": len(process_ids),
        },
    )
