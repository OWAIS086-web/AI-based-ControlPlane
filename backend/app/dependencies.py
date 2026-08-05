from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_token
from app.prisma_client import db

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise unauthorized()

    if payload.get("type") != "access":
        raise unauthorized("Invalid token type.")

    user_id: str = payload.get("sub", "")
    user = await db.user.find_unique(where={"id": user_id})
    if not user or user.deletedAt is not None:
        raise unauthorized("User not found.")
    if user.status == "inactive":
        raise forbidden("Account is inactive.")
    return user


async def require_process_manager(current_user=Depends(get_current_user)):
    if current_user.role != "process_manager":
        raise forbidden("Requires process_manager role.")
    return current_user
