"""Regression tests for state machine transition guards."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login(client: AsyncClient) -> str:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models import User

    async with AsyncSessionLocal() as db:
        login_id = await db.scalar(select(User.login_id).where(User.email == SUPERUSER_EMAIL))
    assert login_id is not None
    response = await client.post(
        "/api/v1/auth/login",
        json={"user_id": login_id, "password": SUPERUSER_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ── Task state machine ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_valid_transition_in_progress_to_done():
    """A task can move from in_progress → done."""
    async with _client() as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create task (defaults to todo)
        resp = await client.post(
            "/api/v1/tasks",
            json={"title": "SM test task", "project_id": 1},
            headers=headers,
        )
        if resp.status_code != 201:
            pytest.skip("No project available for task creation")
        task_id = resp.json()["id"]

        # todo → in_progress (valid)
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 200

        # in_progress → done (valid)
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "done"},
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_task_invalid_transition_done_to_todo():
    """A completed task cannot be reopened to todo."""
    async with _client() as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/tasks",
            json={"title": "SM reopen test", "project_id": 1},
            headers=headers,
        )
        if resp.status_code != 201:
            pytest.skip("No project available")
        task_id = resp.json()["id"]

        # Move to done via valid path
        await client.patch(
            f"/api/v1/tasks/{task_id}", json={"status": "in_progress"}, headers=headers
        )
        await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"}, headers=headers)

        # done → todo (INVALID)
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "todo"},
            headers=headers,
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_task_invalid_transition_todo_to_done():
    """A task in todo cannot skip directly to done."""
    async with _client() as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/tasks",
            json={"title": "SM skip test", "project_id": 1},
            headers=headers,
        )
        if resp.status_code != 201:
            pytest.skip("No project available")
        task_id = resp.json()["id"]

        # todo → done (INVALID — must go through in_progress/review)
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "done"},
            headers=headers,
        )
        assert resp.status_code == 409


# ── Expense state machine ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expense_invalid_re_decide():
    """An already-approved expense cannot be re-rejected."""
    async with _client() as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create expense
        resp = await client.post(
            "/api/v1/expenses",
            data={"category": "materials", "amount": "100.00"},
            headers=headers,
        )
        if resp.status_code != 201:
            pytest.skip("Cannot create expense")
        expense_id = resp.json()["id"]

        # Approve it
        resp = await client.patch(
            f"/api/v1/expenses/{expense_id}/approve",
            json={"approve": True},
            headers=headers,
        )
        assert resp.status_code == 200

        # Try to re-reject (INVALID)
        resp = await client.patch(
            f"/api/v1/expenses/{expense_id}/approve",
            json={"approve": False},
            headers=headers,
        )
        assert resp.status_code == 409
