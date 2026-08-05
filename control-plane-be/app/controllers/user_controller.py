"""Users controller — serialisation, authorisation, delegation."""
from app.core.exceptions import forbidden
from app.core.utils import ev
from app.schemas.common import make_paginated
from app.schemas.user import UserOut, UserSettingsOut
from app.services import user_service


def _out(u) -> UserOut:
    return UserOut(
        id=u.id, name=u.name, email=u.email,
        role=ev(u.role), status=ev(u.status),
        avatar=u.avatar, createdAt=u.createdAt, updatedAt=u.updatedAt,
    )


def _settings_out(s) -> UserSettingsOut:
    return UserSettingsOut(
        userId=s.userId,
        notifications={
            "newUploads": s.notifNewUploads,
            "migrations": s.notifMigrations,
            "userChanges": s.notifUserChanges,
            "systemAlerts": s.notifSystemAlerts,
        },
        dataRetentionDays=s.dataRetentionDays,
        updatedAt=s.updatedAt,
    )


def _assert_self_or_manager(current_user, target_user_id: str) -> None:
    if current_user.id != target_user_id and ev(current_user.role) != "process_manager":
        raise forbidden()


async def list_users(role, status, page, limit) -> dict:
    result = await user_service.list_users(role, status, page, limit)
    return make_paginated([_out(u) for u in result["users"]], result["total"], page, limit)


async def create_user(name, email, role, password, actor_id) -> UserOut:
    return _out(await user_service.create_user(name, email, role, password, actor_id))


async def get_user(user_id: str) -> UserOut:
    return _out(await user_service.get_user(user_id))


async def update_user(user_id: str, name, email, current_user) -> UserOut:
    _assert_self_or_manager(current_user, user_id)
    return _out(await user_service.update_user(user_id, name, email, current_user.id))


async def update_user_status(user_id: str, status: str, actor_id: str) -> UserOut:
    return _out(await user_service.update_user_status(user_id, status, actor_id))


async def delete_user(user_id: str, actor_id: str) -> None:
    await user_service.delete_user(user_id, actor_id)


async def get_settings(user_id: str, current_user) -> UserSettingsOut:
    _assert_self_or_manager(current_user, user_id)
    return _settings_out(await user_service.get_settings(user_id))


async def update_settings(user_id: str, notif_data: dict, data_retention_days, current_user) -> UserSettingsOut:
    _assert_self_or_manager(current_user, user_id)
    updated = await user_service.update_settings(
        user_id,
        notif_data.get("newUploads"),
        notif_data.get("migrations"),
        notif_data.get("userChanges"),
        notif_data.get("systemAlerts"),
        data_retention_days,
    )
    return _settings_out(updated)
