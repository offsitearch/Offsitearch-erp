"""Fix enum case: convert UPPERCASE DB values/constraints to lowercase to match Python enums.

Drops ALL check constraints on each table dynamically, normalizes data
to lowercase, then recreates constraints with ck_{table}_{column} naming.

Revision ID: 0010_fix_enum_case
Revises: 0009_contact_email
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_fix_enum_case"
down_revision = "0009_contact_email"
branch_labels = None
depends_on = None


COLUMN_ENUMS = [
    ("users", "role",
     ["super_admin", "admin", "project_lead", "employee", "intern", "client"]),
    ("users", "employment_type",
     ["full_time", "part_time", "contract", "internship"]),
    ("attendance", "status",
     ["present", "absent", "late", "half_day", "work_from_home", "on_leave"]),
    ("attendance", "check_in_method",
     ["web", "manual", "qr", "gps", "ip"]),
    ("leave_balance", "leave_type",
     ["casual", "sick", "earned", "compensatory", "maternity", "paternity", "work_from_home", "unpaid"]),
    ("leaves", "leave_type",
     ["casual", "sick", "earned", "compensatory", "maternity", "paternity", "work_from_home", "unpaid"]),
    ("leaves", "status",
     ["pending", "approved", "rejected", "cancelled"]),
    ("projects", "project_type",
     ["residential", "commercial", "interior", "institutional", "landscape", "urban_planning", "renovation", "mixed_use"]),
    ("projects", "status",
     ["draft", "concept", "design", "under_review", "in_construction", "completed", "on_hold", "cancelled"]),
    ("project_phases", "status",
     ["not_started", "in_progress", "completed", "delayed"]),
    ("tasks", "priority",
     ["low", "medium", "high", "urgent"]),
    ("tasks", "status",
     ["todo", "in_progress", "review", "done", "blocked"]),
    ("invoices", "status",
     ["draft", "sent", "partial", "paid", "overdue", "cancelled"]),
    ("invoices", "payment_method",
     ["bank_transfer", "upi", "cash", "cheque", "card"]),
    ("expenses", "status",
     ["pending", "approved", "rejected"]),
    ("payroll_runs", "status",
     ["draft", "processed"]),
    ("vendors", "category",
     ["contractor", "material_supplier", "consultant", "printing", "photographer", "other"]),
    ("notices", "importance",
     ["low", "medium", "high"]),
    ("meetings", "meeting_type",
     ["internal", "client", "team", "review", "other"]),
    ("meetings", "status",
     ["scheduled", "completed", "cancelled"]),
    ("meeting_attendees", "rsvp_status",
     ["pending", "accepted", "declined"]),
    ("site_visits", "status",
     ["scheduled", "completed", "cancelled"]),
    ("client_communications", "type",
     ["call", "email", "meeting", "site_visit"]),
    ("clients", "client_type",
     ["individual", "company", "developer", "government"]),
    ("clients", "deal_stage",
     ["lead", "proposal", "negotiation", "won", "lost"]),
]

ALL_TABLES = sorted({t for t, _, _ in COLUMN_ENUMS})


def upgrade() -> None:
    # Phase 1: Drop ALL check constraints dynamically by querying pg_constraint.
    for table in ALL_TABLES:
        conn = op.get_bind()
        result = conn.execute(
            sa.text(
                f"SELECT conname FROM pg_constraint "
                f"WHERE conrelid = '{table}'::regclass AND contype = 'c'"
            ),
        )
        for row in result:
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {row[0]}")

    # Phase 2: Normalize data and recreate constraints per column
    for table, column, valid_values in COLUMN_ENUMS:
        constraint_name = f"ck_{table}_{column}"

        op.execute(f"UPDATE {table} SET {column} = LOWER({column})")

        vals_str = ", ".join(f"'{v}'" for v in valid_values)
        default_val = valid_values[-1]
        op.execute(
            f"UPDATE {table} SET {column} = '{default_val}' "
            f"WHERE {column} IS NOT NULL AND {column} NOT IN ({vals_str})"
        )

        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} "
            f"CHECK (({column})::text = ANY (ARRAY[{vals_str}]))"
        )


def downgrade() -> None:
    for table, column, _ in COLUMN_ENUMS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS ck_{table}_{column}")
