"""Auth controller — validate input, delegate to auth_service."""
from jose import JWTError

from app.core.exceptions import unauthorized
from app.core.security import decode_token
from app.core.utils import ev
from app.schemas.auth import LoginResponse, RefreshResponse
from app.schemas.user import UserOut
from app.services import auth_service


def _serialize_user(user) -> UserOut:
    return UserOut(
        id=user.id, name=user.name, email=user.email,
        role=ev(user.role), status=ev(user.status),
        avatar=user.avatar, createdAt=user.createdAt, updatedAt=user.updatedAt,
    )


async def login(email: str, password: str) -> LoginResponse:
    result = await auth_service.login(email, password)
    return LoginResponse(
        accessToken=result["accessToken"],
        refreshToken=result["refreshToken"],
        expiresIn=result["expiresIn"],
        user=_serialize_user(result["user"]),
    )


async def refresh(refresh_token: str) -> RefreshResponse:
    result = await auth_service.refresh(refresh_token)
    return RefreshResponse(**result)


async def logout(token: str) -> None:
    try:
        payload = decode_token(token)
    except JWTError:
        raise unauthorized()
    await auth_service.logout(payload.get("sub", ""))


async def change_password(user_id: str, current_password: str, new_password: str) -> None:
    await auth_service.change_password(user_id, current_password, new_password)
