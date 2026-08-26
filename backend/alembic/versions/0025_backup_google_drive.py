"""Backup module: Google Drive config + backup run history.

Adds:
- backup_configs: singleton row (id=1) holding the Google OAuth tokens,
  Drive folder id and the auto-backup schedule (enabled + frequency).
- backup_history: one row per backup attempt (manual or scheduled) with
  status, trigger, file name/size and any error message.

Revision ID: 0025_backup_google_drive
Revises: 0024_userid_auth
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0025_backup_google_drive"
down_revision = "0024_userid_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
        sa.Column("google_access_token", sa.Text(), nullable=True),
        sa.Column("google_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("google_account_email", sa.String(length=255), nullable=True),
        sa.Column("drive_folder_id", sa.String(length=255), nullable=True),
        sa.Column("auto_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("frequency", sa.String(length=10), server_default="daily", nullable=False),
        sa.Column("last_backup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Singleton row so services never branch on "no config yet".
    op.execute("INSERT INTO backup_configs (id) VALUES (1)")

    op.create_table(
        "backup_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=10), server_default="success", nullable=False),
        sa.Column("trigger", sa.String(length=10), server_default="manual", nullable=False),
        sa.Column("destination", sa.String(length=20), server_default="google_drive", nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backup_history_created_at", "backup_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_backup_history_created_at", table_name="backup_history")
    op.drop_table("backup_history")
    op.drop_table("backup_configs")
