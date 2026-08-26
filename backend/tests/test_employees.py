import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User
from app.modules.employees.schemas import SalaryUpdate
from app.modules.employees import service as employee_service

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

EMP_A_EMAIL = "emp.a@studioerp.dev"
EMP_A_PASSWORD = "emp-a-pass-123"
EMP_B_EMAIL = "emp.b@studioerp.dev"
EMP_B_PASSWORD = "emp-b-pass-123"
ADMIN_HR_EMAIL = "hr.admin@studioerp.dev"
ADMIN_HR_PASSWORD = "hr-admin-pass-123"
LEAD_EMAIL = "emp.lead@studioerp.dev"
LEAD_PASSWORD = "emp-lead-pass-123"


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
async def employee_a():
    return await _create_user(EMP_A_EMAIL, EMP_A_PASSWORD, "Employee A")


@pytest.fixture(scope="session")
async def employee_b():
    return await _create_user(EMP_B_EMAIL, EMP_B_PASSWORD, "Employee B")


@pytest.fixture(scope="session")
async def hr_admin():
    return await _create_user(ADMIN_HR_EMAIL, ADMIN_HR_PASSWORD, "HR Admin", "L1")


@pytest.fixture(scope="session")
async def emp_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Employee Lead", "L3")


async def test_lead_reads_directory_and_profile(emp_lead: User, employee_a: User) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        directory = await client.get(
            "/api/v1/employees?page=1&page_size=20&active_only=true", headers=headers
        )
        assert directory.status_code == 200
        assert any(item["id"] == employee_a.id for item in directory.json()["items"])

        skills = await client.get("/api/v1/employees/skills", headers=headers)
        assert skills.status_code == 200

        chart = await client.get("/api/v1/employees/org-chart", headers=headers)
        assert chart.status_code == 200
        assert isinstance(chart.json(), list)

        profile = await client.get(f"/api/v1/employees/{employee_a.id}", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["name"] == "Employee A"


async def test_lead_cannot_manage_employees(emp_lead: User, employee_a: User) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/v1/employees",
            json={
                "name": "Not Allowed",
                "email": "not.allowed@studioerp.dev",
                "password": "not-allowed-123",
                "role": "employee",
            },
            headers=headers,
        )
        assert created.status_code == 403

        salary = await client.get(f"/api/v1/employees/{employee_a.id}/salary", headers=headers)
        assert salary.status_code == 403

        deleted = await client.delete(f"/api/v1/employees/{employee_a.id}", headers=headers)
        assert deleted.status_code == 403


async def test_create_employee_via_api(hr_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_HR_EMAIL, ADMIN_HR_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/employees",
            json={
                "name": "Alice Johnson",
                "designation": "Architect",
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["email"].endswith("@offsitearch.com")

        duplicate = await client.post(
            "/api/v1/employees",
            json={
                "name": "Alice Johnson",
            },
            headers=headers,
        )
        assert duplicate.status_code == 409


async def test_list_employees_search_and_pagination(hr_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, ADMIN_HR_EMAIL, ADMIN_HR_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        page = await client.get(
            "/api/v1/employees?page=1&page_size=5&active_only=true", headers=headers
        )
        assert page.status_code == 200
        body = page.json()
        assert body["total"] >= 4
        assert len(body["items"]) <= 5

        search = await client.get("/api/v1/employees?search=Employee+B", headers=headers)
        assert all("Employee B" in item["name"] for item in search.json()["items"])


async def test_employee_cannot_read_other_profile(employee_a: User, employee_b: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_A_EMAIL, EMP_A_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        own = await client.get(f"/api/v1/employees/{employee_a.id}", headers=headers)
        assert own.status_code == 200

        other = await client.get(f"/api/v1/employees/{employee_b.id}", headers=headers)
        assert other.status_code == 403


async def test_self_update_limited_fields(employee_a: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_A_EMAIL, EMP_A_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        ok = await client.patch(
            f"/api/v1/employees/{employee_a.id}",
            json={"phone": "9999000011"},
            headers=headers,
        )
        assert ok.status_code == 200
        assert ok.json()["phone"] == "9999000011"


async def test_soft_delete_deactivates(employee_b: User, emp_lead: User, hr_admin: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}

        # Deactivation is executive-only (L1): the L3 lead is denied.
        forbidden = await client.delete(f"/api/v1/employees/{employee_b.id}", headers=lead_headers)
        assert forbidden.status_code == 403

        admin_token = await _login(client, ADMIN_HR_EMAIL, ADMIN_HR_PASSWORD)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        deleted = await client.delete(f"/api/v1/employees/{employee_b.id}", headers=admin_headers)
        assert deleted.status_code == 204

        profile = await client.get(f"/api/v1/employees/{employee_b.id}", headers=admin_headers)
        assert profile.json()["is_active"] is False


async def test_salary_upsert(hr_admin: User) -> None:
    async with AsyncSessionLocal() as db:
        user = await _create_user("salary.user@studioerp.dev", "salary-pass-123", "Salary User")
        salary = await employee_service.upsert_salary(
            db,
            user.id,
            SalaryUpdate(ctc_annual=1200000, basic=50000, hra=25000),
        )
        assert float(salary.ctc_annual) == 1200000.0

        updated = await employee_service.upsert_salary(
            db, user.id, SalaryUpdate(bank_name="ICICI", ifsc_code="ICIC0001")
        )
        assert updated.bank_name == "ICICI"
        assert float(updated.ctc_annual) == 1200000.0


async def test_departments_list_and_org_chart(hr_admin: User) -> None:
    async with _client() as client:
        admin_token = await _login(client, ADMIN_HR_EMAIL, ADMIN_HR_PASSWORD)
        headers = {"Authorization": f"Bearer {admin_token}"}

        depts = await client.get("/api/v1/departments", headers=headers)
        assert depts.status_code == 200
        assert len(depts.json()) >= 1

        chart = await client.get("/api/v1/employees/org-chart", headers=headers)
        assert chart.status_code == 200
        assert isinstance(chart.json(), list)
