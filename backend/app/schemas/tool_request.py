"""Pydantic schemas for tool fault reports / requests."""
from __future__ import annotations
from pydantic import BaseModel


class ToolRequestCreate(BaseModel):
    reportedToolId: str
    typeId: str
    workerId: str | None = None
    notes: str | None = None


class ToolRequestMarkFaulty(BaseModel):
    note: str | None = None


class ToolRequestResolve(BaseModel):
    replacementToolId: str | None = None
    note: str | None = None


class ToolRequestOut(BaseModel):
    id: str
    reportedToolId: str
    toolDbId: str | None
    faultyToolRef: str | None        # toolId string of the linked faulty tool
    typeId: str
    typeName: str
    workerId: str | None
    workerName: str | None
    workerExternalId: str | None
    reporterName: str
    notes: str | None
    status: str
    replacementToolId: str | None
    replacementToolRef: str | None   # toolId string of the replacement
    resolvedNote: str | None
    resolvedAt: str | None
    createdAt: str
    updatedAt: str


class ToolRequestListResponse(BaseModel):
    requests: list[ToolRequestOut]
    total: int
