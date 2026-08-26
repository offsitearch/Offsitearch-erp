import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password


def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _superuser_login_id() -> str:
    async with AsyncSessionLocal() as db:
        login_id = await db.scalar(select(User.login_id).where(User.email == SUPERUSER_EMAIL))
    assert login_id is not None, "seed superuser missing"
    return login_id


async def test_login_success() -> None:
    login_id = await _superuser_login_id()
    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == SUPERUSER_EMAIL
    assert body["user"]["login_id"] == login_id
    assert "org_level_code" in body["user"]


async def test_login_unknown_user_id() -> None:
    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"user_id": "999999", "password": SUPERUSER_PASSWORD},
        )
    assert response.status_code == 401


async def test_login_rejects_malformed_user_id() -> None:
    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"user_id": "admin@studioerp.dev", "password": SUPERUSER_PASSWORD},
        )
    assert response.status_code == 422


async def test_login_wrong_password() -> None:
    login_id = await _superuser_login_id()
    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": "wrong-password"},
        )
    assert response.status_code == 401


async def test_me_with_token() -> None:
    login_id = await _superuser_login_id()
    async with _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
        )
        token = login.json()["access_token"]
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == SUPERUSER_EMAIL
    assert body["login_id"] == login_id


async def test_me_without_token() -> None:
    async with _client() as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_rotates_tokens() -> None:
    login_id = await _superuser_login_id()
    async with _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
        )
        refresh_token = login.json()["refresh_token"]
        first_access = login.json()["access_token"]

        refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["access_token"] != first_access
    assert body["refresh_token"] != refresh_token


async def test_logout_revokes_refresh() -> None:
    login_id = await _superuser_login_id()
    async with _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
        )
        refresh_token = login.json()["refresh_token"]

        await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})

        reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401


async def test_change_password_returns_new_tokens_and_invalidates_old() -> None:
    from app.core.security import hash_password

    email = "auth.changepw@studioerp.dev"
    old_password = "old-pass-123"
    new_password = "new-pass-456"
    async with AsyncSessionLocal() as db:
        db.add(
            User(
                email=email,
                name="Change PW",
                password_hash=hash_password(old_password),
            )
        )
        await db.commit()
        login_id = await db.scalar(select(User.login_id).where(User.email == email))

    async with _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": old_password},
        )
        assert login.status_code == 200
        old_access = login.json()["access_token"]

        wrong_current = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "nope-nope", "new_password": new_password},
            headers={"Authorization": f"Bearer {old_access}"},
        )
        assert wrong_current.status_code == 400

        changed = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": old_password, "new_password": new_password},
            headers={"Authorization": f"Bearer {old_access}"},
        )
        assert changed.status_code == 200
        body = changed.json()
        assert body["access_token"]
        assert body["user"]["must_change_password"] is False

        stale = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {old_access}"}
        )
        assert stale.status_code == 401

        relaunch = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": new_password},
        )
        assert relaunch.status_code == 200


@pytest.mark.parametrize("payload", [{"password": "x-pass-123"}, {"user_id": "12345"}])
async def test_login_validates_payload(payload: dict) -> None:
    async with _client() as client:
        response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422
