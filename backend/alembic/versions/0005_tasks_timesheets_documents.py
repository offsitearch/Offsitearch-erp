"""tasks, task_checklist, timesheets, timesheet_entries, document_folders, documents, document_versions

Revision ID: 0005_tasks_timesheets_documents
Revises: 0004_projects_clients
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_tasks_timesheets_documents"
down_revision: Union[str, None] = "0004_projects_clients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)

_TASK_PRIORITIES = "('LOW','MEDIUM','HIGH','URGENT')"
_TASK_STATUSES = "('TODO','IN_PROGRESS','REVIEW','DONE','BLOCKED')"
_TIMESHEET_STATUSES = "('DRAFT','SUBMITTED','APPROVED','REJECTED')"


def upgrade() -> None:
    # --- projects: add hours_logged KPI column ---
    op.add_column(
        "projects",
        sa.Column("hours_logged", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
    )

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("phase_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("assigned_by", sa.BigInteger(), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="todo"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("parent_task_id", sa.BigInteger(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String(length=40)), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_tasks_project", "tasks", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_tasks_phase", "tasks", "project_phases", ["phase_id"], ["id"])
    op.create_foreign_key("fk_tasks_assignee", "tasks", "users", ["assigned_to"], ["id"])
    op.create_foreign_key("fk_tasks_assigned_by", "tasks", "users", ["assigned_by"], ["id"])
    op.create_foreign_key("fk_tasks_parent", "tasks", "tasks", ["parent_task_id"], ["id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_check_constraint("ck_tasks_priority", "tasks", f"priority IN {_TASK_PRIORITIES}")
    op.create_check_constraint("ck_tasks_status", "tasks", f"status IN {_TASK_STATUSES}")

    # --- task_checklist ---
    op.create_table(
        "task_checklist",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_checklist_task", "task_checklist", "tasks", ["task_id"], ["id"])
    op.create_index("ix_task_checklist_task_id", "task_checklist", ["task_id"])

    # --- timesheets ---
    op.create_table(
        "timesheets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="draft"),
        sa.Column("submitted_at", _ts, nullable=True),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", _ts, nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_start", name="uq_timesheet_week"),
    )
    op.create_foreign_key("fk_timesheets_user", "timesheets", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_timesheets_approver", "timesheets", "users", ["approved_by"], ["id"])
    op.create_index("ix_timesheets_user_id", "timesheets", ["user_id"])
    op.create_check_constraint(
        "ck_timesheets_status", "timesheets", f"status IN {_TIMESHEET_STATUSES}"
    )

    # --- timesheet_entries ---
    op.create_table(
        "timesheet_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("timesheet_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("task_id", sa.BigInteger(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(4, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_entries_timesheet", "timesheet_entries", "timesheets", ["timesheet_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_entries_project", "timesheet_entries", "projects", ["project_id"], ["id"]
    )
    op.create_foreign_key("fk_entries_task", "timesheet_entries", "tasks", ["task_id"], ["id"])
    op.create_index("ix_timesheet_entries_timesheet_id", "timesheet_entries", ["timesheet_id"])

    # --- document_folders ---
    op.create_table(
        "document_folders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_folders_parent", "document_folders", "document_folders", ["parent_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_folders_project", "document_folders", "projects", ["project_id"], ["id"]
    )
    op.create_index("ix_document_folders_project_id", "document_folders", ["project_id"])

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("folder_id", sa.BigInteger(), nullable=True),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("phase_id", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String(length=40)), nullable=True),
        sa.Column("access_level", sa.String(length=20), nullable=False, server_default="team"),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "shared_with_client", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_documents_folder", "documents", "document_folders", ["folder_id"], ["id"]
    )
    op.create_foreign_key("fk_documents_project", "documents", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_documents_phase", "documents", "project_phases", ["phase_id"], ["id"])
    op.create_foreign_key("fk_documents_uploader", "documents", "users", ["uploaded_by"], ["id"])
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])

    # --- document_versions ---
    op.create_table(
        "document_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_at", _ts, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_versions_document", "document_versions", "documents", ["document_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_versions_uploader", "document_versions", "users", ["uploaded_by"], ["id"]
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("document_folders")
    op.drop_table("timesheet_entries")
    op.drop_table("timesheets")
    op.drop_table("task_checklist")
    op.drop_table("tasks")
    op.drop_column("projects", "hours_logged")
