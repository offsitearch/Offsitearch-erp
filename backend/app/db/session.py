from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _is_external_pooler(url: str) -> bool:
    """Detect Supavisor / PgBouncer pooler URLs.

    When an external pooler already manages connections, SQLAlchemy's
    built-in pool causes double-pooling and prepared-statement conflicts.
    Use NullPool to hand connection lifecycle to the pooler.
    """
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return "pooler.supabase.com" in host or "pgbouncer" in host


_use_null_pool = settings.environment == "test" or _is_external_pooler(settings.database_url)

_engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
    "connect_args": {
        "statement_cache_size": 0,
    },
}
if _use_null_pool:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10
    _engine_kwargs["pool_timeout"] = 30
    _engine_kwargs["pool_recycle"] = 1800

engine = create_async_engine(settings.database_url, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
