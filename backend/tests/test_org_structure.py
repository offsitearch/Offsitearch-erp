"""Organizational structure tests.

Covers the 7-level hierarchy (L0–L6), the department model with
sub-department support, designations, and reporting relationships.
Verifies that designations never grant permissions and that seniority
levels gate endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Department, OrgLevel, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

ORG_EMP_EMAIL = "org.emp@studioerp.dev"
ORG_EMP_PASSWORD = "org-emp-pass-123"
ORG_MANAGER_EMAIL = "org.manager@studioerp.dev"
ORG_MANAGER_PASSWORD = "org-manager-pass-123"


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
async def org_levels() -> dict[str, OrgLevel]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(OrgLevel.__table__.select())).fetchall()
        return {row.code: row for row in rows}


@pytest.fixture(scope="session")
async def org_departments() -> dict[str, Department]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(Department.__table__.select())).fetchall()
        return {row.name: row for row in rows}


@pytest.fixture(scope="session")
async def org_manager(org_levels):
    async with AsyncSessionLocal() as db:
        user = User(
            email=ORG_MANAGER_EMAIL,
            name="Org Manager",
            password_hash=hash_password(ORG_MANAGER_PASSWORD),
            org_level_id=org_levels["L3"].id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest.fixture(scope="session")
async def org_employee(org_levels, org_departments, org_manager):
    """Employee with department + level + designation + reporting manager."""
    async with AsyncSessionLocal() as db:
        manager = await db.get(User, org_manager.id)
        user = User(
            email=ORG_EMP_EMAIL,
            name="Org Employee",
            password_hash=hash_password(ORG_EMP_PASSWORD),
            department_id=org_departments["Architecture & Design"].id,
            org_level_id=org_levels["L5"].id,
            designation="Architect",
            reporting_to_id=manager.id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


# ── Level catalog ───────────────────────────────────────────────────


async def test_seven_org_levels_seeded(org_levels) -> None:
    expected = {
        "L0": "CEO",
        "L1": "Director",
        "L2": "Department Head",
        "L3": "Project / Team Lead",
        "L4": "Sr. Professional",
        "L5": "Professional",
        "L6": "Intern",
    }
    assert set(org_levels.keys()) == set(expected.keys())
    for code, name in expected.items():
        assert org_levels[code].name == name
    ranks = [org_levels[c].rank for c in expected]
    assert ranks == sorted(ranks)
    assert org_levels["L0"].rank == 0


async def test_list_org_levels_endpoint(org_employee) -> None:
    async with _client() as client:
        token = await _login(client, ORG_EMP_EMAIL, ORG_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/org-levels", headers=headers)
        assert response.status_code == 200
        levels = response.json()
        assert [lvl["code"] for lvl in levels] == ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]
        assert all({"id", "code", "name", "description", "rank"} <= set(lvl) for lvl in levels)


async def test_org_levels_require_authentication() -> None:
    async with _client() as client:
        response = await client.get("/api/v1/org-levels")
        assert response.status_code == 401


# ── Departments ─────────────────────────────────────────────────────


async def test_seven_top_level_departments_seeded(org_departments) -> None:
    expected = [
        "Architecture & Design",
        "Interior Design",
        "Landscape",
        "BIM & Visualization",
        "Project & Site",
        "Business & Operations",
        "Corporate / Administration",
    ]
    for name in expected:
        assert name in org_departments, f"missing department: {name}"
        assert org_departments[name].is_active is True
        assert org_departments[name].parent_id is None


async def test_sub_department_creation_and_listing(org_departments) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        parent_id = org_departments["Architecture & Design"].id
        created = await client.post(
            "/api/v1/departments",
            json={"name": "Urban Design", "parent_id": parent_id, "description": "Sub-department"},
            headers=headers,
        )
        assert created.status_code == 201
        sub = created.json()
        assert sub["parent_id"] == parent_id
        assert sub["parent_name"] == "Architecture & Design"

        listing = await client.get("/api/v1/departments", headers=headers)
        names = {d["name"]: d for d in listing.json()}
        assert names["Urban Design"]["parent_name"] == "Architecture & Design"

        # A department cannot be its own parent
        self_parent = await client.patch(
            f"/api/v1/departments/{parent_id}",
            json={"parent_id": parent_id},
            headers=headers,
        )
        assert self_parent.status_code == 400

        # Unknown parent → 404
        bad_parent = await client.post(
            "/api/v1/departments",
            json={"name": "Orphan Dept", "parent_id": 999999},
            headers=headers,
        )
        assert bad_parent.status_code == 404


# ── Employee organizational fields ──────────────────────────────────


async def test_employee_profile_shows_all_org_fields(org_employee) -> None:
    async with _client() as client:
        token = await _login(client, ORG_EMP_EMAIL, ORG_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        profile = await client.get(f"/api/v1/employees/{org_employee.id}", headers=headers)
        assert profile.status_code == 200
        body = profile.json()
        assert body["department"] == "Architecture & Design"
        assert body["org_level_code"] == "L5"
        assert body["org_level_name"] == "Professional"
        assert body["designation"] == "Architect"
        assert body["reporting_to_id"] is not None


async def test_create_employee_with_full_org_data(org_levels, org_departments) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post(
            "/api/v1/employees",
            json={
                "name": "Ayesha Khan",
                "department_id": org_departments["BIM & Visualization"].id,
                "org_level_id": org_levels["L5"].id,
                "designation": "BIM Architect",
            },
            headers=headers,
        )
        assert created.status_code == 201
        body = created.json()
        assert body["department"] == "BIM & Visualization"
        assert body["org_level_code"] == "L5"
        assert body["designation"] == "BIM Architect"

        # Invalid FK references are rejected
        bad_dept = await client.post(
            "/api/v1/employees",
            json={"name": "Bad Dept Person", "department_id": 999999},
            headers=headers,
        )
        assert bad_dept.status_code == 404

        bad_level = await client.post(
            "/api/v1/employees",
            json={"name": "Bad Level Person", "org_level_id": 999999},
            headers=headers,
        )
        assert bad_level.status_code == 404


async def test_directory_filter_by_level(org_levels, org_employee) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"/api/v1/employees?org_level_id={org_levels['L5'].id}&active_only=true&page_size=100",
            headers=headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1
        assert all(item["org_level_code"] == "L5" for item in items)
        assert any(item["id"] == org_employee.id for item in items)


async def test_designation_catalog_endpoint(org_employee, org_manager) -> None:
    async with _client() as client:
        # Leads and admins can read the catalog…
        token = await _login(client, ORG_MANAGER_EMAIL, ORG_MANAGER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/employees/designations", headers=headers)
        assert response.status_code == 200
        catalog = response.json()
        assert set(catalog.keys()) == {"L0", "L1", "L2", "L3", "L4", "L5", "L6"}
        assert "Project Manager" in catalog["L3"]
        assert "Sr. Architect" in catalog["L4"]

        # …plain employees cannot.
        emp_token = await _login(client, ORG_EMP_EMAIL, ORG_EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        denied = await client.get("/api/v1/employees/designations", headers=emp_headers)
        assert denied.status_code == 403


async def test_org_chart_includes_level(org_employee) -> None:
    async with _client() as client:
        token = await _login(client, ORG_EMP_EMAIL, ORG_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        chart = await client.get("/api/v1/employees/org-chart", headers=headers)
        assert chart.status_code == 200
        flat: list[dict] = []

        def walk(nodes):
            for node in nodes:
                flat.append(node)
                walk(node.get("children", []))

        walk(chart.json())
        target = next(n for n in flat if n["user_id"] == org_employee.id)
        assert target["org_level_code"] == "L5"


# ── Seniority gates endpoints ───────────────────────────────────────


async def test_level_gates_admin_endpoints(org_levels, org_departments) -> None:
    """Authorization follows organizational level: an L5 professional is
    denied admin endpoints while an L1 director passes them."""
    async with AsyncSessionLocal() as db:
        db.add(
            User(
                email="org.l5.employee@studioerp.dev",
                name="L5 Professional",
                org_level_id=org_levels["L5"].id,
                department_id=org_departments["Corporate / Administration"].id,
                designation="Architect",
                password_hash=hash_password("org-l5-pass-123"),
            )
        )
        db.add(
            User(
                email="org.l1.director@studioerp.dev",
                name="L1 Director",
                org_level_id=org_levels["L1"].id,
                designation="Studio Director",
                password_hash=hash_password("org-l1-pass-123"),
            )
        )
        await db.commit()

    async with _client() as client:
        # L5: staff band — admin endpoints are out of reach
        token = await _login(client, "org.l5.employee@studioerp.dev", "org-l5-pass-123")
        headers = {"Authorization": f"Bearer {token}"}
        denied = await client.get("/api/v1/audit-logs?limit=5", headers=headers)
        assert denied.status_code == 403

        # L1: executive band — audit logs open
        token = await _login(client, "org.l1.director@studioerp.dev", "org-l1-pass-123")
        headers = {"Authorization": f"Bearer {token}"}
        allowed = await client.get("/api/v1/audit-logs?limit=5", headers=headers)
        assert allowed.status_code == 200


async def test_designation_without_level_grants_nothing(org_levels) -> None:
    """A grand-sounding designation on a user without any org level grants
    nothing — unknown/no level ranks as least-privileged."""
    async with AsyncSessionLocal() as db:
        db.add(
            User(
                email="org.md.titled@studioerp.dev",
                name="MD Titled Employee",
                designation="Managing Director",
                password_hash=hash_password("org-md-pass-123"),
            )
        )
        await db.commit()

    async with _client() as client:
        token = await _login(client, "org.md.titled@studioerp.dev", "org-md-pass-123")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/finance/overview", headers=headers)
        assert response.status_code == 403
        reports = await client.get("/api/v1/reports/finance", headers=headers)
        assert reports.status_code == 403


async def test_department_head_is_organizational_not_rbac(org_departments) -> None:
    """Assigning a department head must not change anyone's system role."""
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        dept_id = org_departments["Interior Design"].id
        updated = await client.patch(
            f"/api/v1/departments/{dept_id}",
            json={"head_id": 1},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["head_id"] == 1

        # The superuser's own level is untouched by the head assignment.
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.json()["org_level_code"] == "L0"


async def test_auth_me_returns_org_level(org_employee) -> None:
    async with _client() as client:
        token = await _login(client, ORG_EMP_EMAIL, ORG_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        body = me.json()
        assert body["org_level_code"] == "L5"
        assert body["org_level_name"] == "Professional"
