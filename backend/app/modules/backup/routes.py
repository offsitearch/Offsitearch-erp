"""Backup & restore routes.

Endpoints: /backup — status, Google Drive one-click OAuth connect,
manual/scheduled backups, history and a direct JSON-dump download.
The whole router is executive-only (L0/L1) — backups contain every
table in the database including salary and financial data.
"""

from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.backup.models import BackupHistory
from app.modules.backup.schemas import BackupHistoryOut, BackupScheduleIn, BackupStatusOut
from app.modules.backup import service as backup_service
from app.modules.identity.schemas import MessageResponse
from app.modules.audit.service import log_audit

logger = logging.getLogger("app.backup")

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("/status", response_model=BackupStatusOut)
async def backup_status(
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    return await backup_service.status_payload(db)


@router.get("/history", response_model=list[BackupHistoryOut])
async def backup_history(
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BackupHistory]:
    return await backup_service.list_history(db, limit)


@router.get("/google/connect")
async def google_connect(
    current_user: Annotated[User, Depends(require_min_level("L1"))],
) -> RedirectResponse:
    """One-click setup: bounce the browser through Google's consent screen.

    The callback stores the tokens and redirects back to the settings page.
    """
    return backup_service.connect_redirect()


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    # `state` must carry a fresh HMAC signature from our own connect
    # endpoint — otherwise this route would accept authorization codes from
    # anywhere (OAuth CSRF → attacker-hosted Drive receiving backups).
    if error or not code or not backup_service.verify_state(state):
        if not error:
            logger.warning("Google Drive callback rejected (bad or missing state)")
        return RedirectResponse(url=f"{backup_service.settings.backup_ui_redirect}&drive=error")
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await backup_service.exchange_code(db, code)
            await db.commit()
        except Exception:  # noqa: BLE001 — user-facing redirect carries the state
            logger.exception("Google Drive token exchange failed")
            return RedirectResponse(url=f"{backup_service.settings.backup_ui_redirect}&drive=error")
    return RedirectResponse(url=f"{backup_service.settings.backup_ui_redirect}&drive=connected")


@router.post("/google/disconnect", response_model=MessageResponse)
async def google_disconnect(
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    await backup_service.disconnect(db)
    await log_audit(db, current_user, "delete", "backup_google_connection")
    await db.commit()
    return MessageResponse(message="Google Drive disconnected")


@router.put("/schedule", response_model=BackupStatusOut)
async def update_schedule(
    payload: BackupScheduleIn,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    status = await backup_service.update_schedule(db, payload.auto_enabled, payload.frequency)
    await log_audit(
        db,
        current_user,
        "update",
        "backup_schedule",
        details={"auto_enabled": payload.auto_enabled, "frequency": payload.frequency},
    )
    await db.commit()
    return status


@router.post("/run", response_model=BackupHistoryOut)
async def run_backup(
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackupHistory:
    history = await backup_service.run_backup(db, trigger="manual")
    if history.status != "success":
        raise HTTPException(status_code=502, detail=f"Backup failed: {history.error_message}")
    await log_audit(
        db,
        current_user,
        "create",
        "backup",
        details={"file_name": history.file_name, "size_bytes": history.file_size_bytes},
    )
    # run_backup already committed; audit trail rides the same session state
    await db.commit()
    return history


@router.get("/download")
async def download_backup(
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Direct one-click download of a fresh database dump (no Drive needed)."""
    content, file_name = await backup_service.build_dump(db)
    await log_audit(db, current_user, "create", "backup_download", details={"file_name": file_name})
    await db.commit()
    return StreamingResponse(
        iter([content]),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
