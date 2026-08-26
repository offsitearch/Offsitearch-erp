"""Timesheet daily flow: per-day approval rows.

New ``timesheet_days`` table: one approval state (draft/submitted/
approved/rejected) per weekly sheet × day, enabling single-day
submission and review alongside bulk week actions.

Backfills day rows for any existing entries, copying the parent
sheet's status so aggregates stay consistent.

Revision ID: 0028_timesheet_daily_flow
Revises: 0027_timesheets_module
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0028_timesheet_daily_flow"
down_revision = "0027_timesheets_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timesheet_days",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "timesheet_id",
            sa.Integer(),
            sa.ForeignKey("timesheets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint("timesheet_id", "date", name="uq_timesheet_days_sheet_date"),
        sa.CheckConstraint(
            "status IN ('draft','submitted','approved','rejected')",
            name="ck_timesheet_days_status",
        ),
    )
    op.create_index("ix_timesheet_days_status", "timesheet_days", ["status"])

    # Backfill: a day row for every date that already has entries; the day
    # inherits its sheet's status so the aggregate stays truthful.
    op.execute(
        """
        INSERT INTO timesheet_days (timesheet_id, date, status)
        SELECT DISTINCT te.timesheet_id, te.date, t.status::text
        FROM timesheet_entries te
        JOIN timesheets t ON t.id = te.timesheet_id
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_timesheet_days_status", table_name="timesheet_days")
    op.drop_table("timesheet_days")
