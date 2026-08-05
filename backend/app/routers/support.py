"""Support routes — bug reports and feature requests."""
from fastapi import APIRouter, Depends

from app.controllers import support_controller
from app.dependencies import get_current_user
from app.schemas.support import BugReportCreate, FeatureRequestCreate, SupportOut

router = APIRouter(prefix="/support", tags=["Support"])


@router.post("/bug", response_model=SupportOut, status_code=201)
async def report_bug(body: BugReportCreate, current_user=Depends(get_current_user)):
    return await support_controller.report_bug(
        title=body.title,
        description=body.description,
        severity=body.severity,
        steps=body.steps_to_reproduce,
        expected=body.expected_behavior,
        actual=body.actual_behavior,
        reporter_name=current_user.name,
        reporter_email=current_user.email,
    )


@router.post("/feature", response_model=SupportOut, status_code=201)
async def request_feature(body: FeatureRequestCreate, current_user=Depends(get_current_user)):
    return await support_controller.request_feature(
        title=body.title,
        description=body.description,
        priority=body.priority,
        use_case=body.use_case,
        reporter_name=current_user.name,
        reporter_email=current_user.email,
    )
