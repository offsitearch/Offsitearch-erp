import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

ADMIN_EMAIL = "adm.admin@studioerp.dev"
ADMIN_PASSWORD = "adm-admin-pass-123"
LEAD_EMAIL = "adm.lead@studioerp.dev"
LEAD_PASSWORD = "adm-lead-pass-123"
TARGET_EMAIL = "adm.target@studioerp.dev"
TARGET_PASSWORD = "adm-target-pass-123"


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
async def adm_admin():
    return await _create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Admin", "L1")


async def test_lead_can_list_users(adm_admin: User) -> None:
    async with _client() as client:
        await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Lead", "L3")
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/users?active_only=true", headers=headers)
        assert response.status_code == 200, response.text
        assert any(u["email"] == ADMIN_EMAIL for u in response.json())


async def test_super_admin_can_create_and_update_user(adm_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "name": "New Hire",
                "password": TARGET_PASSWORD,
                "designation": "Architect",
                "employee_id": "NEW001",
            },
        )
        assert response.status_code == 201, response.text
        created = response.json()
        assert created["is_active"] is True
        assert len(created["login_id"]) == 6
        assert created["must_change_password"] is True

        actual_email = created["email"]
        actual_password = created["generated_password"]
        new_login = await _login(client, actual_email, actual_password)
        assert new_login

        # The freshly shared password is temporary: everything except the
        # auth endpoints is blocked until the user sets their own.
        gated = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {new_login}"})
        assert gated.status_code == 403
        assert "password" in gated.json()["detail"].lower()

        own_change = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": actual_password, "new_password": "my-own-pass-1"},
            headers={"Authorization": f"Bearer {new_login}"},
        )
        assert own_change.status_code == 200, own_change.text
        assert own_change.json()["user"]["must_change_password"] is False
        working_token = own_change.json()["access_token"]
        me_ok = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {working_token}"}
        )
        assert me_ok.status_code == 200

        response = await client.patch(
            f"/api/v1/users/{created['id']}",
            headers=headers,
            json={"is_active": False, "designation": "Senior Architect"},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False
        assert response.json()["designation"] == "Senior Architect"

        login_after = await client.post(
            "/api/v1/auth/login",
            json={"user_id": created["login_id"], "password": "my-own-pass-1"},
        )
        assert login_after.status_code == 401


async def test_regenerate_password_flow(adm_admin: User) -> None:
    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        super_headers = {"Authorization": f"Bearer {super_token}"}

        created = (
            await client.post(
                "/api/v1/users",
                headers=super_headers,
                json={"name": "Regen Target", "password": "regen-pass-123"},
            )
        ).json()
        target_id = created["id"]
        target_login_id = created["login_id"]

        # Below L1 cannot issue password resets.
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        denied = await client.post(
            f"/api/v1/users/{target_id}/regenerate-password",
            headers={"Authorization": f"Bearer {lead_token}"},
        )
        assert denied.status_code == 403

        # Executives get a one-time password back.
        regen = await client.post(
            f"/api/v1/users/{target_id}/regenerate-password",
            headers=super_headers,
        )
        assert regen.status_code == 200, regen.text
        body = regen.json()
        assert body["login_id"] == target_login_id
        new_password = body["generated_password"]
        assert new_password != created["generated_password"]

        # Old password dead, new temporary one works.
        old_pw_login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": target_login_id, "password": "regen-pass-123"},
        )
        assert old_pw_login.status_code == 401
        temp_login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": target_login_id, "password": new_password},
        )
        assert temp_login.status_code == 200
        temp_access = temp_login.json()["access_token"]

        # Non-auth endpoints stay locked until the user picks a new password.
        gated = await client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {temp_access}"}
        )
        assert gated.status_code == 403

        final = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": new_password, "new_password": "target-final-1"},
            headers={"Authorization": f"Bearer {temp_access}"},
        )
        assert final.status_code == 200
        ok = await client.post(
            "/api/v1/auth/login",
            json={"user_id": target_login_id, "password": "target-final-1"},
        )
        assert ok.status_code == 200


async def test_regenerate_password_guards(adm_admin: User) -> None:
    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        super_headers = {"Authorization": f"Bearer {super_token}"}
        super_user_id = (await client.get("/api/v1/auth/me", headers=super_headers)).json()["id"]

        self_target = await client.post(
            f"/api/v1/users/{super_user_id}/regenerate-password",
            headers=super_headers,
        )
        assert self_target.status_code == 400

        # L1 cannot reset an equal-or-higher rank (the CEO).
        admin_token = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        higher = await client.post(
            f"/api/v1/users/{super_user_id}/regenerate-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert higher.status_code == 403

        missing = await client.post(
            "/api/v1/users/999999/regenerate-password",
            headers=super_headers,
        )
        assert missing.status_code == 404


async def test_below_l1_cannot_manage_users() -> None:
    async with _client() as client:
        try:
            await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Lead", "L3")
        except IntegrityError:
            pass  # already created by an earlier test in this session
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/users",
            headers=headers,
            json={"name": "Nope", "password": "Nope@12345"},
        )
        assert response.status_code == 403


async def test_duplicate_email_rejected() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        # First create a user with name "Dup"
        await client.post(
            "/api/v1/users",
            headers=headers,
            json={"name": "Dup", "password": "Dup@12345"},
        )
        # Creating another with the same name generates the same email → 409
        response = await client.post(
            "/api/v1/users",
            headers=headers,
            json={"name": "Dup", "password": "Dup@12345"},
        )
        assert response.status_code == 409
