"""Add the L0 CEO org level above L1.

L0 (CEO) becomes the most senior organizational level. Authorization
ranks are canonical in app.utils.shared.LEVEL_RANK; this migration only
seeds the reference row and adjusts the L1 description.

Revision ID: 0023_add_l0_ceo
Revises: 0022_rename_org_levels
Create Date: 2026-08-22
"""
from alembic import op


revision = "0023_add_l0_ceo"
down_revision = "0022_rename_org_levels"
branch_labels = None
depends_on = None

_L0 = ("L0", "CEO", "Chief Executive Officer - founder/owner; highest authority")
_L1_DESC = "Studio Director - a single director; executive authority"
_OLD_L1_DESC = "Studio Director - a single director; highest authority"


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO org_levels (code, name, description, rank)
        SELECT '{_L0[0]}', '{_L0[1]}', '{_L0[2]}', 0
        WHERE NOT EXISTS (SELECT 1 FROM org_levels WHERE code = '{_L0[0]}')
        """
    )
    op.execute(
        f"UPDATE org_levels SET description = '{_L1_DESC}' "
        f"WHERE code = 'L1' AND description = '{_OLD_L1_DESC}'"
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET org_level_id = NULL
        WHERE org_level_id IN (SELECT id FROM org_levels WHERE code = 'L0')
        """
    )
    op.execute("DELETE FROM org_levels WHERE code = 'L0'")
    op.execute(
        f"UPDATE org_levels SET description = '{_OLD_L1_DESC}' "
        f"WHERE code = 'L1' AND description = '{_L1_DESC}'"
    )
