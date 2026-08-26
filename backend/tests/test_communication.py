from datetime import date, datetime, timedelta, timezone

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

ADMIN_EMAIL = "comm.admin@studioerp.dev"
ADMIN_PASSWORD = "comm-admin-pass-123"
LEAD_EMAIL = "comm.lead@studioerp.dev"
LEAD_PASSWORD = "comm-lead-pass-123"
EMP_EMAIL = "comm.emp@studioerp.dev"
EMP_PASSWORD = "comm-emp-pass-123"


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
async def comm_admin():
    return await _create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Comm Admin", "L1")


@pytest.fixture(scope="session")
async def comm_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Comm Lead", "L3")


@pytest.fixture(scope="session")
async def comm_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "Comm Employee")


async def test_notice_create_and_publish_gating(comm_admin: User, comm_employee: User) -> None:
    async with _client() as client:
        admin_token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        future = (date.today() + timedelta(days=7)).isoformat()
        response = await client.post(
            "/api/v1/notices",
            headers=admin_headers,
            json={
                "title": "Policy update",
                "body": "New expense policy from next month.",
                "importance": "high",
                "is_pinned": True,
                "publish_date": date.today().isoformat(),
                "expiry_date": future,
            },
        )
        assert response.status_code == 201, response.text
        notice = response.json()
        assert notice["is_active"] is True

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        response = await client.get("/api/v1/notices", headers=emp_headers)
        assert response.status_code == 200
        assert any(n["title"] == "Policy update" for n in response.json()["items"])

        response = await client.patch(
            f"/api/v1/notices/{notice['id']}", headers=emp_headers, json={"is_active": False}
        )
        assert response.status_code == 403

        response = await client.patch(
            f"/api/v1/notices/{notice['id']}",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False


async def test_notice_future_publish_hidden_from_employees(
    comm_admin: User, comm_employee: User
) -> None:
    async with _client() as client:
        admin_token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {admin_token}"}
        future = (date.today() + timedelta(days=30)).isoformat()
        response = await client.post(
            "/api/v1/notices",
            headers=headers,
            json={
                "title": "Future notice",
                "publish_date": future,
                "expiry_date": (date.today() + timedelta(days=60)).isoformat(),
            },
        )
        assert response.status_code == 201
        notice_id = response.json()["id"]

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        response = await client.get("/api/v1/notices", headers=emp_headers)
        assert not any(n["id"] == notice_id for n in response.json()["items"])

        response = await client.get("/api/v1/notices?include_inactive=true", headers=emp_headers)
        assert not any(n["id"] == notice_id for n in response.json()["items"])


async def test_meeting_create_invite_notify_and_rsvp(comm_lead: User, comm_employee: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = await client.post(
            "/api/v1/meetings",
            headers=lead_headers,
            json={
                "title": "Client review",
                "meeting_type": "client",
                "scheduled_at": when,
                "duration_minutes": 45,
                "attendee_ids": [comm_employee.id],
            },
        )
        assert response.status_code == 201, response.text
        meeting = response.json()
        assert len(meeting["attendees"]) == 1
        assert meeting["attendees"][0]["user_id"] == comm_employee.id

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        response = await client.get("/api/v1/notifications", headers=emp_headers)
        assert any(
            n["type"] == "meeting" and n["link"] == f"/meetings/{meeting['id']}"
            for n in response.json()["items"]
        )

        response = await client.post(
            f"/api/v1/meetings/{meeting['id']}/rsvp?rsvp_status=accepted",
            headers=emp_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == "accepted"

        response = await client.get("/api/v1/meetings", headers=emp_headers)
        assert any(
            m["id"] == meeting["id"] and m["my_rsvp"] == "accepted"
            for m in response.json()["items"]
        )


async def test_meeting_requires_lead(comm_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/meetings",
            headers=headers,
            json={
                "title": "Should fail",
                "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 403


async def test_notifications_workflow(comm_lead: User, comm_employee: User) -> None:
    async with _client() as client:
        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        response = await client.get("/api/v1/notifications/unread-count", headers=emp_headers)
        assert response.status_code == 200
        unread_before = response.json()["count"]

        items = (await client.get("/api/v1/notifications", headers=emp_headers)).json()["items"]
        unread_ids = [n["id"] for n in items if n["read_at"] is None]

        response = await client.post("/api/v1/notifications/read-all", headers=emp_headers)
        assert response.status_code == 200
        response = await client.get("/api/v1/notifications/unread-count", headers=emp_headers)
        assert response.json()["count"] == 0

        if unread_ids:
            assert unread_before > 0
        else:
            assert unread_before == 0
