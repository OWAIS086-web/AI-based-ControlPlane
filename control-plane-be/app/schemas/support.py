from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class BugReportCreate(BaseModel):
    title: str
    description: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    steps_to_reproduce: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None


class FeatureRequestCreate(BaseModel):
    title: str
    description: str
    use_case: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"


class SupportOut(BaseModel):
    success: bool
    message: str