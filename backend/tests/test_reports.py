import zipfile
from datetime import date
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

EMP_EMAIL = "rep.emp@studioerp.dev"
EMP_PASSWORD = "rep-emp-pass-123"

LEAD_EMAIL = "rep.lead@studioerp.dev"
LEAD_PASSWORD = "rep-lead-pass-123"


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


async def _create_employee() -> None:
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models import OrgLevel, User

    async with AsyncSessionLocal() as db:
        lead_level_id = await db.scalar(select(OrgLevel.id).where(OrgLevel.code == "L3"))
        user = User(
            email=EMP_EMAIL,
            name="Report Employee",
            password_hash=hash_password(EMP_PASSWORD),
        )
        db.add(user)
        lead = User(
            email=LEAD_EMAIL,
            name="Report Lead",
            org_level_id=lead_level_id,
            password_hash=hash_password(LEAD_PASSWORD),
        )
        db.add(lead)
        await db.commit()


@pytest.fixture(scope="session")
async def report_employee():
    await _create_employee()
    return None


async def test_reports_require_admin(report_employee) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        for path in ["/api/v1/reports/projects", "/api/v1/reports/finance", "/api/v1/reports/hr"]:
            response = await client.get(path, headers=headers)
            assert response.status_code == 403


async def test_reports_lead_denied_persona(report_employee) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        for path in ["/api/v1/reports/projects", "/api/v1/reports/finance", "/api/v1/reports/hr"]:
            response = await client.get(path, headers=headers)
            assert response.status_code == 403


async def test_reports_json_shapes() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/reports/projects", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data and "rows" in data
        assert "total_projects" in data["summary"]

        response = await client.get("/api/v1/reports/finance?period=all", headers=headers)
        assert response.status_code == 200
        assert "invoiced" in response.json()["summary"]

        today = date.today()
        response = await client.get(
            f"/api/v1/reports/hr?month={today.month}&year={today.year}", headers=headers
        )
        assert response.status_code == 200
        assert "total_employees" in response.json()["summary"]


async def test_reports_csv_export() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/reports/projects?format=csv", headers=headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "Content-Disposition" in response.headers
        text = response.text
        assert "project_code" in text
        assert "ARC-" in text


async def test_reports_xlsx_export_is_valid_zip() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            "/api/v1/reports/finance?period=all&format=xlsx", headers=headers
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            names = zf.namelist()
            assert "[Content_Types].xml" in names
            assert "xl/workbook.xml" in names
            assert "xl/styles.xml" in names
            assert any(n.startswith("xl/worksheets/") for n in names)


async def test_attendance_report_xlsx() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        today = date.today()
        first = today.replace(day=1).isoformat()
        response = await client.get(
            f"/api/v1/attendance/report?from_date={first}&to_date={today.isoformat()}&format=xlsx",
            headers=headers,
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            assert any(n.startswith("xl/worksheets/") for n in zf.namelist())


async def test_audit_logs_listing_and_filtering() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/audit-logs?limit=20", headers=headers)
        assert response.status_code == 200
        logs = response.json()
        assert isinstance(logs, list)
        for entry in logs:
            assert "action" in entry and "entity_type" in entry and "user_name" in entry

        response = await client.get("/api/v1/audit-logs?entity_type=user", headers=headers)
        assert response.status_code == 200
        assert all(log["entity_type"] == "user" for log in response.json())

        response = await client.get("/api/v1/audit-logs?user_id=0", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


async def test_audit_logs_require_admin(report_employee) -> None:
    async with _client() as client:
        for email, password in ((EMP_EMAIL, EMP_PASSWORD), (LEAD_EMAIL, LEAD_PASSWORD)):
            token = await _login(client, email, password)
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get("/api/v1/audit-logs", headers=headers)
            assert response.status_code == 403
