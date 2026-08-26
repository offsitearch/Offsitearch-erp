"""Enable Row Level Security on all public tables.

Creates permissive policies for the postgres role (used by the backend).
This is defense-in-depth: if the DB connection string leaks and is used
with a non-superuser role, RLS restricts access.

Revision ID: 0015_enable_rls
Revises: 0014_fix_deal_stage
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_enable_rls"
down_revision = "0014_fix_deal_stage"
branch_labels = None
depends_on = None

# All application tables (excluding alembic_version and system tables)
TABLES = [
    "attendance",
    "audit_logs",
    "client_communications",
    "clients",
    "departments",
    "document_folders",
    "document_versions",
    "documents",
    "employee_documents",
    "expenses",
    "holidays",
    "invoice_items",
    "invoices",
    "leave_balance",
    "leaves",
    "meeting_attendees",
    "meetings",
    "notices",
    "notifications",
    "payroll_entries",
    "payroll_runs",
    "project_phases",
    "project_team",
    "projects",
    "refresh_tokens",
    "salary_components",
    "settings",
    "site_visit_photos",
    "site_visits",
    "task_checklist",
    "tasks",
    "timesheet_entries",
    "timesheets",
    "users",
    "vendor_projects",
    "vendors",
]


def upgrade() -> None:
    for table in TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create permissive policy for postgres role (backend DB user)
        # This ensures the backend is not affected by RLS
        op.execute(
            f"DROP POLICY IF EXISTS postgres_full_access ON {table}"
        )
        op.execute(
            f"CREATE POLICY postgres_full_access ON {table} "
            f"FOR ALL TO postgres USING (true) WITH CHECK (true)"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS postgres_full_access ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
