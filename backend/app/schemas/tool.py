from datetime import datetime
from pydantic import BaseModel, Field


class ToolTypeOut(BaseModel):
    id: str
    name: str
    maxPerWorker: int
    toolCount: int = 0
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class ToolTypeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    maxPerWorker: int = Field(1, ge=1)


class ToolTypeUpdate(BaseModel):
    name: str | None = None
    maxPerWorker: int | None = Field(None, ge=1)


class ToolEventOut(BaseModel):
    id: str
    action: str
    workerId: str | None
    workerName: str | None
    processId: str | None
    processName: str | None
    note: str | None
    createdAt: datetime

    model_config = {"from_attributes": True}


class ToolOut(BaseModel):
    id: str
    toolId: str
    typeId: str
    typeName: str
    status: str
    workerId: str | None
    workerName: str | None
    processId: str | None
    processName: str | None
    notes: str | None
    events: list[ToolEventOut] = []
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class ToolCreate(BaseModel):
    toolId: str = Field(..., min_length=1)
    typeId: str
    notes: str | None = None


class ToolUpdate(BaseModel):
    toolId: str | None = None
    notes: str | None = None


class ToolAssignRequest(BaseModel):
    workerId: str | None = None
    processId: str | None = None


class ToolStatusRequest(BaseModel):
    status: str  # available, faulty, in_repair
    note: str | None = None


class ToolListResponse(BaseModel):
    data: list[ToolOut]
    meta: dict
