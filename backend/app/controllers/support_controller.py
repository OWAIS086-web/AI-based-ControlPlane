"""Support controller — bug reports and feature requests."""
from app.schemas.support import SupportOut
from app.services import support_service


async def report_bug(title, description, severity, steps, expected, actual, reporter_name, reporter_email) -> SupportOut:
    await support_service.report_bug(
        title=title, description=description, severity=severity,
        steps=steps, expected=expected, actual=actual,
        reporter_name=reporter_name, reporter_email=reporter_email,
    )
    return SupportOut(success=True, message="Bug report submitted — thank you!")


async def request_feature(title, description, priority, use_case, reporter_name, reporter_email) -> SupportOut:
    await support_service.request_feature(
        title=title, description=description, priority=priority,
        use_case=use_case, reporter_name=reporter_name, reporter_email=reporter_email,
    )
    return SupportOut(success=True, message="Feature request submitted — thank you!")
