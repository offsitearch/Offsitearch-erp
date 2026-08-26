from datetime import date, timedelta

import pytest
from sqlalchemy import select
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

ADMIN_EMAIL = "cfg.admin@studioerp.dev"
ADMIN_PASSWORD = "cfg-admin-pass-123"
EMP_EMAIL = "cfg.emp@studioerp.dev"
EMP_PASSWORD = "cfg-emp-pass-123"
LEAD_EMAIL = "cfg.lead@studioerp.dev"
LEAD_PASSWORD = "cfg-lead-pass-123"


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
async def cfg_admin():
    return await _create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Config Admin", "L1")


@pytest.fixture(scope="session")
async def cfg_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "Config Employee")


@pytest.fixture(scope="session")
async def cfg_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Config Lead", "L3")


async def test_upsert_and_read_settings(cfg_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.put(
            "/api/v1/settings",
            headers=headers,
            json=[
                {
                    "group": "finance",
                    "key": "invoice_terms_days",
                    "value": {"days": 30},
                }
            ],
        )
        assert response.status_code == 200

        response = await client.get("/api/v1/settings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert any(
            s["group"] == "finance"
            and s["key"] == "invoice_terms_days"
            and s["value"] == {"days": 30}
            for s in data
        )


async def test_delete_setting(cfg_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        await client.put(
            "/api/v1/settings",
            headers=headers,
            json=[{"group": "attendance", "key": "temp_probe", "value": {"x": 1}}],
        )
        response = await client.delete("/api/v1/settings/attendance/temp_probe", headers=headers)
        assert response.status_code == 200
        response = await client.get("/api/v1/settings", headers=headers)
        assert not any(s["key"] == "temp_probe" for s in response.json())


async def test_settings_require_admin(cfg_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/settings", headers=headers)
        assert response.status_code == 403
        response = await client.put(
            "/api/v1/settings",
            headers=headers,
            json=[{"group": "attendance", "key": "x", "value": {}}],
        )
        assert response.status_code == 403


async def test_settings_lead_denied_persona(cfg_lead: User) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/settings", headers=headers)
        assert response.status_code == 403
        response = await client.put(
            "/api/v1/settings",
            headers=headers,
            json=[{"group": "attendance", "key": "x", "value": {}}],
        )
        assert response.status_code == 403


async def test_holiday_crud(cfg_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        future = (date.today() + timedelta(days=90)).isoformat()
        response = await client.post(
            "/api/v1/holidays",
            headers=headers,
            json={
                "name": "Test Holiday",
                "date": future,
                "is_recurring": True,
                "applicable_to": "all",
            },
        )
        assert response.status_code == 201, response.text
        holiday = response.json()
        assert holiday["is_recurring"] is True

        response = await client.patch(
            f"/api/v1/holidays/{holiday['id']}",
            headers=headers,
            json={"applicable_to": "field"},
        )
        assert response.status_code == 200
        assert response.json()["applicable_to"] == "field"

        response = await client.get("/api/v1/holidays", headers=headers)
        assert any(h["name"] == "Test Holiday" for h in response.json())

        response = await client.delete(f"/api/v1/holidays/{holiday['id']}", headers=headers)
        assert response.status_code == 200


async def test_holidays_require_admin(cfg_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/holidays", headers=headers)
        assert response.status_code == 403
