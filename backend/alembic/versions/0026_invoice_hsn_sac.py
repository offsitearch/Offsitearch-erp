"""Invoices: structured GST-ready line items.

Adds hsn_sac to invoice_items so each line can carry its HSN/SAC code
(GST return filing). Quantity/rate/amount already exist; amount is now
always computed server-side as quantity * rate.

Revision ID: 0026_invoice_hsn_sac
Revises: 0025_backup_google_drive
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0026_invoice_hsn_sac"
down_revision = "0025_backup_google_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoice_items", sa.Column("hsn_sac", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("invoice_items", "hsn_sac")
