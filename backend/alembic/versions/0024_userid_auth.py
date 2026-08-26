"""User-ID based authentication.

Adds:
- users.login_id: 6-digit immutable login identifier, ``YY####`` where
  ``YY`` is the two-digit year of joining (fallback: creation year) and
  ``####`` is a zero-padded per-year sequence (260001, 260002, ...).
- users.must_change_password: forces a password change at next login
  (set on registration and whenever an executive assigns/resets a password).
- users.token_version: bumped on every password event; embedded in JWTs so
  password changes instantly invalidate outstanding tokens.

Drops:
- users.password_plain: plaintext password storage is removed for good;
  passwords exist only as bcrypt hashes and generated values are shown
  exactly once in the create/regenerate responses.

Revision ID: 0024_userid_auth
Revises: 0023_add_l0_ceo
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa


revision = "0024_userid_auth"
down_revision = "0023_add_l0_ceo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("login_id", sa.String(6), nullable=True))
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )

    # Backfill: order by joining year (fallback created year), then id, and
    # number each year's cohort starting from 000001.
    op.execute(
        """
        WITH ranked AS (
            SELECT u.id,
                   LPAD(
                       (COALESCE(EXTRACT(YEAR FROM u.date_of_joining),
                                 EXTRACT(YEAR FROM u.created_at))::int % 100)::text,
                       2, '0'
                   ) AS yy,
                   ROW_NUMBER() OVER (
                       PARTITION BY COALESCE(EXTRACT(YEAR FROM u.date_of_joining),
                                             EXTRACT(YEAR FROM u.created_at))::int
                       ORDER BY u.id
                   )::text AS rn
            FROM users u
        )
        UPDATE users
        SET login_id = ranked.yy || LPAD(ranked.rn, 4, '0')
        FROM ranked
        WHERE ranked.id = users.id AND ranked.rn::int <= 9999
        """
    )
    # Extremely defensive fallback for cohorts beyond 9999 members.
    op.execute("UPDATE users SET login_id = LPAD(id::text, 6, '9') WHERE login_id IS NULL")

    op.alter_column("users", "login_id", existing_type=sa.String(6), nullable=False)
    op.create_unique_constraint("uq_users_login_id", "users", ["login_id"])
    op.create_index("ix_users_login_id", "users", ["login_id"], unique=True)

    # Safety net: rows inserted without an explicit login_id (direct ORM
    # constructions in seeds/tools/tests) get a unique 6-digit identifier
    # derived from the primary key. Application code always allocates a
    # proper YY#### id beforehand; this only guarantees NOT NULL/uniqueness.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION assign_user_login_id() RETURNS trigger AS $$
        BEGIN
            IF NEW.login_id IS NULL THEN
                NEW.login_id := LPAD((NEW.id % 1000000)::text, 6, '0');
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_users_assign_login_id BEFORE INSERT ON users "
        "FOR EACH ROW EXECUTE FUNCTION assign_user_login_id()"
    )

    op.drop_column("users", "password_plain")


def downgrade() -> None:
    op.add_column("users", sa.Column("password_plain", sa.String(128), nullable=True))
    op.execute("DROP TRIGGER IF EXISTS trg_users_assign_login_id ON users")
    op.execute("DROP FUNCTION IF EXISTS assign_user_login_id()")
    op.drop_index("ix_users_login_id", table_name="users")
    op.drop_constraint("uq_users_login_id", "users", type_="unique")
    op.drop_column("users", "token_version")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "login_id")
