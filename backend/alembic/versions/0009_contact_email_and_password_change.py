"""add contact_email to users

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_contact_email"
down_revision = "0008_crm_pipeline_fees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("contact_email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "contact_email")
