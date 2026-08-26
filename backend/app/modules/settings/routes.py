"""Application settings routes.

Endpoints: /settings — read and upsert key-value settings. Admin roles only.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.settings.schemas import SettingOut, SettingUpsertIn
from app.modules.settings import service as settings_service
from app.modules.identity.schemas import MessageResponse
from app.modules.audit.service import log_audit
from app.utils.errors import SettingsError

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingOut])
async def list_settings(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    group: str | None = Query(default=None),
) -> list[dict]:
    return await settings_service.list_settings(db, group)


@router.put("", response_model=list[SettingOut])
async def upsert_settings(
    payload: list[SettingUpsertIn],
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    result = await settings_service.upsert_settings(db, payload)
    await log_audit(
        db,
        current_user,
        "update",
        "settings",
        details={"count": len(payload), "groups": sorted({entry.group for entry in payload})},
    )
    await db.commit()
    return result


@router.delete("/{group}/{key}", response_model=MessageResponse)
async def delete_setting(
    group: str,
    key: str,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    try:
        await settings_service.delete_setting(db, group, key)
    except SettingsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    await log_audit(db, current_user, "delete", "settings", details={"group": group, "key": key})
    await db.commit()
    return MessageResponse(message=f"Setting {group}.{key} deleted")
