"""Backup service: JSON dumps of the whole database with optional
Google Drive upload and scheduled runs.

Google Drive integration uses plain REST over httpx (no extra deps):
OAuth 2.0 offline access with the ``drive.file`` scope so the app can
only see files it created itself.
"""

import asyncio
import gzip
import hashlib
import hmac
import json
import logging
import secrets
import time
from base64 import urlsafe_b64encode
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import Base
from app.modules.backup.models import BackupConfig, BackupHistory
from app.utils.shared import now_local

logger = logging.getLogger("app.backup")

DRIVE_FOLDER_NAME = "StudioERP Backups"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"

# Tables never written into the dump file: the config row holds live OAuth
# tokens, and embedding them inside backups that themselves travel to Drive
# (and get downloaded) would spread the secret everywhere.
DUMP_EXCLUDED_TABLES = frozenset({"backup_configs"})
# Keep the newest N files in the Drive folder; older ones are pruned after
# each successful upload so storage cannot grow without bound.
DRIVE_RETENTION_KEEP = 30

_state_log = logging.getLogger("app.backup.state")

_run_lock = asyncio.Lock()


# ── Config singleton ─────────────────────────────────────────────────────


def google_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


async def get_or_create_config(db: AsyncSession) -> BackupConfig:
    config = (
        await db.execute(select(BackupConfig).where(BackupConfig.id == 1))
    ).scalar_one_or_none()
    if config is None:
        config = BackupConfig(id=1)
        db.add(config)
        await db.flush()
    return config


def _status_dict(config: BackupConfig, last_backup_status: str | None) -> dict:
    """Single source for the status payload shape (status + schedule endpoints)."""
    return {
        "configured": google_configured(),
        "connected": bool(decrypt_secret(config.google_refresh_token)),
        "account_email": config.google_account_email,
        "auto_enabled": config.auto_enabled,
        "frequency": config.frequency,
        "last_backup_at": config.last_backup_at,
        "last_backup_status": last_backup_status,
    }


async def status_payload(db: AsyncSession) -> dict:
    config = await get_or_create_config(db)
    last = (
        await db.execute(select(BackupHistory).order_by(BackupHistory.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    return _status_dict(config, last.status if last else None)


async def update_schedule(db: AsyncSession, auto_enabled: bool, frequency: str) -> dict:
    config = await get_or_create_config(db)
    config.auto_enabled = auto_enabled
    config.frequency = frequency if frequency in {"daily", "weekly"} else "daily"
    await db.flush()
    await db.refresh(config)
    # Same shape as status_payload — callers cache this over the top of the
    # cached status, so it must carry the real last_backup_status.
    return await status_payload(db)


async def list_history(db: AsyncSession, limit: int = 20) -> list[BackupHistory]:
    result = await db.execute(
        select(BackupHistory).order_by(BackupHistory.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ── Secrets at rest ──────────────────────────────────────────────────────
# OAuth tokens live in the database, so they are encrypted with a Fernet key
# derived from SECRET_KEY. Anyone with raw DB read access no longer gets a
# working Drive token for free.

_STATE_MAX_AGE_SECONDS = 600


def _fernet() -> Fernet:
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(urlsafe_b64encode(key))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        # Written by an older plaintext build (or different SECRET_KEY) —
        # treat as absent rather than crashing every status call.
        logger.warning("Backup token could not be decrypted — treating it as absent")
        return None


# ── Signed OAuth state ───────────────────────────────────────────────────


def make_state() -> str:
    """HMAC-signed, timestamped state so the callback can prove the flow
    started here — without needing server-side session storage."""
    nonce = secrets.token_urlsafe(16)
    ts = int(time.time())
    msg = f"{nonce}.{ts}".encode()
    sig = hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).hexdigest()
    return f"{nonce}.{ts}.{sig}"


def verify_state(state: str | None) -> bool:
    if not state:
        return False
    parts = state.split(".")
    if len(parts) != 3:
        return False
    nonce, ts_raw, sig = parts
    try:
        ts = int(ts_raw)
    except ValueError:
        return False
    if time.time() - ts > _STATE_MAX_AGE_SECONDS:
        return False
    expected = hmac.new(
        settings.secret_key.encode(), f"{nonce}.{ts}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig)


# ── Google OAuth ─────────────────────────────────────────────────────────


def connect_redirect() -> RedirectResponse:
    """One-click entry point: redirect the browser to Google's consent screen."""
    if not google_configured():
        return RedirectResponse(url=f"{settings.backup_ui_redirect}&drive=not_configured")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": f"{DRIVE_SCOPE} https://www.googleapis.com/auth/userinfo.email",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": make_state(),
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=307)


async def _token_request(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()


async def exchange_code(db: AsyncSession, code: str) -> None:
    """OAuth callback handler: swap the auth code for tokens, store them,
    record the account email and pre-create the Drive folder."""
    tokens = await _token_request(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
    )
    access_token = tokens["access_token"]
    expires_in = int(tokens.get("expires_in", 3600))
    refresh_token = tokens.get("refresh_token")  # present thanks to prompt=consent

    async with httpx.AsyncClient(timeout=30) as client:
        userinfo = await client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo.raise_for_status()
        email = userinfo.json().get("email")

    config = await get_or_create_config(db)
    if refresh_token:  # Google may omit on re-consent; keep the old one otherwise
        old_refresh = decrypt_secret(config.google_refresh_token)
        if old_refresh and old_refresh != refresh_token:
            logger.info("Google Drive refresh token rotated")
        config.google_refresh_token = encrypt_secret(refresh_token)
    config.google_access_token = encrypt_secret(access_token)
    config.google_token_expires_at = now_local() + timedelta(seconds=expires_in)
    config.google_account_email = email
    config.drive_folder_id = await _ensure_drive_folder(access_token)
    await db.flush()


async def disconnect(db: AsyncSession) -> None:
    config = await get_or_create_config(db)
    config.google_refresh_token = None
    config.google_access_token = None
    config.google_token_expires_at = None
    config.google_account_email = None
    config.drive_folder_id = None
    # A schedule without a Drive connection is dead weight — and silently
    # resuming uploads on reconnect would surprise whoever disconnected.
    config.auto_enabled = False
    await db.flush()


async def _access_token(db: AsyncSession, config: BackupConfig) -> str:
    """Return a valid Drive access token, refreshing it when stale."""
    expires_at = config.google_token_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    stored_access = decrypt_secret(config.google_access_token)
    fresh = (
        stored_access is not None
        and expires_at is not None
        and expires_at > now_local() + timedelta(minutes=2)
    )
    if fresh and stored_access:
        return stored_access
    tokens = await _token_request(
        {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": decrypt_secret(config.google_refresh_token),
            "grant_type": "refresh_token",
        }
    )
    config.google_access_token = encrypt_secret(tokens["access_token"])
    config.google_token_expires_at = now_local() + timedelta(
        seconds=int(tokens.get("expires_in", 3600))
    )
    await db.flush()
    return tokens["access_token"]


# ── Google Drive helpers ─────────────────────────────────────────────────


async def _drive_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _ensure_drive_folder(access_token: str | None) -> str | None:
    if not access_token:
        return None
    query = (
        f"name='{DRIVE_FOLDER_NAME}' and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        found = await client.get(
            GOOGLE_DRIVE_FILES_URL,
            params={"q": query, "fields": "files(id)", "pageSize": 1},
            headers=_drive_headers(access_token),
        )
        found.raise_for_status()
        files = found.json().get("files", [])
        if files:
            return files[0]["id"]
        created = await client.post(
            GOOGLE_DRIVE_FILES_URL,
            json={"name": DRIVE_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
            headers=_drive_headers(access_token),
        )
        created.raise_for_status()
        return created.json()["id"]


async def _prune_drive_folder(access_token: str, folder_id: str | None) -> None:
    """Keep only the newest DRIVE_RETENTION_KEEP files in the backup folder.

    Best-effort: a prune failure must never fail the backup that just
    uploaded successfully.
    """
    if not folder_id:
        return
    query = f"'{folder_id}' in parents and trashed=false"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            found = await client.get(
                GOOGLE_DRIVE_FILES_URL,
                params={
                    "q": query,
                    "fields": "files(id,name)",
                    "orderBy": "createdTime desc",
                    "pageSize": 100,
                },
                headers=_drive_headers(access_token),
            )
            found.raise_for_status()
            files = found.json().get("files", [])
            for stale in files[DRIVE_RETENTION_KEEP:]:
                await client.delete(
                    f"{GOOGLE_DRIVE_FILES_URL}/{stale['id']}",
                    headers=_drive_headers(access_token),
                )
                logger.info("Pruned old Drive backup: %s", stale.get("name"))
    except Exception:  # noqa: BLE001 — pruning is opportunistic
        logger.exception("Drive retention prune failed (backup itself is safe)")


async def _upload_to_drive(
    db: AsyncSession, config: BackupConfig, file_name: str, content: bytes
) -> int:
    token = await _access_token(db, config)
    if not config.drive_folder_id:
        config.drive_folder_id = await _ensure_drive_folder(token)
    metadata: dict[str, Any] = {"name": file_name}
    if config.drive_folder_id:
        metadata["parents"] = [config.drive_folder_id]
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            f"{GOOGLE_DRIVE_UPLOAD_URL}?uploadType=multipart",
            files={
                "metadata": (None, json.dumps(metadata), "application/json"),
                "file": (file_name, content, "application/gzip"),
            },
            headers=_drive_headers(token),
        )
        response.raise_for_status()
    await _prune_drive_folder(token, config.drive_folder_id)
    return len(content)


# ── Database dump ────────────────────────────────────────────────────────


def _serialize(value: Any) -> Any:
    # datetime is a subclass of date — test it first.
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _pack_payload(payload: dict[str, list]) -> bytes:
    """CPU-bound tail of the dump (JSON + gzip) — run in a worker thread so
    the event loop keeps serving requests while a large backup compresses."""
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return gzip.compress(blob, compresslevel=6)


async def build_dump(db: AsyncSession) -> tuple[bytes, str]:
    """Serialize every table to a gzipped JSON archive.

    Returns ``(gzip_bytes, suggested_file_name)``. Excluded tables carry
    live secrets and are deliberately left out (see DUMP_EXCLUDED_TABLES).
    """
    stamp = now_local().strftime("%Y%m%d-%H%M")
    file_name = f"studioerp-backup-{stamp}.json.gz"
    payload: dict[str, list] = {}
    for table in Base.metadata.sorted_tables:
        if table.name in DUMP_EXCLUDED_TABLES:
            continue
        rows = (await db.execute(select(table))).mappings().all()
        payload[table.name] = [
            {key: _serialize(value) for key, value in dict(row).items()} for row in rows
        ]
    return await asyncio.to_thread(_pack_payload, payload), file_name


async def run_backup(
    db: AsyncSession,
    *,
    trigger: str,
    destination: str = "google_drive",
    commit: bool = True,
) -> BackupHistory:
    """Create a dump and push it to the configured destination.

    Never raises: failures are recorded in history (and returned).
    """
    async with _run_lock:
        config = await get_or_create_config(db)
        history = BackupHistory(status="success", trigger=trigger, destination=destination)
        db.add(history)
        try:
            content, file_name = await build_dump(db)
            history.file_name = file_name
            history.file_size_bytes = len(content)
            if destination == "google_drive":
                size = await _upload_to_drive(db, config, file_name, content)
                history.file_size_bytes = size
                config.last_backup_at = now_local()
            else:
                config.last_backup_at = now_local()
        except Exception as exc:  # noqa: BLE001 — recorded, never surfaced raw
            history.status = "failed"
            history.error_message = str(exc)[:2000]
        finally:
            if commit:
                await db.commit()
                await db.refresh(history)
            else:
                await db.flush()
        return history


async def is_backup_due(db: AsyncSession) -> bool:
    config = await get_or_create_config(db)
    if not config.auto_enabled:
        return False
    if not decrypt_secret(config.google_refresh_token):
        return False
    if config.last_backup_at is None:
        return True
    last_local = config.last_backup_at
    today = now_local().date()
    if config.frequency == "weekly":
        return last_local.isocalendar()[:2] < today.isocalendar()[:2]
    return last_local.date() < today
