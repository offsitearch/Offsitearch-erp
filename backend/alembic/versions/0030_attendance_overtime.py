"""add overtime_hours to attendance

Revision ID: 0030_attendance_overtime
Revises: 0029_timesheet_entry_location
Create Date: 2026-08-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_attendance_overtime"
down_revision: Union[str, None] = "0029_timesheet_entry_location"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance",
        sa.Column(
            "overtime_hours",
            sa.Numeric(5, 2),
            nullable=True,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("attendance", "overtime_hours")
