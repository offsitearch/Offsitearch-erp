import asyncio
import os
from pathlib import Path

import pytest

TEST_DB = "studio_erp_test"
BACKEND_DIR = Path(__file__).resolve().parent.parent

BASE_URL = os.environ.get("DATABASE_URL")
if not BASE_URL:
    raise RuntimeError("DATABASE_URL env var is required to run tests")

# Windows resolves `localhost` to ::1 first; if Postgres only listens on
# IPv4 every new connection stalls ~2s before falling back to 127.0.0.1.
# Tests use NullPool (fresh connection per request), so that stall would
# be paid on every single request.
BASE_URL = BASE_URL.replace("://localhost:", "://127.0.0.1:")


def _switch_db(url: str, dbname: str) -> str:
    head, _ = url.rsplit("/", 1)
    return f"{head}/{dbname}"


# Must be set before any `app.*` import so the module-level async engine
# binds to the test database and uses NullPool (no cross-event-loop pooling).
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = _switch_db(BASE_URL, TEST_DB)
os.environ.setdefault("LOGIN_MAX_ATTEMPTS", "10000")


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.core.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(scope="session", autouse=True)
def database_setup():
    import asyncpg

    base_dsn = "postgresql://" + BASE_URL.split("://", 1)[1]

    async def prepare() -> None:
        conn = await asyncpg.connect(base_dsn)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
            await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
        finally:
            await conn.close()

    async def cleanup() -> None:
        conn = await asyncpg.connect(base_dsn)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        finally:
            await conn.close()

    asyncio.run(prepare())

    from alembic import command
    from alembic.config import Config

    from app.db.init_db import init_db

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    asyncio.run(init_db())

    yield

    asyncio.run(cleanup())
