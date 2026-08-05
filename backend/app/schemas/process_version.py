from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.user import UserOut


class DiffRow(BaseModel):
    row: str
    field: str
    oldValue: str
    newValue: str


class ProcessVersionOut(BaseModel):
    id: str
    processId: str
    version: str
    fileUrl: str
    fileName: str | None = None
    fileSize: int
    commitMessage: str
    changes: int
    uploadedBy: str
    uploader: UserOut | None = None
    diff: Any = None
    extractedData: dict | None = None
    createdAt: datetime
    deletedAt: datetime | None = None

    model_config = {"from_attributes": True}


class VersionCompareOut(BaseModel):
    v1: ProcessVersionOut
    v2: ProcessVersionOut
    diff: Any
    summary: dict
