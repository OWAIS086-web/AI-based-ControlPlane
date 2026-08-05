"""Audit log controller."""
from app.core.utils import ev
from app.schemas.audit import AuditEntryOut, AuditStatsOut
from app.schemas.common import make_paginated
from app.schemas.user import UserOut
from app.services import audit_service


def _user_out(u) -> UserOut | None:
    if not u:
        return None
    return UserOut(
        id=u.id, name=u.name, email=u.email, role=ev(u.role),
        status=ev(u.status), avatar=u.avatar, createdAt=u.createdAt, updatedAt=u.updatedAt,
    )


def _out(e) -> AuditEntryOut:
    return AuditEntryOut(
        id=e.id, type=ev(e.type), action=e.action, target=e.target,
        performedBy=e.performedBy, performer=_user_out(getattr(e, "performer", None)),
        metadata=e.metadata if isinstance(e.metadata, dict) else {},
        createdAt=e.createdAt,
    )


async def list_audit(type, performed_by, search, from_, to, page, limit) -> dict:
    result = await audit_service.list_audit(type, performed_by, search, from_, to, page, limit)
    return make_paginated([_out(e) for e in result["entries"]], result["total"], page, limit)


async def get_stats() -> AuditStatsOut:
    return await audit_service.get_stats()
