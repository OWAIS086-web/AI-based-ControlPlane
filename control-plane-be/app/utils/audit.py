"""Write audit entries and helpers shared across services."""
import json
import uuid
from typing import Any

from app.prisma_client import db
from app.utils.cache import cache_delete

_AUDIT_STATS_KEY = "audit:stats"


async def write_audit(
    type: str,
    action: str,
    target: str,
    performed_by: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    await db.execute_raw(
        'INSERT INTO audit_entries (id, type, action, target, performed_by, metadata, created_at) '
        'VALUES ($1, $2::"AuditType", $3, $4, $5, $6::jsonb, NOW())',
        str(uuid.uuid4()),
        type,
        action,
        target,
        performed_by,
        json.dumps(metadata or {}),
    )
    # Bust the cached stats count on every write
    await cache_delete(_AUDIT_STATS_KEY)
