import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login() -> str:
    async with AsyncSessionLocal() as db:
        login_id = await db.scalar(select(User.login_id).where(User.email == SUPERUSER_EMAIL))
    assert login_id is not None
    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
        )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_login_rate_limit_returns_429() -> None:
    async with AsyncSessionLocal() as db:
        login_id = await db.scalar(select(User.login_id).where(User.email == SUPERUSER_EMAIL))
    original_max = settings.login_max_attempts
    original_window = settings.login_rate_window_seconds
    settings.login_max_attempts = 3
    settings.login_rate_window_seconds = 300
    try:
        async with _client() as client:
            for _ in range(3):
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"user_id": login_id, "password": "wrong-password"},
                )
                assert response.status_code == 401
            blocked = await client.post(
                "/api/v1/auth/login",
                json={"user_id": login_id, "password": "wrong-password"},
            )
        assert blocked.status_code == 429
        assert blocked.headers.get("Retry-After")
        assert "too many" in blocked.json()["detail"].lower()
    finally:
        settings.login_max_attempts = original_max
        settings.login_rate_window_seconds = original_window


async def test_successful_login_resets_failure_bucket() -> None:
    async with AsyncSessionLocal() as db:
        login_id = await db.scalar(select(User.login_id).where(User.email == SUPERUSER_EMAIL))
    original_max = settings.login_max_attempts
    settings.login_max_attempts = 2
    try:
        async with _client() as client:
            await client.post(
                "/api/v1/auth/login",
                json={"user_id": login_id, "password": "wrong-password"},
            )
            ok = await client.post(
                "/api/v1/auth/login",
                json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
            )
            assert ok.status_code == 200
            again = await client.post(
                "/api/v1/auth/login",
                json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
            )
            assert again.status_code == 200
    finally:
        settings.login_max_attempts = original_max


async def test_tokens_carry_issuer_and_audience() -> None:
    async with AsyncSessionLocal() as db:
        login_id = await db.scalar(select(User.login_id).where(User.email == SUPERUSER_EMAIL))
    async with _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
        )
    assert login.status_code == 200
    body = login.json()
    decoded = jwt.decode(
        body["access_token"],
        settings.secret_key,
        algorithms=[settings.algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    assert decoded["iss"] == settings.jwt_issuer
    assert decoded["aud"] == settings.jwt_audience
    assert decoded["type"] == "access"
    assert decoded["tvp"] == 0
    assert "org_level_code" in body["user"]


async def test_stale_token_version_rejected() -> None:
    """A token minted before a password event must not authenticate."""
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.id).where(User.email == SUPERUSER_EMAIL))
    stale = create_access_token(int(user_id), "L0", token_version=999)
    async with _client() as client:
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {stale}"})
    assert response.status_code == 401


async def test_expired_access_token_rejected() -> None:
    original_minutes = settings.access_token_expire_minutes
    settings.access_token_expire_minutes = -1
    try:
        expired = create_access_token(1, "L0", token_version=0)
    finally:
        settings.access_token_expire_minutes = original_minutes
    async with _client() as client:
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
        )
    assert response.status_code == 401


async def test_access_token_with_wrong_audience_rejected() -> None:
    token = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "exp": 9999999999,
            "iss": settings.jwt_issuer,
            "aud": "other-app",
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    async with _client() as client:
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_create_user_requires_strong_password() -> None:
    token = await _login()
    async with _client() as client:
        weak = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Weak Pass", "password": "abcdefgh"},
        )
        letters_only = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Letters", "password": "abcdefghij"},
        )
    assert weak.status_code == 201
    assert letters_only.status_code == 201
    for body in (weak.json(), letters_only.json()):
        assert len(body["login_id"]) == 6
        assert body["must_change_password"] is True


def test_production_guard_rejects_default_secrets() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(_env_file=None, environment="production", secret_key="change-me-in-production")
    with pytest.raises(ValueError, match="FIRST_SUPERUSER_PASSWORD"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="s3cr3t-r4nd0m-key",
            first_superuser_password="change-me",
        )


def test_production_guard_allows_strong_config() -> None:
    cfg = Settings(
        _env_file=None,
        environment="production",
        secret_key="s3cr3t-r4nd0m-key-1234",
        first_superuser_password="Pr0duction!Pwd",
    )
    assert cfg.environment == "production"
