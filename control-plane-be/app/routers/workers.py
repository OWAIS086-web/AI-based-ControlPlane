"""Workers routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import worker_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.worker import AssignWorkerRequest, WorkerCreate, WorkerOut, WorkerUpdate

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("", response_model=dict)
async def list_workers(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _=Depends(get_current_user),
):
    return await worker_controller.list_workers(search, page, limit)


@router.get("/all", response_model=list[WorkerOut])
async def list_all_workers(_=Depends(get_current_user)):
    """Return all workers unpaginated — used for assignment dropdowns."""
    return await worker_controller.list_all_workers()


@router.post("", response_model=WorkerOut, status_code=201)
async def create_worker(body: WorkerCreate, current_user=Depends(require_process_manager)):
    return await worker_controller.create_worker(body.name, body.workerId, current_user.id)


@router.get("/{worker_id}", response_model=WorkerOut)
async def get_worker(worker_id: str, _=Depends(get_current_user)):
    return await worker_controller.get_worker(worker_id)


@router.patch("/{worker_id}", response_model=WorkerOut)
async def update_worker(
    worker_id: str, body: WorkerUpdate, current_user=Depends(require_process_manager)
):
    return await worker_controller.update_worker(worker_id, body.name, body.workerId, current_user.id)


@router.delete("/{worker_id}", status_code=204)
async def delete_worker(worker_id: str, current_user=Depends(require_process_manager)):
    await worker_controller.delete_worker(worker_id, current_user.id)


@router.post("/assign", status_code=204)
async def assign_worker(body: AssignWorkerRequest, current_user=Depends(require_process_manager)):
    """Assign (or unassign) a worker to one or more processes.

    Pass workerId=null to remove all assignments for the given processIds.
    """
    await worker_controller.assign_workers(body.processIds, body.workerId, current_user.id)
