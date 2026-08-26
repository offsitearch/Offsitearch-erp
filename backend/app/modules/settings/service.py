"""System settings key-value store CRUD."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import Setting
from app.modules.settings.schemas import SettingUpsertIn
from app.utils.errors import SettingsError


async def list_settings(db: AsyncSession, group: str | None = None) -> list[dict]:
    stmt = select(Setting).order_by(Setting.group, Setting.key)
    if group:
        stmt = stmt.where(Setting.group == group)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": row.id, "group": row.group, "key": row.key, "value": row.value} for row in rows]


async def upsert_settings(db: AsyncSession, entries: list[SettingUpsertIn]) -> list[dict]:
    for entry in entries:
        result = await db.execute(
            select(Setting).where(Setting.group == entry.group, Setting.key == entry.key)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(Setting(group=entry.group, key=entry.key, value=entry.value))
        else:
            existing.value = entry.value
    await db.commit()
    return await list_settings(db)


async def delete_setting(db: AsyncSession, group: str, key: str) -> bool:
    result = await db.execute(select(Setting).where(Setting.group == group, Setting.key == key))
    existing = result.scalar_one_or_none()
    if existing is None:
        raise SettingsError("Setting not found", 404)
    await db.delete(existing)
    await db.commit()
    return True


async def get_studio_info(db: AsyncSession) -> dict:
    """Read the studio/company profile used on generated PDFs."""
    result = await db.execute(
        select(Setting).where(Setting.group == "company", Setting.key == "profile")
    )
    setting = result.scalar_one_or_none()
    if setting:
        return setting.value
    from app.utils.pdf import (
        DEFAULT_GSTIN,
        STUDIO_ADDRESS_LINES,
        STUDIO_MONOGRAM,
        STUDIO_NAME,
        STUDIO_TAGLINE,
    )

    return {
        "name": STUDIO_NAME,
        "tagline": STUDIO_TAGLINE,
        "monogram": STUDIO_MONOGRAM,
        "address": list(STUDIO_ADDRESS_LINES),
        "gstin": DEFAULT_GSTIN,
    }
