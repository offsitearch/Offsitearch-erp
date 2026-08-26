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

ADMIN_EMAIL = "meet.admin@studioerp.dev"
ADMIN_PASSWORD = "meet-admin-pass-123"
LEAD_EMAIL = "meet.lead@studioerp.dev"
LEAD_PASSWORD = "meet-lead-pass-123"
LEAD2_EMAIL = "meet.lead2@studioerp.dev"
LEAD2_PASSWORD = "meet-lead2-pass-123"
EMP_EMAIL = "meet.emp@studioerp.dev"
EMP_PASSWORD = "meet-emp-pass-123"
EMP2_EMAIL = "meet.emp2@studioerp.dev"
EMP2_PASSWORD = "meet-emp2-pass-123"


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
async def meet_admin():
    return await _create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Meeting Admin", "L1")


@pytest.fixture(scope="session")
async def meet_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Meeting Lead", "L3")


@pytest.fixture(scope="session")
async def meet_lead2():
    return await _create_user(LEAD2_EMAIL, LEAD2_PASSWORD, "Meeting Lead 2", "L3")


@pytest.fixture(scope="session")
async def meet_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "Meeting Employee")


@pytest.fixture(scope="session")
async def meet_employee2():
    return await _create_user(EMP2_EMAIL, EMP2_PASSWORD, "Meeting Employee 2")


async def _create_meeting(
    client: AsyncClient, headers: dict, title: str, attendee_ids: list[int]
) -> dict:
    response = await client.post(
        "/api/v1/meetings",
        headers=headers,
        json={
            "title": title,
            "meeting_type": "internal",
            "scheduled_at": "2026-08-20T10:00:00Z",
            "duration_minutes": 45,
            "location": "Studio",
            "attendee_ids": attendee_ids,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_lead_lists_users_and_creates_meeting(meet_lead: User, meet_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        users = await client.get("/api/v1/users?active_only=true", headers=headers)
        assert users.status_code == 200
        assert any(u["email"] == EMP_EMAIL for u in users.json())

        meeting = await _create_meeting(client, headers, "Weekly studio sync", [meet_employee.id])
        assert meeting["organizer_name"] == "Meeting Lead"
        assert any(a["user_id"] == meet_employee.id for a in meeting["attendees"])
        assert meeting["my_rsvp"] is None


async def test_employee_sees_only_invited_meetings(
    meet_lead: User, meet_employee: User, meet_employee2: User
) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}

        await _create_meeting(client, lead_headers, "Design review", [meet_employee.id])
        await _create_meeting(client, lead_headers, "Private catch-up", [meet_employee2.id])

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        listing = await client.get("/api/v1/meetings", headers=emp_headers)
        assert listing.status_code == 200
        titles = [m["title"] for m in listing.json()["items"]]
        assert "Design review" in titles
        assert "Private catch-up" not in titles

        invited_listing = next(m for m in listing.json()["items"] if m["title"] == "Design review")
        assert invited_listing["my_rsvp"] == "pending"


async def test_employee_cannot_create_or_manage(meet_lead: User, meet_employee: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        meeting = await _create_meeting(client, lead_headers, "Site briefing", [meet_employee.id])

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        created = await client.post(
            "/api/v1/meetings",
            headers=emp_headers,
            json={
                "title": "Not allowed",
                "meeting_type": "internal",
                "scheduled_at": "2026-08-21T10:00:00Z",
            },
        )
        assert created.status_code == 403

        patched = await client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=emp_headers,
            json={"title": "Hacked"},
        )
        assert patched.status_code == 403

        deleted = await client.delete(f"/api/v1/meetings/{meeting['id']}", headers=emp_headers)
        assert deleted.status_code == 403


async def test_rsvp_flow_and_restrictions(
    meet_lead: User, meet_employee: User, meet_employee2: User
) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        meeting = await _create_meeting(client, lead_headers, "Client review", [meet_employee.id])

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        accepted = await client.post(
            f"/api/v1/meetings/{meeting['id']}/rsvp",
            params={"rsvp_status": "accepted"},
            headers=emp_headers,
        )
        assert accepted.status_code == 200
        assert accepted.json()["my_rsvp"] == "accepted"

        emp2_token = await _login(client, EMP2_EMAIL, EMP2_PASSWORD)
        emp2_headers = {"Authorization": f"Bearer {emp2_token}"}
        not_attendee = await client.post(
            f"/api/v1/meetings/{meeting['id']}/rsvp",
            params={"rsvp_status": "declined"},
            headers=emp2_headers,
        )
        assert not_attendee.status_code == 404

        organizer = await client.post(
            f"/api/v1/meetings/{meeting['id']}/rsvp",
            params={"rsvp_status": "accepted"},
            headers=lead_headers,
        )
        assert organizer.status_code == 409


async def test_lead_cannot_manage_others_meeting(meet_lead: User, meet_lead2: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        meeting = await _create_meeting(client, lead_headers, "Team sync", [])

        lead2_token = await _login(client, LEAD2_EMAIL, LEAD2_PASSWORD)
        lead2_headers = {"Authorization": f"Bearer {lead2_token}"}
        patched = await client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=lead2_headers,
            json={"title": "Hijacked"},
        )
        assert patched.status_code == 403

        deleted = await client.delete(f"/api/v1/meetings/{meeting['id']}", headers=lead2_headers)
        assert deleted.status_code == 403


async def test_admin_manages_any_meeting(meet_lead: User, meet_admin: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        meeting = await _create_meeting(client, lead_headers, "Admin oversight", [])

        admin_token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        completed = await client.patch(
            f"/api/v1/meetings/{meeting['id']}",
            headers=admin_headers,
            json={"status": "completed"},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"

        deleted = await client.delete(f"/api/v1/meetings/{meeting['id']}", headers=admin_headers)
        assert deleted.status_code == 200
