"""Auth service — token issuance, refresh, revocation."""
import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError

from app.config import settings
from app.core.exceptions import unauthorized
from app.core.utils import ev
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.prisma_client import db
from app.utils.audit import write_audit


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def login(email: str, password: str) -> dict:
    user = await db.user.find_unique(where={"email": email})
    if not user or not verify_password(password, user.hashedPassword):
        raise unauthorized("Invalid email or password.")
    if ev(user.status) == "inactive":
        raise unauthorized("Account is inactive.")

    access_token = create_access_token(user.id, ev(user.role))
    refresh_token = create_refresh_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await db.refreshtoken.create(
        data={"user": {"connect": {"id": user.id}}, "tokenHash": _hash(refresh_token), "expiresAt": expires_at}
    )
    # await write_audit("user", f"User logged in: {user.email}", user.email, user.id)
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


async def refresh(refresh_token_str: str) -> dict:
    try:
        payload = decode_token(refresh_token_str)
    except JWTError:
        raise unauthorized("Invalid or expired refresh token.")

    if payload.get("type") != "refresh":
        raise unauthorized("Not a refresh token.")

    stored = await db.refreshtoken.find_unique(where={"tokenHash": _hash(refresh_token_str)})
    if not stored or stored.revoked:
        raise unauthorized("Refresh token has been revoked.")
    if stored.expiresAt < datetime.now(timezone.utc):
        raise unauthorized("Refresh token expired.")

    user = await db.user.find_unique(where={"id": stored.userId})
    if not user:
        raise unauthorized("User not found.")

    return {
        "accessToken": create_access_token(user.id, ev(user.role)),
        "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout(user_id: str) -> None:
    await db.refreshtoken.update_many(
        where={"userId": user_id, "revoked": False},
        data={"revoked": True},
    )


async def change_password(user_id: str, current_password: str, new_password: str) -> None:
    user = await db.user.find_unique(where={"id": user_id})
    if not user or not verify_password(current_password, user.hashedPassword):
        raise unauthorized("Current password is incorrect.")
    await db.user.update(
        where={"id": user_id},
        data={"hashedPassword": hash_password(new_password)},
    )
