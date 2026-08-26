import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User
from app.modules.projects.schemas import ProjectCreate
from app.modules.projects import service as project_service
from app.utils.enums import ProjectType

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

LEAD_EMAIL = "proj.lead@studioerp.dev"
LEAD_PASSWORD = "proj-lead-pass-123"
MEMBER_EMAIL = "proj.member@studioerp.dev"
MEMBER_PASSWORD = "proj-member-pass-123"
EMP_EMAIL = "proj.emp@studioerp.dev"
EMP_PASSWORD = "proj-emp-pass-123"


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
async def project_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Project Lead", "L3")


@pytest.fixture(scope="session")
async def team_member():
    return await _create_user(MEMBER_EMAIL, MEMBER_PASSWORD, "Team Member")


@pytest.fixture(scope="session")
async def regular_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "Regular Employee")


async def _make_project(admin_token: str) -> dict:
    async with _client() as client:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.post(
            "/api/v1/projects",
            json={
                "name": "Test Residential Villa",
                "project_type": "residential",
                "status": "draft",
            },
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()


async def test_create_project_auto_generates_phases(project_lead: User) -> None:
    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {super_token}"}
        payload = {
            "name": "Residential Template Check",
            "project_type": "residential",
            "start_date": "2026-09-01",
            "end_date": "2027-02-28",
        }
        created = await client.post("/api/v1/projects", json=payload, headers=headers)
        assert created.status_code == 201
        body = created.json()
        assert body["project_code"].startswith("ARC-2026-")
        assert len(body["phases"]) == 6
        assert body["phases"][0]["name"] == "Concept"
        assert body["phases"][-1]["name"] == "Construction Administration"
        assert body["phases"][0]["start_date"] == "2026-09-01"
        assert body["progress_pct"] == "0.00"


async def test_create_project_bad_client_404(project_lead: User) -> None:
    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {super_token}"}
        response = await client.post(
            "/api/v1/projects",
            json={"name": "Bad Client Project", "project_type": "commercial", "client_id": 99999},
            headers=headers,
        )
        assert response.status_code == 404


async def test_employee_cannot_create_project(regular_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/projects",
            json={"name": "Nope", "project_type": "interior"},
            headers=headers,
        )
        assert response.status_code == 403


async def test_list_projects_filters(project_lead: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        listing = await client.get("/api/v1/projects?project_type=residential", headers=headers)
        assert listing.status_code == 200
        assert all(item["project_type"] == "residential" for item in listing.json()["items"])
        assert listing.json()["total"] >= 1


async def test_team_add_duplicate_and_remove(project_lead: User, team_member: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        project = await _make_project(token)

        added = await client.post(
            f"/api/v1/projects/{project['id']}/team",
            json={"user_id": team_member.id, "role": "Architect"},
            headers=headers,
        )
        assert added.status_code == 201
        assert added.json()["name"] == "Team Member"

        duplicate = await client.post(
            f"/api/v1/projects/{project['id']}/team",
            json={"user_id": team_member.id, "role": "Architect"},
            headers=headers,
        )
        assert duplicate.status_code == 409

        removed = await client.delete(
            f"/api/v1/projects/{project['id']}/team/{team_member.id}", headers=headers
        )
        assert removed.status_code == 204


async def test_phase_update_recomputes_progress(project_lead: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        project = await _make_project(token)
        first_phase = project["phases"][0]

        resp = await client.patch(
            f"/api/v1/projects/{project['id']}/phases/{first_phase['id']}",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 200

        updated = await client.patch(
            f"/api/v1/projects/{project['id']}/phases/{first_phase['id']}",
            json={"status": "completed", "completion_pct": 100},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "completed"

        detail = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)
        assert detail.json()["progress_pct"] == "16.67"


async def test_delete_phase_reorders_and_recomputes(project_lead: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        project = await _make_project(token)
        phases = project["phases"]
        _, second, third = phases[0], phases[1], phases[2]

        await client.patch(
            f"/api/v1/projects/{project['id']}/phases/{third['id']}",
            json={"status": "in_progress"},
            headers=headers,
        )

        await client.patch(
            f"/api/v1/projects/{project['id']}/phases/{third['id']}",
            json={"status": "completed", "completion_pct": 100},
            headers=headers,
        )

        deleted = await client.delete(
            f"/api/v1/projects/{project['id']}/phases/{second['id']}", headers=headers
        )
        assert deleted.status_code == 204

        detail = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)
        body = detail.json()
        assert len(body["phases"]) == 5
        assert body["phases"][1]["id"] == third["id"]
        assert [p["order_index"] for p in body["phases"]] == [0, 1, 2, 3, 4]
        assert body["progress_pct"] == "20.00"

        not_found = await client.delete(
            f"/api/v1/projects/{project['id']}/phases/{second['id']}", headers=headers
        )
        assert not_found.status_code == 404


async def test_timeline_and_templates(project_lead: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        project = await _make_project(token)

        timeline = await client.get(f"/api/v1/projects/{project['id']}/timeline", headers=headers)
        assert timeline.status_code == 200
        assert len(timeline.json()["rows"]) == 6

        templates = await client.get("/api/v1/projects/templates", headers=headers)
        assert templates.status_code == 200
        assert len(templates.json()) == 8


async def test_project_permissions(project_lead: User, regular_employee: User) -> None:
    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        super_headers = {"Authorization": f"Bearer {super_token}"}
        project = await _make_project(super_token)

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        forbidden = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"priority": "high"},
            headers=emp_headers,
        )
        assert forbidden.status_code == 403

        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        not_their_project = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"priority": "high"},
            headers=lead_headers,
        )
        assert not_their_project.status_code == 403

        assigned = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"project_lead_id": project_lead.id},
            headers=super_headers,
        )
        assert assigned.status_code == 200

        ok = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"priority": "high"},
            headers=lead_headers,
        )
        assert ok.status_code == 200
        assert ok.json()["project_lead_id"] == project_lead.id

        admin_no_delete = await client.delete(
            f"/api/v1/projects/{project['id']}", headers=lead_headers
        )
        assert admin_no_delete.status_code == 403

        deleted = await client.delete(f"/api/v1/projects/{project['id']}", headers=super_headers)
        assert deleted.status_code == 204

        gone = await client.get(f"/api/v1/projects/{project['id']}", headers=super_headers)
        assert gone.status_code == 404


async def test_lead_create_is_always_self_led(project_lead: User, regular_employee: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {lead_token}"}
        created = await client.post(
            "/api/v1/projects",
            json={
                "name": "Lead Forced Self Project",
                "project_type": "residential",
                "status": "draft",
                "project_lead_id": regular_employee.id,
            },
            headers=headers,
        )
        assert created.status_code == 201
        assert created.json()["project_lead_id"] == project_lead.id


async def test_lead_cannot_reassign_project_lead(
    project_lead: User, regular_employee: User
) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {lead_token}"}
        created = await client.post(
            "/api/v1/projects",
            json={"name": "Lead Owned Project", "project_type": "residential", "status": "draft"},
            headers=headers,
        )
        assert created.status_code == 201

        reassign = await client.patch(
            f"/api/v1/projects/{created.json()['id']}",
            json={"project_lead_id": regular_employee.id},
            headers=headers,
        )
        assert reassign.status_code == 403


async def test_employee_sees_only_projects_they_are_part_of(
    regular_employee: User,
) -> None:
    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        super_headers = {"Authorization": f"Bearer {super_token}"}
        mine = await _make_project(super_token)
        other = await _make_project(super_token)

        added = await client.post(
            f"/api/v1/projects/{mine['id']}/team",
            json={"user_id": regular_employee.id, "role": "Draftsman"},
            headers=super_headers,
        )
        assert added.status_code == 201

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}

        listing = await client.get("/api/v1/projects", headers=emp_headers)
        assert listing.status_code == 200
        ids = [item["id"] for item in listing.json()["items"]]
        assert mine["id"] in ids
        assert other["id"] not in ids

        forbidden = await client.get(f"/api/v1/projects/{other['id']}", headers=emp_headers)
        assert forbidden.status_code == 404

        allowed = await client.get(f"/api/v1/projects/{mine['id']}", headers=emp_headers)
        assert allowed.status_code == 200
        assert allowed.json()["id"] == mine["id"]


async def test_service_create_with_team_and_progress(project_lead: User, team_member: User) -> None:
    from sqlalchemy import select

    from app.models import ProjectPhase, ProjectTeam

    async with AsyncSessionLocal() as db:
        project = await project_service.create_project(
            db,
            ProjectCreate(
                name="Service Level Project",
                project_type=ProjectType.RENOVATION,
                team=[{"user_id": team_member.id, "role": "Draftsman"}],
            ),
        )
        assert project.project_code.startswith("ARC-")

        phases = (
            (await db.execute(select(ProjectPhase).where(ProjectPhase.project_id == project.id)))
            .scalars()
            .all()
        )
        assert len(phases) == 6

        team = (
            (await db.execute(select(ProjectTeam).where(ProjectTeam.project_id == project.id)))
            .scalars()
            .all()
        )
        assert len(team) == 1
        assert team[0].role == "Draftsman"
