"""Add ip_address and user_agent columns to audit_logs.

Revision ID: 0016_audit_ip_user_agent
Revises: 0015_enable_rls
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_audit_ip_user_agent"
down_revision = "0015_enable_rls"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(45), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(255), nullable=True))
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "ip_address")
