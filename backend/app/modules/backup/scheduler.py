"""Hourly scheduler that fires due automatic backups.

Started/stopped from the app lifespan (app.main). The module never
imports app.main — the dependency points one way only.

A Postgres advisory lock guards the run so multiple backend workers (or a
second container) can never upload the same scheduled backup twice; the
in-process asyncio lock in the service only serialises within one worker.
"""

import asyncio
import contextlib
import logging

from sqlalchemy import text

from app.modules.backup import service as backup_service

logger = logging.getLogger("app.backup")

CHECK_INTERVAL_SECONDS = 3600
ADVISORY_LOCK_KEY = "studioerp:backup:auto"
_task: asyncio.Task | None = None


async def _try_advisory_lock(db) -> bool:
    result = await db.execute(
        text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": ADVISORY_LOCK_KEY}
    )
    return bool(result.scalar())


async def _unlock_advisory(db) -> None:
    await db.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": ADVISORY_LOCK_KEY})


async def _tick() -> None:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        if not await _try_advisory_lock(db):
            logger.debug("Another worker holds the backup lock — skipping")
            return
        try:
            if await backup_service.is_backup_due(db):
                history = await backup_service.run_backup(db, trigger="auto")
                if history.status == "success":
                    logger.info("Auto backup uploaded: %s", history.file_name)
                else:
                    logger.error("Auto backup failed: %s", history.error_message)
        finally:
            try:
                await _unlock_advisory(db)
                await db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("Releasing the backup advisory lock failed")


async def _loop() -> None:
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            await _tick()
        except asyncio.CancelledError:  # pragma: no cover — shutdown path
            raise
        except Exception:  # noqa: BLE001 — scheduler must survive any failure
            logger.exception("Backup scheduler iteration failed")


def start_backup_scheduler() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        logger.info("Backup scheduler started (hourly check)")


def stop_backup_scheduler() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            pass
        _task = None
