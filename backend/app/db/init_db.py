from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.seeds.data import (
    seed_clients,
    seed_departments,
    seed_holidays,
    seed_org_levels,
    seed_projects,
    seed_settings,
    seed_superuser,
)


async def init_db() -> None:
    """Idempotent seeding of reference data. Runs on app startup."""
    async with AsyncSessionLocal() as db:
        await seed_org_levels(db)
        await seed_departments(db)
        await seed_settings(db)
        await seed_holidays(db)
        await seed_superuser(db)
        if settings.seed_demo:
            from app.seeds.demo import seed_demo

            await seed_clients(db)
            await seed_projects(db)
            await seed_demo(db)
