"""Workers controller — serialisation and delegation."""
from app.schemas.common import make_paginated
from app.schemas.worker import WorkerAssignmentOut, WorkerOut
from app.services import worker_service


def _assignment_out(a) -> WorkerAssignmentOut:
    p = a.process
    return WorkerAssignmentOut(
        processId=p.id,
        processName=p.name,
        processCode=p.code,
        processStatus=p.status,
        carModelId=p.carModelId,
        carModelName=p.carModel.name if p.carModel else "",
        lineId=p.lineId,
        stationId=p.stationId,
    )


def _out(w) -> WorkerOut:
    assignments = [_assignment_out(a) for a in (w.assignments or [])]
    return WorkerOut(
        id=w.id,
        name=w.name,
        workerId=w.workerId,
        assignedCount=len(assignments),
        assignments=assignments,
        createdAt=w.createdAt,
        updatedAt=w.updatedAt,
    )


async def list_workers(search, page, limit) -> dict:
    result = await worker_service.list_workers(search, page, limit)
    return make_paginated([_out(w) for w in result["workers"]], result["total"], page, limit)


async def list_all_workers() -> list[WorkerOut]:
    workers = await worker_service.list_all_workers()
    return [_out(w) for w in workers]


async def get_worker(worker_id: str) -> WorkerOut:
    return _out(await worker_service.get_worker(worker_id))


async def create_worker(name: str, worker_id: str, performed_by: str) -> WorkerOut:
    return _out(await worker_service.create_worker(name, worker_id, performed_by))


async def update_worker(worker_id: str, name, manual_id, performed_by: str) -> WorkerOut:
    return _out(await worker_service.update_worker(worker_id, name, manual_id, performed_by))


async def delete_worker(worker_id: str, performed_by: str) -> None:
    await worker_service.delete_worker(worker_id, performed_by)


async def assign_workers(process_ids: list[str], worker_id: str | None, performed_by: str) -> None:
    await worker_service.assign_workers(process_ids, worker_id, performed_by)
