"""Add indexes on FK columns and fix cascade deletes.

Revision ID: 0011_add_indexes_fix_cascade
Revises: 0010_fix_enum_case
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_add_indexes_fix_cascade"
down_revision = "0010_fix_enum_case"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing indexes on FK columns
    indexes = [
        ("users", "department_id"),
        ("users", "reporting_to_id"),
        ("tasks", "phase_id"),
        ("tasks", "assigned_by"),
        ("tasks", "parent_task_id"),
        ("refresh_tokens", "user_id"),
        ("attendance", "user_id"),
        ("attendance", "marked_by"),
        ("client_communications", "user_id"),
        ("projects", "project_lead_id"),
        ("payroll_runs", "processed_by"),
        ("departments", "head_id"),
        ("notices", "created_by"),
        ("meetings", "organizer_id"),
        ("expenses", "approved_by"),
        ("clients", "referred_by"),
        ("leaves", "approved_by"),
        ("site_visits", "created_by"),
        ("site_visit_photos", "uploaded_by"),
        ("employee_documents", "uploaded_by"),
    ]
    for table, column in indexes:
        index_name = f"ix_{table}_{column}"
        op.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})")

    # Fix dangerous cascade: Client.projects should not cascade-delete
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_client_id_clients"
    )
    op.execute(
        "ALTER TABLE projects ADD CONSTRAINT fk_projects_client_id_clients "
        "FOREIGN KEY (client_id) REFERENCES clients(id)"
    )

    # Fix dangerous cascade: attendance.user_id should SET NULL, not CASCADE
    op.execute(
        "ALTER TABLE attendance DROP CONSTRAINT IF EXISTS fk_attendance_user_id_users"
    )
    op.execute(
        "ALTER TABLE attendance ALTER COLUMN user_id DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE attendance ADD CONSTRAINT fk_attendance_user_id_users "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # Revert attendance FK to CASCADE
    op.execute(
        "ALTER TABLE attendance DROP CONSTRAINT IF EXISTS fk_attendance_user_id_users"
    )
    op.execute(
        "ALTER TABLE attendance ADD CONSTRAINT fk_attendance_user_id_users "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
    )
    op.execute(
        "ALTER TABLE attendance ALTER COLUMN user_id SET NOT NULL"
    )

    # Revert Client.projects cascade
    op.execute(
        "ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_projects_client_id_clients"
    )
    op.execute(
        "ALTER TABLE projects ADD CONSTRAINT fk_projects_client_id_clients "
        "FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE"
    )

    # Drop indexes
    for table, column in indexes:
        index_name = f"ix_{table}_{column}"
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
