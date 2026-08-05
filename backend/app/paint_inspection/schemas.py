from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class InspectionDefectCreate(BaseModel):
    serial_no: int
    name: str
    total_qty: Optional[int] = None
    let_go_qty: Optional[int] = None
    repair_qty: Optional[int] = None
    remarks: Optional[str] = None


class InspectionDefectResponse(BaseModel):
    id: int
    inspection_id: int
    serial_no: int
    name: str
    total_qty: Optional[int] = None
    let_go_qty: Optional[int] = None
    repair_qty: Optional[int] = None
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VehiclePartCreate(BaseModel):
    part_code: str
    part_name: str
    position: str
    annotation: Optional[str] = None


class VehiclePartResponse(BaseModel):
    id: int
    inspection_id: int
    part_code: str
    part_name: str
    position: str
    annotation: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaintInspectionCreate(BaseModel):
    inspection_date: date
    painting_date: date
    oven_out_time: Optional[str] = None
    color: str
    vin_no: str
    checked_by: Optional[str] = None
    confirmed_by: Optional[str] = None
    approved_by: Optional[str] = None
    defects: List[InspectionDefectCreate] = []
    vehicle_parts: List[VehiclePartCreate] = []


class PaintInspectionUpdate(BaseModel):
    inspection_date: date
    painting_date: date
    oven_out_time: Optional[str] = None
    color: str
    vin_no: str
    checked_by: Optional[str] = None
    confirmed_by: Optional[str] = None
    approved_by: Optional[str] = None
    defects: List[InspectionDefectCreate] = []
    vehicle_parts: List[VehiclePartCreate] = []


class PaintInspectionResponse(BaseModel):
    id: int
    inspection_date: date
    painting_date: date
    oven_out_time: Optional[str] = None
    color: str
    vin_no: str
    total_problems: int
    checked_by: Optional[str] = None
    confirmed_by: Optional[str] = None
    approved_by: Optional[str] = None
    created_by_id: str
    created_at: datetime
    updated_at: datetime
    defects: List[InspectionDefectResponse] = []
    vehicle_parts: List[VehiclePartResponse] = []

    model_config = {"from_attributes": True}


class PaintInspectionListResponse(BaseModel):
    items: List[PaintInspectionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
