"""deal_stage, follow-up fields on clients; per-phase studio fees

Revision ID: 0008_crm_pipeline_fees
Revises: 0007_reports_settings_comm
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_crm_pipeline_fees"
down_revision: Union[str, None] = "0007_reports_settings_comm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- clients: deal pipeline ---
    op.add_column(
        "clients",
        sa.Column("deal_stage", sa.String(30), nullable=False, server_default="lead"),
    )
    op.add_column(
        "clients",
        sa.Column("next_follow_up_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("next_follow_up_action", sa.String(120), nullable=True),
    )

    # --- project_phases: per-phase studio fee ---
    op.add_column(
        "project_phases",
        sa.Column("studio_fee", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_phases", "studio_fee")
    op.drop_column("clients", "next_follow_up_action")
    op.drop_column("clients", "next_follow_up_date")
    op.drop_column("clients", "deal_stage")
