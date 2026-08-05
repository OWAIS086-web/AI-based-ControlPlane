from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Integer, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.maintenance.database import Base


class PaintInspection(Base):
    __tablename__ = "paint_inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    painting_date: Mapped[date] = mapped_column(Date, nullable=False)
    oven_out_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    color: Mapped[str] = mapped_column(String(100), nullable=False)
    vin_no: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    total_problems: Mapped[int] = mapped_column(Integer, default=0)
    checked_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    defects: Mapped[List["InspectionDefect"]] = relationship(
        "InspectionDefect", back_populates="inspection", cascade="all, delete-orphan", lazy="selectin"
    )
    vehicle_parts: Mapped[List["VehiclePart"]] = relationship(
        "VehiclePart", back_populates="inspection", cascade="all, delete-orphan", lazy="selectin"
    )


class InspectionDefect(Base):
    __tablename__ = "inspection_defects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, ForeignKey("paint_inspections.id", ondelete="CASCADE"), nullable=False)
    serial_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    total_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    let_go_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    repair_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    inspection: Mapped["PaintInspection"] = relationship("PaintInspection", back_populates="defects")


class VehiclePart(Base):
    __tablename__ = "vehicle_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, ForeignKey("paint_inspections.id", ondelete="CASCADE"), nullable=False)
    part_code: Mapped[str] = mapped_column(String(100), nullable=False)
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    annotation: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    inspection: Mapped["PaintInspection"] = relationship("PaintInspection", back_populates="vehicle_parts")
