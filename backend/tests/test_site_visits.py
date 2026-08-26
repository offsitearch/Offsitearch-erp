from datetime import date, timedelta

import pytest
from sqlalchemy import select
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User
from app.modules.projects.schemas import ProjectCreate
from app.modules.projects import service as project_service
from app.utils.enums import ProjectType

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

LEAD_EMAIL = "sv.lead@studioerp.dev"
LEAD_PASSWORD = "sv-lead-pass-123"
EMP_EMAIL = "sv.emp@studioerp.dev"
EMP_PASSWORD = "sv-emp-pass-123"


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


async def _create_user(email: str, password: str, name: str, level_code: str | None = None) -> User:
    async with AsyncSessionLocal() as db:
        level_id = None
        if level_code is not None:
            level_id = await db.scalar(select(OrgLevel.id).where(OrgLevel.code == level_code))
        user = User(
            email=email,
            name=name,
            org_level_id=level_id,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _create_project(lead_id: int, team: list | None = None) -> tuple[int, str]:
    async with AsyncSessionLocal() as db:
        project = await project_service.create_project(
            db,
            ProjectCreate(
                name="Site Visit Test Tower",
                project_type=ProjectType.COMMERCIAL,
                status="design",
                project_lead_id=lead_id,
                team=team or [],
            ),
        )
        return project.id, project.project_code


@pytest.fixture(scope="session")
async def sv_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Site Visit Lead", "L3")


@pytest.fixture(scope="session")
async def sv_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "Site Visit Employee")


async def test_site_visit_crud_and_pdf(sv_lead: User) -> None:
    project_id, project_code = await _create_project(sv_lead.id)
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/site-visits",
            headers=headers,
            json={
                "project_id": project_id,
                "visit_date": (date.today() + timedelta(days=2)).isoformat(),
                "purpose": "Structural inspection",
                "location": "Plot 12, Whitefield",
            },
        )
        assert response.status_code == 201, response.text
        visit = response.json()
        assert visit["status"] == "scheduled"
        assert visit["project_code"] == project_code

        response = await client.get(
            "/api/v1/site-visits", headers=headers, params={"project_id": project_id}
        )
        assert any(v["id"] == visit["id"] for v in response.json()["items"])

        response = await client.patch(
            f"/api/v1/site-visits/{visit['id']}",
            headers=headers,
            json={"status": "completed", "notes": "All clear"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["completed_at"] is not None

        response = await client.get(f"/api/v1/site-visits/{visit['id']}/report", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"

        response = await client.delete(f"/api/v1/site-visits/{visit['id']}", headers=headers)
        assert response.status_code == 200


async def test_site_visit_photo_upload(sv_lead: User) -> None:
    project_id, _ = await _create_project(sv_lead.id)
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post(
            "/api/v1/site-visits",
            headers=headers,
            json={
                "project_id": project_id,
                "visit_date": date.today().isoformat(),
                "purpose": "Photo test",
            },
        )
        assert created.status_code == 201
        visit_id = created.json()["id"]

        response = await client.post(
            f"/api/v1/site-visits/{visit_id}/photos",
            headers=headers,
            files={"file": ("site.jpg", b"\xff\xd8\xff\xe0\x00\x10fakejpeg", "image/jpeg")},
            data={"caption": "Corner detail"},
        )
        assert response.status_code == 201, response.text
        photo = response.json()
        assert photo["file_path"].startswith("site_visits/")
        assert photo["caption"] == "Corner detail"

        response = await client.get(
            f"/api/v1/site-visits/{visit_id}/photos/{photo['id']}", headers=headers
        )
        assert response.status_code == 200
        assert response.content == b"\xff\xd8\xff\xe0\x00\x10fakejpeg"

        response = await client.delete(f"/api/v1/site-visits/{visit_id}", headers=headers)
        assert response.status_code == 200


async def test_lead_cannot_create_visit_for_unled_project(sv_lead: User) -> None:
    async with AsyncSessionLocal() as db:
        project = await project_service.create_project(
            db,
            ProjectCreate(
                name="Unled Visit Project",
                project_type=ProjectType.COMMERCIAL,
                status="design",
            ),
        )
        project_id = project.id

    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/site-visits",
            headers=headers,
            json={"project_id": project_id, "visit_date": date.today().isoformat(), "purpose": "x"},
        )
        assert response.status_code == 403


async def test_site_visit_requires_lead(sv_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/site-visits",
            headers=headers,
            json={"project_id": 1, "visit_date": date.today().isoformat(), "purpose": "x"},
        )
        assert response.status_code == 403


async def test_employee_reads_project_visits_but_cannot_manage(
    sv_lead: User, sv_employee: User
) -> None:
    project_id, _ = await _create_project(
        sv_lead.id, team=[{"user_id": sv_employee.id, "role": "Draftsman"}]
    )
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        created = await client.post(
            "/api/v1/site-visits",
            headers={"Authorization": f"Bearer {lead_token}"},
            json={
                "project_id": project_id,
                "visit_date": date.today().isoformat(),
                "purpose": "Team review",
            },
        )
        assert created.status_code == 201
        visit_id = created.json()["id"]

        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/site-visits", headers=headers)
        assert response.status_code == 200
        assert any(v["id"] == visit_id for v in response.json()["items"])

        response = await client.get(f"/api/v1/site-visits/{visit_id}", headers=headers)
        assert response.status_code == 200

        response = await client.get(f"/api/v1/site-visits/{visit_id}/report", headers=headers)
        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"

        response = await client.post(
            f"/api/v1/site-visits/{visit_id}/photos",
            headers=headers,
            files={"file": ("site.jpg", b"not-a-photo", "image/jpeg")},
        )
        assert response.status_code == 403

        response = await client.patch(
            f"/api/v1/site-visits/{visit_id}", headers=headers, json={"notes": "edit"}
        )
        assert response.status_code == 403

        response = await client.delete(f"/api/v1/site-visits/{visit_id}", headers=headers)
        assert response.status_code == 403


async def test_employee_hidden_from_unrelated_project_visits(
    sv_lead: User, sv_employee: User
) -> None:
    project_id, _ = await _create_project(sv_lead.id)
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        created = await client.post(
            "/api/v1/site-visits",
            headers={"Authorization": f"Bearer {lead_token}"},
            json={
                "project_id": project_id,
                "visit_date": date.today().isoformat(),
                "purpose": "Closed",
            },
        )
        assert created.status_code == 201
        visit_id = created.json()["id"]

        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/site-visits", headers=headers)
        assert response.status_code == 200
        assert not any(v["id"] == visit_id for v in response.json()["items"])

        response = await client.get(f"/api/v1/site-visits/{visit_id}", headers=headers)
        assert response.status_code == 403
