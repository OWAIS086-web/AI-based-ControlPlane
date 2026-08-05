from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.process_version import ProcessVersionOut


class ProcessOut(BaseModel):
    id: str
    name: str
    code: str
    extractedCode: str | None = None
    lineId: str
    stationId: str
    carModelId: str
    status: str
    hasMissingCp: bool
    aiStatus: str = "idle"
    versionCount: int
    latestVersion: ProcessVersionOut | None = None
    workerId: str | None = None
    workerName: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class ExcelUploadOut(BaseModel):
    """Response returned by the smart Excel upload endpoint.

    status values:
      "created"  — no matching process found; a new one was created and first version uploaded
      "matched"  — existing process found by extractedCode; a new version was added
      "rejected" — upload rejected (e.g. code mismatch or unreadable file)
    """

    status: str
    message: str
    extractedCode: str
    process: ProcessOut | None = None
    version: ProcessVersionOut | None = None


class ProcessCreate(BaseModel):
    name: str
    carModelId: str

class ProcessBulkCreate(BaseModel):
    """Used by the bulk-import endpoint. `names` are the process names to create."""
    names:      list[str] = Field(..., min_length=1)
    carModelId: str

class ProcessImport(BaseModel):
    """Import processes from source process IDs into this station.

    mode='copy'      – duplicates the full version history (independent copy).
    mode='reference' – snapshots only the latest version, commit message tags the source.
    Names that already exist for the target station+carModel are skipped.
    """
    processIds: list[str] = Field(..., min_length=1)
    carModelId: str
    mode: str = Field("copy", pattern="^(copy|reference)$")


class ProcessStatusUpdate(BaseModel):
    status: str  # active | archived


class ProcessBulkStatusUpdate(BaseModel):
    ids: list[str] = Field(..., min_length=1)
    status: str  # active | archived


class ProcessBulkDelete(BaseModel):
    ids: list[str] = Field(..., min_length=1)
