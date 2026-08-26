"""projects, project_team, project_phases, clients, client_communications tables

Revision ID: 0004_projects_clients
Revises: 0003_leave_hr
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_projects_clients"
down_revision: Union[str, None] = "0003_leave_hr"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)

_PROJECT_TYPES = (
    "('RESIDENTIAL','COMMERCIAL','INTERIOR','INSTITUTIONAL','LANDSCAPE',"
    "'URBAN_PLANNING','RENOVATION','MIXED_USE')"
)
_PROJECT_STATUSES = (
    "('DRAFT','CONCEPT','DESIGN','UNDER_REVIEW','IN_CONSTRUCTION','COMPLETED',"
    "'ON_HOLD','CANCELLED')"
)
_PHASE_STATUSES = "('NOT_STARTED','IN_PROGRESS','COMPLETED','DELAYED')"
_CLIENT_TYPES = "('INDIVIDUAL','COMPANY','DEVELOPER','GOVERNMENT')"
_COMMS_TYPES = "('CALL','EMAIL','MEETING','SITE_VISIT')"


def upgrade() -> None:
    # --- clients ---
    op.create_table(
        "clients",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("client_type", sa.String(length=20), nullable=False, server_default="individual"),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("contact_person", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("phone_secondary", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("gst_number", sa.String(length=20), nullable=True),
        sa.Column("pan_number", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
        sa.Column("budget_range", sa.String(length=40), nullable=True),
        sa.Column("interest", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_clients_referred_by", "clients", "clients", ["referred_by"], ["id"])
    op.create_index("ix_clients_name", "clients", ["name"])
    op.create_check_constraint("ck_clients_type", "clients", f"client_type IN {_CLIENT_TYPES}")

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_type", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("client_id", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("plot_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("built_up_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("no_of_floors", sa.String(length=20), nullable=True),
        sa.Column("coordinates", sa.String(length=80), nullable=True),
        sa.Column("budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("studio_fee", sa.Numeric(14, 2), nullable=True),
        sa.Column("fee_type", sa.String(length=20), nullable=True),
        sa.Column("fee_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("project_lead_id", sa.BigInteger(), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="medium"),
        sa.Column("progress_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_code", name="uq_projects_code"),
    )
    op.create_foreign_key("fk_projects_client", "projects", "clients", ["client_id"], ["id"])
    op.create_foreign_key("fk_projects_lead", "projects", "users", ["project_lead_id"], ["id"])
    op.create_index("ix_projects_project_code", "projects", ["project_code"], unique=True)
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_client_id", "projects", ["client_id"])
    op.create_check_constraint("ck_projects_type", "projects", f"project_type IN {_PROJECT_TYPES}")
    op.create_check_constraint("ck_projects_status", "projects", f"status IN {_PROJECT_STATUSES}")

    # --- project_team ---
    op.create_table(
        "project_team",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_team_member"),
    )
    op.create_foreign_key("fk_team_project", "project_team", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_team_user", "project_team", "users", ["user_id"], ["id"])
    op.create_index("ix_project_team_project_id", "project_team", ["project_id"])
    op.create_index("ix_project_team_user_id", "project_team", ["user_id"])

    # --- project_phases ---
    op.create_table(
        "project_phases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="not_started"),
        sa.Column("completion_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_phases_project", "project_phases", "projects", ["project_id"], ["id"])
    op.create_index("ix_project_phases_project_id", "project_phases", ["project_id"])
    op.create_check_constraint("ck_phases_status", "project_phases", f"status IN {_PHASE_STATUSES}")

    # --- client_communications ---
    op.create_table(
        "client_communications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", _ts, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_comms_client", "client_communications", "clients", ["client_id"], ["id"]
    )
    op.create_foreign_key("fk_comms_user", "client_communications", "users", ["user_id"], ["id"])
    op.create_index("ix_client_communications_client_id", "client_communications", ["client_id"])
    op.create_check_constraint("ck_comms_type", "client_communications", f"type IN {_COMMS_TYPES}")


def downgrade() -> None:
    op.drop_table("client_communications")
    op.drop_table("project_phases")
    op.drop_table("project_team")
    op.drop_table("projects")
    op.drop_table("clients")
