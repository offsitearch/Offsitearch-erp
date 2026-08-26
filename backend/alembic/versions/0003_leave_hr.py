"""leave, hr (documents, salary) tables

Revision ID: 0003_leave_hr
Revises: 0002_attendance
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_leave_hr"
down_revision: Union[str, None] = "0002_attendance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)

_LEAVE_TYPES = (
    "('CASUAL','SICK','EARNED','COMPENSATORY','MATERNITY','PATERNITY','WORK_FROM_HOME','UNPAID')"
)
_LEAVE_STATUSES = "('PENDING','APPROVED','REJECTED','CANCELLED')"


def upgrade() -> None:
    # --- leave_balance ---
    op.create_table(
        "leave_balance",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("leave_type", sa.String(length=20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("allocated", sa.Numeric(6, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("used", sa.Numeric(6, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "leave_type", "year", name="uq_leave_balance_user_type_year"
        ),
    )
    op.create_foreign_key("fk_leave_balance_user", "leave_balance", "users", ["user_id"], ["id"])
    op.create_index("ix_leave_balance_year", "leave_balance", ["year"])
    op.create_check_constraint(
        "ck_leave_balance_type", "leave_balance", f"leave_type IN {_LEAVE_TYPES}"
    )

    # --- leaves ---
    op.create_table(
        "leaves",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("leave_type", sa.String(length=20), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("total_days", sa.Numeric(6, 2), nullable=False),
        sa.Column("half_day_first", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("half_day_second", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("attachment", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", _ts, nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_leaves_user", "leaves", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_leaves_approved_by", "leaves", "users", ["approved_by"], ["id"])
    op.create_index("ix_leaves_user_id", "leaves", ["user_id"])
    op.create_index("ix_leaves_from_date", "leaves", ["from_date"])
    op.create_index("ix_leaves_user_status", "leaves", ["user_id", "status"])
    op.create_check_constraint("ck_leaves_type", "leaves", f"leave_type IN {_LEAVE_TYPES}")
    op.create_check_constraint("ck_leaves_status", "leaves", f"status IN {_LEAVE_STATUSES}")

    # --- employee_documents ---
    op.create_table(
        "employee_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("doc_type", sa.String(length=40), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_documents_user", "employee_documents", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "fk_documents_uploaded_by", "employee_documents", "users", ["uploaded_by"], ["id"]
    )
    op.create_index("ix_employee_documents_user_id", "employee_documents", ["user_id"])

    # --- salary_components ---
    op.create_table(
        "salary_components",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ctc_annual", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("basic", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("hra", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "special_allowance", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("pf_deduction", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("bank_name", sa.String(length=120), nullable=True),
        sa.Column("account_number", sa.String(length=30), nullable=True),
        sa.Column("ifsc_code", sa.String(length=15), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_salary_user"),
    )
    op.create_foreign_key("fk_salary_user", "salary_components", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_table("salary_components")
    op.drop_table("employee_documents")
    op.drop_table("leaves")
    op.drop_table("leave_balance")
