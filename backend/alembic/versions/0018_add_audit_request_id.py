"""Add request_id column to audit_logs.

Revision ID: 0018_add_audit_request_id
Revises: 0017_add_password_plain
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_add_audit_request_id"
down_revision = "0017_add_password_plain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("request_id", sa.String(36), nullable=True))
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_column("audit_logs", "request_id")
