import asyncio
from logging.config import fileConfig
from urllib.parse import urlsplit

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app import models  # noqa: F401  # registers all models on Base.metadata
from app.core.config import settings
from app.db.base import Base

config = context.config


def _log_db_target() -> None:
    """Print the connection target with credentials masked.

    Makes deploy-log failures like ``Name or service not known``
    self-explanatory: you can see exactly which host was used.
    """
    parts = urlsplit(settings.database_url)
    print(
        f"Connecting to DB host={parts.hostname!r} port={parts.port or 5432} "
        f"db={parts.path.lstrip('/')!r} user={parts.username!r}"
    )


if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_url() -> str:
    return settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg")


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from uuid import uuid4

    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Transaction-mode poolers (Supavisor :6543 / PgBouncer) don't
        # support shared prepared-statement names — use unique ones.
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda *_: f"__alembic_{uuid4().hex}__",
        },
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    _log_db_target()
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
