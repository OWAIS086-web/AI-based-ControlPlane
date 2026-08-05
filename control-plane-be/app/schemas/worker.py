from datetime import datetime
from pydantic import BaseModel, Field


class WorkerAssignmentOut(BaseModel):
    processId: str
    processName: str
    processCode: str
    processStatus: str
    carModelId: str
    carModelName: str
    lineId: str
    stationId: str

    model_config = {"from_attributes": True}


class WorkerOut(BaseModel):
    id: str
    name: str
    workerId: str
    assignedCount: int
    assignments: list[WorkerAssignmentOut] = []
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class WorkerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    workerId: str = Field(..., min_length=1)


class WorkerUpdate(BaseModel):
    name: str | None = None
    workerId: str | None = None


class AssignWorkerRequest(BaseModel):
    """Assign (or unassign) a worker to one or more processes.

    Pass workerId=None to remove the current assignment.
    processIds can contain one or multiple process IDs to assign in bulk.
    """
    workerId: str | None = None
    processIds: list[str] = Field(..., min_length=1)
