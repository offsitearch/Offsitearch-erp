import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import User
from app.modules.projects.schemas import ProjectCreate
from app.modules.projects import service as project_service
from app.utils.enums import ProjectType

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

DASH_EMP_EMAIL = "dash.emp@studioerp.dev"
DASH_EMP_PASSWORD = "dash-emp-pass-123"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login(client: AsyncClient, email: str, password: str) -> str:
    from sqlalchemy import select as _select

    from app.db.session import AsyncSessionLocal as _DB
    from app.models import User as _User

    async with _DB() as db:
        user_id = await db.scalar(_select(_User.login_id).where(_User.email == email))
    assert user_id is not None, f"no user with email {email}"
    response = await client.post(
        "/api/v1/auth/login", json={"user_id": user_id, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="session")
async def dash_emp():
    async with AsyncSessionLocal() as db:
        user = User(
            email=DASH_EMP_EMAIL,
            name="Dashboard Employee",
            password_hash=hash_password(DASH_EMP_PASSWORD),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def test_summary_admin_sees_counts_and_revenue() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        body = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
        assert body["total_employees"] >= 1
        assert body["present_today"] >= 0
        assert body["active_projects"] >= 0
        assert body["pending_tasks"] >= 0
        assert body["revenue_this_month"] is not None


async def test_summary_employee_is_scoped_and_hides_money(dash_emp: User) -> None:
    async with _client() as client:
        token = await _login(client, DASH_EMP_EMAIL, DASH_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        before = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
        assert before["revenue_this_month"] is None

        async with AsyncSessionLocal() as db:
            await project_service.create_project(
                db,
                ProjectCreate(
                    name="Scoped Dashboard Project",
                    project_type=ProjectType.RESIDENTIAL,
                    status="draft",
                    team=[{"user_id": dash_emp.id, "role": "Draftsman"}],
                ),
            )

        after = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
        assert after["active_projects"] == before["active_projects"] + 1
        assert after["pending_tasks"] == before["pending_tasks"]
        assert after["revenue_this_month"] is None
