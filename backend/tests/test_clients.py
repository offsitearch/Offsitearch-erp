import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User
from app.modules.clients.schemas import ClientCreate
from app.modules.clients import service as client_service

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

ADMIN_EMAIL = "crm.admin@studioerp.dev"
ADMIN_PASSWORD = "crm-admin-pass-123"
EMP_EMAIL = "crm.emp@studioerp.dev"
EMP_PASSWORD = "crm-emp-pass-123"
LEAD_EMAIL = "crm.lead@studioerp.dev"
LEAD_PASSWORD = "crm-lead-pass-123"


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


@pytest.fixture(scope="session")
async def crm_admin():
    return await _create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "CRM Admin", "L1")


@pytest.fixture(scope="session")
async def crm_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "CRM Employee")


@pytest.fixture(scope="session")
async def crm_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "CRM Lead", "L3")


async def test_create_and_search_client(crm_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/v1/clients",
            json={
                "name": "Inventive Interiors Ltd",
                "client_type": "company",
                "email": "hello@inventive.in",
                "source": "referral",
            },
            headers=headers,
        )
        assert created.status_code == 201
        assert created.json()["client_type"] == "company"

        search = await client.get("/api/v1/clients?search=Inventive", headers=headers)
        assert search.status_code == 200
        assert search.json()["total"] >= 1
        assert search.json()["items"][0]["name"] == "Inventive Interiors Ltd"


async def test_client_profile_aggregates_projects(crm_admin: User) -> None:
    from app.modules.projects.schemas import ProjectCreate
    from app.modules.projects import service as project_service
    from app.utils.enums import ProjectType

    async with AsyncSessionLocal() as db:
        client = await client_service.create_client(db, ClientCreate(name="Aggregate Client"))
        client_id = client.id

    async with AsyncSessionLocal() as db:
        await project_service.create_project(
            db,
            ProjectCreate(
                name="Aggregate Project",
                project_type=ProjectType.INTERIOR,
                client_id=client_id,
                budget=10000000,
                studio_fee=900000,
            ),
        )

    async with _client() as client_api:
        token = await _login(client_api, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        profile = await client_api.get(f"/api/v1/clients/{client_id}", headers=headers)
        assert profile.status_code == 200
        body = profile.json()
        assert len(body["projects"]) == 1
        assert body["financial_summary"]["total_projects"] == 1
        assert float(body["financial_summary"]["total_budget"]) == 10000000.0
        assert float(body["financial_summary"]["total_studio_fee"]) == 900000.0
        assert float(body["financial_summary"]["invoiced"]) == 0.0


async def test_communications_log(crm_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        new_client = await client.post(
            "/api/v1/clients",
            json={"name": "Comms Client", "client_type": "individual"},
            headers=headers,
        )
        client_id = new_client.json()["id"]

        added = await client.post(
            f"/api/v1/clients/{client_id}/communications",
            json={"type": "email", "subject": "Proposal follow-up", "notes": "Sent rev 2"},
            headers=headers,
        )
        assert added.status_code == 201
        assert added.json()["user_name"] == "CRM Admin"

        listing = await client.get(f"/api/v1/clients/{client_id}/communications", headers=headers)
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["type"] == "email"


async def test_client_update_and_delete_permissions(
    crm_admin: User, crm_employee: User, crm_lead: User
) -> None:
    async with _client() as client:
        admin_token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        new_client = await client.post(
            "/api/v1/clients",
            json={"name": "Permission Client", "client_type": "individual"},
            headers=admin_headers,
        )
        client_id = new_client.json()["id"]

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        forbidden = await client.patch(
            f"/api/v1/clients/{client_id}", json={"name": "Hacked"}, headers=emp_headers
        )
        assert forbidden.status_code == 403

        # Client deletion stays executive-only: the L3 lead is denied,
        # the L1 CRM admin may delete.
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        lead_denied = await client.delete(f"/api/v1/clients/{client_id}", headers=lead_headers)
        assert lead_denied.status_code == 403

        deleted = await client.delete(f"/api/v1/clients/{client_id}", headers=admin_headers)
        assert deleted.status_code == 204

        gone = await client.get(f"/api/v1/clients/{client_id}", headers=admin_headers)
        assert gone.status_code == 404


async def test_employee_blocked_from_clients_module(crm_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        # CRM reads and writes are both L3+ (2026-08-24 hardening).
        listing = await client.get("/api/v1/clients", headers=headers)
        assert listing.status_code == 403

        created = await client.post(
            "/api/v1/clients",
            json={"name": "Should Fail", "client_type": "individual"},
            headers=headers,
        )
        assert created.status_code == 403

        profile = await client.get("/api/v1/clients/1", headers=headers)
        assert profile.status_code == 403


async def test_lead_can_create_and_update_clients(crm_lead: User) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/v1/clients",
            json={"name": "Lead Onboarded", "client_type": "company", "email": "lead@client.in"},
            headers=headers,
        )
        assert created.status_code == 201
        client_id = created.json()["id"]

        updated = await client.patch(
            f"/api/v1/clients/{client_id}",
            json={"contact_person": "Mr. Lead Contact"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["contact_person"] == "Mr. Lead Contact"

        deleted = await client.delete(f"/api/v1/clients/{client_id}", headers=headers)
        assert deleted.status_code == 403
