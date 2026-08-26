"""Financial data isolation — end-to-end matrix and body-leak tests.

Policy: only L0 (CEO) and L1 (Director) may access financial data, directly
or indirectly (see docs/architecture/financial_access_policy.md).
These tests verify both the authorization gates AND that unauthorized
responses never leak rupee figures in their bodies.
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

PERSONAS = {
    "ceo": ("fin.ceo@studioerp.dev", "fin-ceo-pass-123", "L0"),
    "director": ("fin.director@studioerp.dev", "fin-dir-pass-123", "L1"),
    "dept_head": ("fin.head@studioerp.dev", "fin-head-pass-123", "L2"),
    "lead": ("fin.lead@studioerp.dev", "fin-lead-pass-123", "L3"),
    "staff": ("fin.staff@studioerp.dev", "fin-staff-pass-123", None),
}

PASSWORDS = {email: pwd for email, pwd, _ in PERSONAS.values()}


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
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
async def personas():
    async with AsyncSessionLocal() as db:
        level_ids = {
            code: await db.scalar(select(OrgLevel.id).where(OrgLevel.code == code))
            for _, _, code in PERSONAS.values()
            if code
        }
        for name, (email, password, code) in PERSONAS.items():
            existing = await db.scalar(select(User).where(User.email == email))
            if existing is None:
                db.add(
                    User(
                        email=email,
                        name=f"Fin {name.title()}",
                        org_level_id=level_ids.get(code),
                        password_hash=hash_password(password),
                    )
                )
        await db.commit()
    return PERSONAS


async def _token(persona: str) -> str:
    email, password, _ = PERSONAS[persona]
    async with _client() as client:
        return await _login(client, email, password)


# ── 1. Direct financial endpoints ───────────────────────────────────────────

FINANCIAL_GETS = [
    "/api/v1/finance/overview?period=month",
    "/api/v1/invoices",
    "/api/v1/expenses",
    "/api/v1/reports/projects",
    "/api/v1/reports/finance?period=month",
]


@pytest.mark.parametrize("path", FINANCIAL_GETS)
@pytest.mark.asyncio
async def test_financial_reads_executive_only(path: str, personas) -> None:
    allowed = []
    for persona in ("ceo", "director", "dept_head", "lead", "staff"):
        async with _client() as client:
            token = await _token(persona)
            response = await client.get(path, headers=_headers(token))
            if response.status_code == 200:
                allowed.append(persona)
            else:
                assert response.status_code == 403, f"{persona}: {response.status_code}"
    assert allowed == ["ceo", "director"], f"{path}: allowed={allowed}"


@pytest.mark.parametrize("persona", ["ceo", "director"])
@pytest.mark.asyncio
async def test_salary_read_executive_only(persona: str, personas) -> None:
    # superuser is the L0 CEO seed account; use its own salary endpoint.
    async with _client() as client:
        if persona == "ceo":
            token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
            me = await client.get("/api/v1/auth/me", headers=_headers(token))
            user_id = me.json()["id"]
        else:
            token = await _token(persona)
            me = await client.get("/api/v1/auth/me", headers=_headers(token))
            user_id = me.json()["id"]
        # 404 simply means the gate passed but no salary record exists yet.
        response = await client.get(f"/api/v1/employees/{user_id}/salary", headers=_headers(token))
        assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_salary_denied_below_executive(personas) -> None:
    async with _client() as client:
        ceo_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        me = await client.get("/api/v1/auth/me", headers=_headers(ceo_token))
        user_id = me.json()["id"]
        for persona in ("dept_head", "lead", "staff"):
            token = await _token(persona)
            response = await client.get(
                f"/api/v1/employees/{user_id}/salary", headers=_headers(token)
            )
            assert response.status_code == 403, persona


# ── 2. Indirect leaks: dashboard ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_revenue_null_for_non_executive(personas) -> None:
    for persona in ("ceo", "director", "dept_head", "lead", "staff"):
        async with _client() as client:
            token = await _token(persona)
            response = await client.get("/api/v1/dashboard/summary", headers=_headers(token))
            assert response.status_code == 200, persona
            revenue = response.json().get("revenue_this_month")
            if persona in ("ceo", "director"):
                continue  # may be a number
            assert revenue is None, f"{persona} leaked revenue: {revenue}"


# ── 3. Body leaks: projects ──────────────────────────────────────────────────

MONEY_KEYS = {
    "budget",
    "studio_fee",
    "fee_type",
    "fee_percent",
    "total_budget",
    "total_studio_fee",
    "invoiced",
    "received",
    "outstanding",
}


@pytest.fixture(scope="module")
async def seeded_project():
    """One project created by the CEO with the lead persona as project lead,
    visible to everyone (used by both leak and write tests)."""
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
    async with AsyncSessionLocal() as db:
        lead_id = await db.scalar(select(User.id).where(User.email == PERSONAS["lead"][0]))
    async with _client() as client:
        created = await client.post(
            "/api/v1/projects",
            json={
                "name": "Isolation Tower",
                "project_type": "commercial",
                "status": "draft",
                "budget": 500000,
                "studio_fee": 120000,
                "project_lead_id": lead_id,
            },
            headers=_headers(token),
        )
        assert created.status_code == 201, created.text
        return created.json()["id"]


@pytest.mark.asyncio
async def test_project_detail_has_no_money_keys_below_l1(seeded_project, personas) -> None:
    for persona in ("dept_head", "lead", "staff"):
        async with _client() as client:
            token = await _token(persona)
            response = await client.get(
                f"/api/v1/projects/{seeded_project}", headers=_headers(token)
            )
            # staff (self-service band) may get 404 when not a team member;
            # if they can read it, the body must not leak money fields.
            assert response.status_code in (200, 404), persona
            if response.status_code != 200:
                continue
            body = response.json()
            leaked = MONEY_KEYS & set(body.keys())
            assert not leaked, f"{persona} leaked {leaked}"
            for phase in body.get("phases", []):
                assert phase.get("studio_fee") is None, persona


@pytest.mark.asyncio
async def test_project_detail_keeps_money_for_executives(seeded_project, personas) -> None:
    async with _client() as client:
        token = await _token("director")
        response = await client.get(f"/api/v1/projects/{seeded_project}", headers=_headers(token))
        assert response.status_code == 200
        body = response.json()
        assert body.get("studio_fee") is not None
        assert body.get("budget") is not None


@pytest.mark.asyncio
async def test_projects_list_no_money_keys_for_lead(personas) -> None:
    async with _client() as client:
        token = await _token("lead")
        response = await client.get("/api/v1/projects", headers=_headers(token))
        assert response.status_code == 200
        for item in response.json()["items"]:
            leaked = {"budget", "studio_fee"} & set(item.keys())
            assert not leaked, leaked


# ── 4. Body leaks: clients ─────────────────────────────────────────


@pytest.fixture(scope="module")
async def seeded_client():
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        created = await client.post(
            "/api/v1/clients",
            json={
                "name": "Iso Client",
                "client_type": "company",
                "email": "iso@client.in",
                "budget_range": "50L+",
            },
            headers=_headers(token),
        )
        assert created.status_code == 201, created.text
        return created.json()["id"]


@pytest.mark.asyncio
async def test_client_profile_masks_deal_value_below_l1(seeded_client, personas) -> None:
    # CRM reads are L3+ (2026-08-24 hardening): staff is denied outright,
    # while the L3 lead still gets a money-masked profile.
    async with _client() as client:
        staff_token = await _token("staff")
        staff_resp = await client.get(
            f"/api/v1/clients/{seeded_client}", headers=_headers(staff_token)
        )
        assert staff_resp.status_code == 403

    token = await _token("lead")
    async with _client() as client:
        response = await client.get(f"/api/v1/clients/{seeded_client}", headers=_headers(token))
        assert response.status_code == 200
        body = response.json()
        assert "budget_range" not in body["client"]
        fin = body["financial_summary"]
        for key in ("total_budget", "total_studio_fee", "invoiced", "received", "outstanding"):
            assert fin.get(key) is None, f"lead leaked {key}"
        for p in body["projects"]:
            assert p.get("budget") is None and p.get("studio_fee") is None


@pytest.mark.asyncio
async def test_client_profile_shows_money_to_director(seeded_client, personas) -> None:
    async with _client() as client:
        token = await _token("director")
        response = await client.get(f"/api/v1/clients/{seeded_client}", headers=_headers(token))
        assert response.status_code == 200
        assert response.json()["client"]["budget_range"] == "50L+"


# ── 5. Money writes restricted to L0/L1 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_project_money_write_denied_below_l1(seeded_project, personas) -> None:
    for persona in ("dept_head", "lead", "staff"):
        async with _client() as client:
            token = await _token(persona)
            response = await client.patch(
                f"/api/v1/projects/{seeded_project}",
                json={"budget": 999},
                headers=_headers(token),
            )
            assert response.status_code == 403, persona


@pytest.mark.asyncio
async def test_phase_fee_write_denied_to_non_executive_manager(seeded_project, personas) -> None:
    # The lead owns this project (project_lead_id) so the operational phase
    # gate passes — only the fee field must be rejected.
    async with _client() as client:
        token = await _token("lead")
        created = await client.post(
            f"/api/v1/projects/{seeded_project}/phases",
            json={"name": "Lead Phase", "studio_fee": 12345},
            headers=_headers(token),
        )
        assert created.status_code == 403

        ok = await client.post(
            f"/api/v1/projects/{seeded_project}/phases",
            json={"name": "Lead Phase"},
            headers=_headers(token),
        )
        assert ok.status_code == 201, ok.text


@pytest.mark.asyncio
async def test_client_budget_write_denied_below_l1(seeded_client, personas) -> None:
    async with _client() as client:
        token = await _token("lead")
        response = await client.patch(
            f"/api/v1/clients/{seeded_client}",
            json={"budget_range": "99Cr"},
            headers=_headers(token),
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_executives_can_still_write_money(seeded_project, seeded_client, personas) -> None:
    async with _client() as client:
        token = await _token("director")
        patched_project = await client.patch(
            f"/api/v1/projects/{seeded_project}",
            json={"budget": 600000},
            headers=_headers(token),
        )
        assert patched_project.status_code == 200
        assert patched_project.json()["budget"] is not None

        patched_client = await client.patch(
            f"/api/v1/clients/{seeded_client}",
            json={"budget_range": "75L"},
            headers=_headers(token),
        )
        assert patched_client.status_code == 200


# ── 6. Exports inherit the same boundary ─────────────────────────────────────


@pytest.mark.asyncio
async def test_report_exports_denied_below_l1(personas) -> None:
    for fmt in ("csv", "xlsx"):
        async with _client() as client:
            token = await _token("dept_head")
            projects_export = await client.get(
                f"/api/v1/reports/projects?format={fmt}", headers=_headers(token)
            )
            finance_export = await client.get(
                f"/api/v1/reports/finance?format={fmt}&period=all", headers=_headers(token)
            )
            assert projects_export.status_code == 403
            assert finance_export.status_code == 403
