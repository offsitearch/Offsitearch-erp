"""Add password_plain column for admin credential recovery

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_add_password_plain"
down_revision = "0016_audit_ip_user_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_plain", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_plain")
