"""Pydantic schemas for the maintenance module."""
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.common import EmailField


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailField
    password: str


class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    user: "MaintenanceUserOut"


class RefreshRequest(BaseModel):
    refreshToken: str


class RefreshResponse(BaseModel):
    accessToken: str
    expiresIn: int


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


# ── Users ─────────────────────────────────────────────────────────────────────

class MaintenanceUserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, u) -> "MaintenanceUserOut":
        return cls(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.value,
            status=u.status.value,
            createdAt=u.created_at,
            updatedAt=u.updated_at,
        )


class MaintenanceUserCreate(BaseModel):
    name: str
    email: EmailField
    password: str
    role: str = "technician"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("admin", "technician"):
            raise ValueError("role must be 'admin' or 'technician'")
        return v


class MaintenanceUserUpdate(BaseModel):
    name: str | None = None
    email: EmailField | None = None


class MaintenanceUserStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("active", "inactive"):
            raise ValueError("status must be 'active' or 'inactive'")
        return v


# ── Faults ────────────────────────────────────────────────────────────────────

class FaultRecordOut(BaseModel):
    id: str
    title: str
    description: str
    location: str | None
    severity: str
    status: str
    reportedBy: str
    reporterName: str
    assignedTo: str | None
    assigneeName: str | None
    resolvedAt: datetime | None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, f) -> "FaultRecordOut":
        return cls(
            id=f.id,
            title=f.title,
            description=f.description,
            location=f.location,
            severity=f.severity.value,
            status=f.status.value,
            reportedBy=f.reported_by,
            reporterName=f.reporter.name if f.reporter else "",
            assignedTo=f.assigned_to,
            assigneeName=f.assignee.name if f.assignee else None,
            resolvedAt=f.resolved_at,
            createdAt=f.created_at,
            updatedAt=f.updated_at,
        )


class FaultRecordCreate(BaseModel):
    title: str
    description: str
    location: str | None = None
    severity: str = "medium"

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in ("low", "medium", "high", "critical"):
            raise ValueError("severity must be low, medium, high, or critical")
        return v


class FaultRecordUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    severity: str | None = None
    status: str | None = None
    assigned_to: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in ("low", "medium", "high", "critical"):
            raise ValueError("severity must be low, medium, high, or critical")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "in_progress", "resolved"):
            raise ValueError("status must be open, in_progress, or resolved")
        return v


class FaultListResponse(BaseModel):
    data: list[FaultRecordOut]
    meta: dict


# ── Comments ──────────────────────────────────────────────────────────────────

class FaultCommentOut(BaseModel):
    id: str
    faultId: str
    userId: str
    authorName: str
    body: str
    createdAt: datetime

    @classmethod
    def from_orm_model(cls, c) -> "FaultCommentOut":
        return cls(
            id=c.id,
            faultId=c.fault_id,
            userId=c.user_id,
            authorName=c.author.name if c.author else "",
            body=c.body,
            createdAt=c.created_at,
        )


class FaultCommentCreate(BaseModel):
    body: str
