"""invoices, invoice_items, expenses, payroll_runs, payroll_entries, vendors, vendor_projects

Revision ID: 0006_finance_vendors_payroll
Revises: 0005_tasks_timesheets_documents
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_finance_vendors_payroll"
down_revision: Union[str, None] = "0005_tasks_timesheets_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)

_INVOICE_STATUSES = "('DRAFT','SENT','PARTIAL','PAID','OVERDUE','CANCELLED')"
_PAYMENT_METHODS = "('BANK_TRANSFER','UPI','CASH','CHEQUE','CARD')"
_EXPENSE_STATUSES = "('PENDING','APPROVED','REJECTED')"
_PAYROLL_STATUSES = "('DRAFT','PROCESSED')"
_VENDOR_CATEGORIES = (
    "('CONTRACTOR','MATERIAL_SUPPLIER','CONSULTANT','PRINTING','PHOTOGRAPHER','OTHER')"
)


def upgrade() -> None:
    # --- invoices ---
    op.create_table(
        "invoices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("invoice_number", sa.String(length=30), nullable=False),
        sa.Column("client_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("tax_percent", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("total", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="draft"),
        sa.Column("sent_at", _ts, nullable=True),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("payment_method", sa.String(length=15), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_number"),
    )
    op.create_foreign_key("fk_invoices_client", "invoices", "clients", ["client_id"], ["id"])
    op.create_foreign_key("fk_invoices_project", "invoices", "projects", ["project_id"], ["id"])
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"])
    op.create_index("ix_invoices_project_id", "invoices", ["project_id"])
    op.create_index("ix_invoices_status_due", "invoices", ["status", "due_date"])
    op.create_check_constraint("ck_invoices_status", "invoices", f"status IN {_INVOICE_STATUSES}")
    op.create_check_constraint(
        "ck_invoices_payment_method", "invoices", f"payment_method IN {_PAYMENT_METHODS}"
    )

    # --- invoice_items ---
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default=sa.text("1")),
        sa.Column("rate", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_invoice_items_invoice", "invoice_items", "invoices", ["invoice_id"], ["id"]
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])

    # --- expenses ---
    op.create_table(
        "expenses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=True),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("paid_by", sa.String(length=80), nullable=True),
        sa.Column("receipt_path", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="pending"),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", _ts, nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_expenses_project", "expenses", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_expenses_approver", "expenses", "users", ["approved_by"], ["id"])
    op.create_index("ix_expenses_project_id", "expenses", ["project_id"])
    op.create_index("ix_expenses_status", "expenses", ["status"])
    op.create_check_constraint("ck_expenses_status", "expenses", f"status IN {_EXPENSE_STATUSES}")

    # --- payroll_runs ---
    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("processed_by", sa.BigInteger(), nullable=True),
        sa.Column("processed_at", _ts, nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("month", "year", name="uq_payroll_month_year"),
    )
    op.create_foreign_key(
        "fk_payroll_runs_processor", "payroll_runs", "users", ["processed_by"], ["id"]
    )
    op.create_check_constraint(
        "ck_payroll_runs_status", "payroll_runs", f"status IN {_PAYROLL_STATUSES}"
    )

    # --- payroll_entries ---
    op.create_table(
        "payroll_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("payroll_run_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("working_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("gross_salary", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("deductions", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("net_pay", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("payslip_path", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_run_id", "user_id", name="uq_payroll_entry_user"),
    )
    op.create_foreign_key(
        "fk_payroll_entries_run", "payroll_entries", "payroll_runs", ["payroll_run_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_payroll_entries_user", "payroll_entries", "users", ["user_id"], ["id"]
    )
    op.create_index("ix_payroll_entries_run_id", "payroll_entries", ["payroll_run_id"])
    op.create_index("ix_payroll_entries_user_id", "payroll_entries", ["user_id"])

    # --- vendors ---
    op.create_table(
        "vendors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("contact_person", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("gst_number", sa.String(length=20), nullable=True),
        sa.Column("bank_details", sa.Text(), nullable=True),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint(
        "ck_vendors_category", "vendors", f"category IN {_VENDOR_CATEGORIES}"
    )
    op.create_index("ix_vendors_category", "vendors", ["category"])

    # --- vendor_projects ---
    op.create_table(
        "vendor_projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("vendor_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_vendor_projects_vendor", "vendor_projects", "vendors", ["vendor_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_vendor_projects_project", "vendor_projects", "projects", ["project_id"], ["id"]
    )
    op.create_index("ix_vendor_projects_vendor_id", "vendor_projects", ["vendor_id"])
    op.create_index("ix_vendor_projects_project_id", "vendor_projects", ["project_id"])


def downgrade() -> None:
    op.drop_table("vendor_projects")
    op.drop_table("vendors")
    op.drop_table("payroll_entries")
    op.drop_table("payroll_runs")
    op.drop_table("expenses")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
