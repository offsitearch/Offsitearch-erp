"""Timesheet module: fix timesheets.status enum case, add lookup indexes.

The timesheets/timesheet_entries tables have existed (unused) since
migration 0005. They are now owned by the new timesheets module. This
migration aligns the legacy schema with the module:

- timesheets.status still carries the pre-0010 UPPERCASE check
  constraint while its server_default is lowercase 'draft' (which would
  violate it). Normalize values to lowercase and recreate the constraint,
  matching the convention migration 0010 applied to every other table.
- Index timesheets.status for the approvals queue.
- Index timesheet_entries.project_id for per-project hour rollups.

Revision ID: 0027_timesheets_module
Revises: 0026_invoice_hsn_sac
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_timesheets_module"
down_revision = "0026_invoice_hsn_sac"
branch_labels = None
depends_on = None

_STATUSES = ["draft", "submitted", "approved", "rejected"]


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'timesheets'::regclass AND contype = 'c'"
        )
    )
    for row in result:
        op.execute(f"ALTER TABLE timesheets DROP CONSTRAINT IF EXISTS {row[0]}")

    op.execute("UPDATE timesheets SET status = LOWER(status)")
    vals_str = ", ".join(f"'{v}'" for v in _STATUSES)
    op.execute(
        f"ALTER TABLE timesheets ADD CONSTRAINT ck_timesheets_status "
        f"CHECK ((status)::text = ANY (ARRAY[{vals_str}]))"
    )

    op.create_index("ix_timesheets_status", "timesheets", ["status"])
    op.create_index(
        "ix_timesheet_entries_project_id", "timesheet_entries", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_timesheet_entries_project_id", table_name="timesheet_entries")
    op.drop_index("ix_timesheets_status", table_name="timesheets")

    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'timesheets'::regclass AND contype = 'c'"
        )
    )
    for row in result:
        op.execute(f"ALTER TABLE timesheets DROP CONSTRAINT IF EXISTS {row[0]}")
    upper_vals = ", ".join(f"'{v.upper()}'" for v in _STATUSES)
    op.execute(
        f"ALTER TABLE timesheets ADD CONSTRAINT ck_timesheets_status "
        f"CHECK (status IN ({upper_vals}))"
    )
