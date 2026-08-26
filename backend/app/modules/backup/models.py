"""Backup models: singleton Google Drive config + backup run history."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BackupConfig(TimestampMixin, Base):
    """Singleton row (id=1) holding the Google Drive connection and
    auto-backup schedule. OAuth tokens are stored server-side (encrypted
    at rest — see backup.service) and are never exposed through the API
    (only the account email is returned).
    """

    __tablename__ = "backup_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text)
    google_access_token: Mapped[str | None] = mapped_column(Text)
    google_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    google_account_email: Mapped[str | None] = mapped_column(String(255))
    drive_folder_id: Mapped[str | None] = mapped_column(String(255))
    auto_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    frequency: Mapped[str] = mapped_column(String(10), nullable=False, server_default="daily")
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BackupHistory(TimestampMixin, Base):
    """One row per backup attempt (manual or scheduled)."""

    __tablename__ = "backup_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="success"
    )  # success | failed
    trigger: Mapped[str] = mapped_column(
        String(10), nullable=False, default="manual"
    )  # manual | auto
    destination: Mapped[str] = mapped_column(String(20), nullable=False, default="google_drive")
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
