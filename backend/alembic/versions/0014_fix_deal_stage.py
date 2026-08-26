"""Fix deal_stage: normalize to lowercase + add CHECK constraint.

Revision ID: 0014_fix_deal_stage
Revises: 0013_fix_constraint_names
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_fix_deal_stage"
down_revision = "0013_fix_constraint_names"
branch_labels = None
depends_on = None

VALID_VALUES = ["lead", "proposal", "negotiation", "won", "lost"]


def upgrade() -> None:
    conn = op.get_bind()

    # Drop any existing check constraint on clients.deal_stage
    result = conn.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'clients'::regclass AND contype = 'c' "
            "AND pg_get_constraintdef(oid) LIKE '%deal_stage%'"
        ),
    )
    for row in result:
        op.execute(f"ALTER TABLE clients DROP CONSTRAINT IF EXISTS {row[0]}")

    # Normalize data to lowercase
    op.execute("UPDATE clients SET deal_stage = LOWER(deal_stage)")

    # Fix rogue values
    vals_str = ", ".join(f"'{v}'" for v in VALID_VALUES)
    default_val = VALID_VALUES[-1]
    op.execute(
        f"UPDATE clients SET deal_stage = '{default_val}' "
        f"WHERE deal_stage IS NOT NULL AND deal_stage NOT IN ({vals_str})"
    )

    # Add CHECK constraint
    op.execute(
        f"ALTER TABLE clients ADD CONSTRAINT ck_clients_deal_stage "
        f"CHECK ((deal_stage)::text = ANY (ARRAY[{vals_str}]))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE clients DROP CONSTRAINT IF EXISTS ck_clients_deal_stage")
