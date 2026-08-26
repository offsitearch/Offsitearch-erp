"""attendance & holidays tables

Revision ID: 0002_attendance
Revises: 0001_initial
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_attendance"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    # --- attendance ---
    op.create_table(
        "attendance",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in_time", _ts, nullable=True),
        sa.Column("check_out_time", _ts, nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="present"),
        sa.Column("late_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("check_in_method", sa.String(length=20), nullable=False, server_default="web"),
        sa.Column("check_in_location", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("marked_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )
    op.create_foreign_key("fk_attendance_user", "attendance", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_attendance_marked_by", "attendance", "users", ["marked_by"], ["id"])
    op.create_index("ix_attendance_date", "attendance", ["date"])
    op.create_index("ix_attendance_status_date", "attendance", ["status", "date"])
    op.create_check_constraint(
        "ck_attendance_status",
        "attendance",
        "status IN ('PRESENT','ABSENT','LATE','HALF_DAY','WORK_FROM_HOME','ON_LEAVE')",
    )
    op.create_check_constraint(
        "ck_attendance_method",
        "attendance",
        "check_in_method IN ('WEB','MANUAL','QR','GPS','IP')",
    )

    # --- holidays ---
    op.create_table(
        "holidays",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("applicable_to", sa.String(length=40), nullable=False, server_default="all"),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_holidays_date", "holidays", ["date"], unique=True)


def downgrade() -> None:
    op.drop_table("holidays")
    op.drop_table("attendance")
