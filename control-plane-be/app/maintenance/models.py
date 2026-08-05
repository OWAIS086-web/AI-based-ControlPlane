"""SQLAlchemy ORM models for the maintenance module."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.maintenance.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MaintenanceUserRole(str, enum.Enum):
    admin = "admin"
    technician = "technician"


class MaintenanceUserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class FaultSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FaultStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class MaintenanceUser(Base):
    __tablename__ = "maintenance_users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[MaintenanceUserRole] = mapped_column(
        Enum(MaintenanceUserRole, name="maintenance_user_role"), nullable=False
    )
    status: Mapped[MaintenanceUserStatus] = mapped_column(
        Enum(MaintenanceUserStatus, name="maintenance_user_status"),
        nullable=False,
        default=MaintenanceUserStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    refresh_tokens: Mapped[list["MaintenanceRefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reported_faults: Mapped[list["FaultRecord"]] = relationship(
        "FaultRecord", foreign_keys="FaultRecord.reported_by", back_populates="reporter"
    )
    assigned_faults: Mapped[list["FaultRecord"]] = relationship(
        "FaultRecord", foreign_keys="FaultRecord.assigned_to", back_populates="assignee"
    )
    comments: Mapped[list["FaultComment"]] = relationship(back_populates="author")


class MaintenanceRefreshToken(Base):
    __tablename__ = "maintenance_refresh_tokens"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("maintenance_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["MaintenanceUser"] = relationship(back_populates="refresh_tokens")


class FaultRecord(Base):
    __tablename__ = "fault_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[FaultSeverity] = mapped_column(
        Enum(FaultSeverity, name="fault_severity"), nullable=False, default=FaultSeverity.medium
    )
    status: Mapped[FaultStatus] = mapped_column(
        Enum(FaultStatus, name="fault_status"), nullable=False, default=FaultStatus.open, index=True
    )
    reported_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("maintenance_users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_to: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("maintenance_users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    reporter: Mapped["MaintenanceUser"] = relationship(
        "MaintenanceUser", foreign_keys=[reported_by], back_populates="reported_faults"
    )
    assignee: Mapped["MaintenanceUser | None"] = relationship(
        "MaintenanceUser", foreign_keys=[assigned_to], back_populates="assigned_faults"
    )
    comments: Mapped[list["FaultComment"]] = relationship(
        back_populates="fault", cascade="all, delete-orphan"
    )


class FaultComment(Base):
    __tablename__ = "fault_comments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    fault_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("fault_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("maintenance_users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    fault: Mapped["FaultRecord"] = relationship(back_populates="comments")
    author: Mapped["MaintenanceUser"] = relationship(back_populates="comments")
