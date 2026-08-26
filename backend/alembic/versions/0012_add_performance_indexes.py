"""Add performance indexes on high-traffic filter/sort columns.

Only creates indexes that do not already exist in the database.

Revision ID: 0012_add_performance_indexes
Revises: 0011_add_indexes_fix_cascade
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_add_performance_indexes"
down_revision = "0011_add_indexes_fix_cascade"
branch_labels = None
depends_on = None

# (table, column, index_name) — only indexes NOT already present in DB
INDEXES_TO_CREATE = [
    ("invoices", "invoice_date", "ix_invoices_invoice_date"),
    ("invoices", "due_date", "ix_invoices_due_date"),
    ("expenses", "expense_date", "ix_expenses_expense_date"),
    ("expenses", "category", "ix_expenses_category"),
    ("leaves", "status", "ix_leaves_status"),
    ("users", "role", "ix_users_role"),
    ("users", "is_active", "ix_users_is_active"),
    ("projects", "is_active", "ix_projects_is_active"),
    ("clients", "is_active", "ix_clients_is_active"),
    ("notices", "is_active", "ix_notices_is_active"),
    ("settings", "group", "ix_settings_group"),
]

# Already exist in DB (confirmed via pg_indexes):
# ix_expenses_status, ix_tasks_status, ix_attendance_status_date,
# ix_invoices_status_due, ix_notifications_user_read, ix_notifications_user_id


def upgrade() -> None:
    for table, column, idx_name in INDEXES_TO_CREATE:
        op.create_index(idx_name, table, [column])


def downgrade() -> None:
    for table, column, idx_name in INDEXES_TO_CREATE:
        op.drop_index(idx_name, table_name=table)
