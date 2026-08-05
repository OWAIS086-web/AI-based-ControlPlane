"""JWT helpers for the maintenance module — uses a separate signing secret."""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.config import settings

_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 60
_REFRESH_EXPIRE_DAYS = 30


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({"exp": now + expires_delta, "iat": now})
    return jwt.encode(to_encode, settings.MAINTENANCE_JWT_SECRET, algorithm=_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    return _create_token(
        {"sub": user_id, "role": role, "type": "access", "svc": "maintenance"},
        timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh", "svc": "maintenance"},
        timedelta(days=_REFRESH_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError on invalid/expired tokens."""
    return jwt.decode(token, settings.MAINTENANCE_JWT_SECRET, algorithms=[_ALGORITHM])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


ACCESS_EXPIRE_SECONDS = _ACCESS_EXPIRE_MINUTES * 60
REFRESH_EXPIRE_DAYS = _REFRESH_EXPIRE_DAYS
