"""Financial-boundary authorization tests (revenue surfaces).

Revenue data (finance overview, finance report, dashboard revenue) is
restricted to the executive band (L0 CEO / L1 Director). Every other
level — department heads, leads, staff, interns and unleveled accounts
— must be denied.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

# persona -> (email, password, org level code)
REVENUE_USERS = {
    "dept_head": ("rev.admin@studioerp.dev", "rev-admin-pass-123", "L2"),
    "lead": ("rev.lead@studioerp.dev", "rev-lead-pass-123", "L3"),
    "employee": ("rev.employee@studioerp.dev", "rev-emp-pass-123", "L5"),
    "intern": ("rev.intern@studioerp.dev", "rev-intern-pass-123", "L6"),
}


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
async def revenue_personas():
    async with AsyncSessionLocal() as db:
        levels = {c: lid for c, lid in (await db.execute(select(OrgLevel.code, OrgLevel.id))).all()}
        for email, password, code in REVENUE_USERS.values():
            db.add(
                User(
                    email=email,
                    name=f"Rev {code}",
                    org_level_id=levels[code],
                    password_hash=hash_password(password),
                )
            )
        await db.commit()
    return None


REVENUE_ENDPOINTS = [
    "/api/v1/finance/overview",
    "/api/v1/reports/finance",
]


@pytest.mark.parametrize("path", REVENUE_ENDPOINTS)
async def test_executive_can_read_revenue(path) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(path, headers=headers)
        assert response.status_code == 200


@pytest.mark.parametrize("persona", list(REVENUE_USERS.keys()))
@pytest.mark.parametrize("path", REVENUE_ENDPOINTS)
async def test_non_executives_denied_revenue(revenue_personas, persona, path) -> None:
    email, password, _ = REVENUE_USERS[persona]
    async with _client() as client:
        token = await _login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(path, headers=headers)
        assert response.status_code == 403, f"{persona} must not read {path}"


@pytest.mark.parametrize("path", REVENUE_ENDPOINTS)
async def test_revenue_requires_authentication(path) -> None:
    async with _client() as client:
        response = await client.get(path)
        assert response.status_code == 401


async def test_dashboard_hides_revenue_from_department_head() -> None:
    async with _client() as client:
        token = await _login(client, *REVENUE_USERS["dept_head"][:2])
        headers = {"Authorization": f"Bearer {token}"}
        summary = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["revenue_this_month"] is None


async def test_dashboard_shows_revenue_to_executive() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        summary = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary.status_code == 200
        body = summary.json()
        # Seeded demo data may be absent in a fresh DB; the field itself
        # must be present and numeric for the executive.
        assert "revenue_this_month" in body
        if body["revenue_this_month"] is not None:
            assert float(body["revenue_this_month"]) >= 0


async def test_finance_report_exports_stay_executive_only(revenue_personas) -> None:
    """CSV/XLSX export variants of the finance report are gated too."""
    async with _client() as client:
        head_token = await _login(client, *REVENUE_USERS["dept_head"][:2])
        head_headers = {"Authorization": f"Bearer {head_token}"}
        for fmt in ("csv", "xlsx"):
            response = await client.get(
                f"/api/v1/reports/finance?period=all&format={fmt}", headers=head_headers
            )
            assert response.status_code == 403, f"L2 must not export finance as {fmt}"

        exec_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        exec_headers = {"Authorization": f"Bearer {exec_token}"}
        csv = await client.get(
            "/api/v1/reports/finance?period=all&format=csv", headers=exec_headers
        )
        assert csv.status_code == 200
        assert "text/csv" in csv.headers["content-type"]
        xlsx = await client.get(
            "/api/v1/reports/finance?period=all&format=xlsx", headers=exec_headers
        )
        assert xlsx.status_code == 200
        assert "spreadsheetml" in xlsx.headers["content-type"]


async def test_operational_finance_executive_only(revenue_personas) -> None:
    """Invoices and expenses are financial data: L0/L1 only. The L2
    department head is denied; the executive passes."""
    async with _client() as client:
        head_token = await _login(client, *REVENUE_USERS["dept_head"][:2])
        head_headers = {"Authorization": f"Bearer {head_token}"}
        invoices = await client.get("/api/v1/invoices?page_size=5", headers=head_headers)
        assert invoices.status_code == 403
        expenses = await client.get("/api/v1/expenses?page_size=5", headers=head_headers)
        assert expenses.status_code == 403

        exec_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        exec_headers = {"Authorization": f"Bearer {exec_token}"}
        assert (
            await client.get("/api/v1/invoices?page_size=5", headers=exec_headers)
        ).status_code == 200
