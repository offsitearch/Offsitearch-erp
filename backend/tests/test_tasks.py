import pytest
from sqlalchemy import select
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

LEAD_EMAIL = "task.lead@studioerp.dev"
LEAD_PASSWORD = "task-lead-pass-123"
EMP_EMAIL = "task.emp@studioerp.dev"
EMP_PASSWORD = "task-emp-pass-123"
ASSIGNEE_EMAIL = "task.assignee@studioerp.dev"
ASSIGNEE_PASSWORD = "task-assignee-pass-123"


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
async def task_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Task Lead", "L3")


@pytest.fixture(scope="session")
async def task_employee():
    return await _create_user(EMP_EMAIL, EMP_PASSWORD, "Task Employee")


@pytest.fixture(scope="session")
async def task_assignee():
    return await _create_user(ASSIGNEE_EMAIL, ASSIGNEE_PASSWORD, "Task Assignee")


async def test_create_task_and_board(task_lead: User, task_assignee: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {lead_token}"}
        created = await client.post(
            "/api/v1/tasks",
            json={
                "title": "Design schematic section",
                "priority": "high",
                "assigned_to": task_assignee.id,
                "due_date": "2026-09-15",
            },
            headers=headers,
        )
        assert created.status_code == 201
        body = created.json()
        assert body["title"] == "Design schematic section"
        assert body["priority"] == "high"
        assert body["status"] == "todo"
        assert body["assignee_name"] == "Task Assignee"

        board = await client.get("/api/v1/tasks/board", headers=headers)
        assert board.status_code == 200
        columns = {col["status"]: col["tasks"] for col in board.json()["columns"]}
        assert any(t["id"] == body["id"] for t in columns["todo"])


async def test_employee_cannot_create_task(task_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Nope"},
            headers=headers,
        )
        assert response.status_code == 403


async def test_assignee_updates_status_and_checklist(task_lead: User, task_assignee: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        assignee_token = await _login(client, ASSIGNEE_EMAIL, ASSIGNEE_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        assignee_headers = {"Authorization": f"Bearer {assignee_token}"}

        created = await client.post(
            "/api/v1/tasks",
            json={"title": "Update permit drawings", "assigned_to": task_assignee.id},
            headers=lead_headers,
        )
        task_id = created.json()["id"]

        updated = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "in_progress"},
            headers=assignee_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "in_progress"

        item = await client.post(
            f"/api/v1/tasks/{task_id}/checklist",
            json={"text": "Collect plot survey"},
            headers=assignee_headers,
        )
        assert item.status_code == 201
        item_id = item.json()["id"]

        toggled = await client.patch(
            f"/api/v1/tasks/{task_id}/checklist/{item_id}",
            headers=assignee_headers,
        )
        assert toggled.status_code == 200
        assert toggled.json()["is_done"] is True

        detail = await client.get(f"/api/v1/tasks/{task_id}", headers=assignee_headers)
        assert detail.status_code == 200
        assert detail.json()["checklist"][0]["is_done"] is True


async def test_lead_cannot_create_task_for_unled_project(task_lead: User) -> None:
    from app.modules.projects.schemas import ProjectCreate
    from app.modules.projects import service as project_service
    from app.utils.enums import ProjectType

    async with AsyncSessionLocal() as db:
        project = await project_service.create_project(
            db,
            ProjectCreate(
                name="Unled Project",
                project_type=ProjectType.RESIDENTIAL,
                status="draft",
            ),
        )
        project_id = project.id

    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Nope", "project_id": project_id},
            headers=headers,
        )
        assert response.status_code == 403


async def test_delete_task(task_lead: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {lead_token}"}
        created = await client.post(
            "/api/v1/tasks",
            json={"title": "Temporary task"},
            headers=headers,
        )
        task_id = created.json()["id"]
        deleted = await client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
        assert deleted.status_code == 204
        gone = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert gone.status_code == 404


async def test_employee_sees_only_own_and_project_tasks(
    task_employee: User, task_assignee: User
) -> None:
    from app.modules.projects.schemas import ProjectCreate
    from app.modules.projects import service as project_service
    from app.utils.enums import ProjectType

    async with _client() as client:
        super_token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        super_headers = {"Authorization": f"Bearer {super_token}"}

        async with AsyncSessionLocal() as db:
            project = await project_service.create_project(
                db,
                ProjectCreate(
                    name="Shared Task Project",
                    project_type=ProjectType.RESIDENTIAL,
                    status="draft",
                    team=[{"user_id": task_employee.id, "role": "Draftsman"}],
                ),
            )
            project_id = project.id
            other_project = await project_service.create_project(
                db,
                ProjectCreate(
                    name="Unrelated Task Project",
                    project_type=ProjectType.RESIDENTIAL,
                    status="draft",
                ),
            )
            other_project_id = other_project.id

        on_project = await client.post(
            "/api/v1/tasks",
            json={
                "title": "On my project",
                "project_id": project_id,
                "assigned_to": task_employee.id,
            },
            headers=super_headers,
        )
        mine = await client.post(
            "/api/v1/tasks",
            json={"title": "Mine standalone", "assigned_to": task_employee.id},
            headers=super_headers,
        )
        theirs = await client.post(
            "/api/v1/tasks",
            json={"title": "Theirs standalone", "assigned_to": task_assignee.id},
            headers=super_headers,
        )
        assert on_project.status_code == 201
        assert mine.status_code == 201
        assert theirs.status_code == 201
        visible = {on_project.json()["id"], mine.json()["id"]}
        hidden = theirs.json()["id"]

        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}

        listing = await client.get("/api/v1/tasks", headers=emp_headers)
        assert listing.status_code == 200
        ids = [t["id"] for t in listing.json()["items"]]
        assert visible <= set(ids)
        assert hidden not in ids

        board = await client.get("/api/v1/tasks/board", headers=emp_headers)
        board_ids = {t["id"] for col in board.json()["columns"] for t in col["tasks"]}
        assert visible <= board_ids
        assert hidden not in board_ids

        unrelated_board = await client.get(
            f"/api/v1/tasks/board?project_id={other_project_id}", headers=emp_headers
        )
        assert unrelated_board.status_code == 404

        hidden_detail = await client.get(f"/api/v1/tasks/{hidden}", headers=emp_headers)
        assert hidden_detail.status_code == 404

        mine_detail = await client.get(f"/api/v1/tasks/{mine.json()['id']}", headers=emp_headers)
        assert mine_detail.status_code == 200


async def test_employee_cannot_reassign_own_task(task_employee: User, task_assignee: User) -> None:
    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        emp_token = await _login(client, EMP_EMAIL, EMP_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        created = await client.post(
            "/api/v1/tasks",
            json={"title": "Own task", "assigned_to": task_employee.id},
            headers=lead_headers,
        )
        task_id = created.json()["id"]
        reassign = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"assigned_to": task_assignee.id},
            headers=emp_headers,
        )
        assert reassign.status_code == 403
