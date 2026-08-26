"""add location to timesheet_entries

Revision ID: 0029_timesheet_entry_location
Revises: 0028_timesheet_daily_flow
Create Date: 2026-08-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_timesheet_entry_location"
down_revision: Union[str, None] = "0028_timesheet_daily_flow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "timesheet_entries",
        sa.Column("location", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("timesheet_entries", "location")
