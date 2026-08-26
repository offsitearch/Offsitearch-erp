"""Pydantic schemas for the backup module."""

from datetime import datetime

from pydantic import BaseModel


class BackupStatusOut(BaseModel):
    configured: bool  # Google OAuth client env vars present?
    connected: bool  # refresh token stored?
    account_email: str | None = None
    auto_enabled: bool
    frequency: str
    last_backup_at: datetime | None = None
    last_backup_status: str | None = None


class BackupScheduleIn(BaseModel):
    auto_enabled: bool
    frequency: str = "daily"  # daily | weekly


class BackupHistoryOut(BaseModel):
    id: int
    status: str
    trigger: str
    destination: str
    file_name: str | None
    file_size_bytes: int | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
