"""Timesheet suite: today-only logging, per-day approval flow, exports, reports."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, Project, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

LEAD_EMAIL = "ts.lead@studioerp.dev"
LEAD_PASSWORD = "ts-lead-pass-123"

HEAD_EMAIL = "ts.head@studioerp.dev"
HEAD_PASSWORD = "ts-head-pass-123"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login(client: AsyncClient, email: str, password: str) -> str:
    from app.db.session import AsyncSessionLocal as _DB
    from app.models import User as _User

    async with _DB() as db:
        user_id = await db.scalar(select(_User.login_id).where(_User.email == email))
    assert user_id is not None, f"no user with email {email}"
    response = await client.post(
        "/api/v1/auth/login", json={"user_id": user_id, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _create_user(
    email: str,
    password: str,
    name: str,
    level_code: str | None = None,
    department_id: int | None = None,
) -> User:
    async with AsyncSessionLocal() as db:
        level_id = None
        if level_code is not None:
            level_id = await db.scalar(select(OrgLevel.id).where(OrgLevel.code == level_code))
        user = User(
            email=email,
            name=name,
            org_level_id=level_id,
            department_id=department_id,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _make_department(name: str) -> int:
    from app.models import Department

    async with AsyncSessionLocal() as db:
        dept = Department(name=f"{name}-{uuid4().hex[:6]}")
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        return dept.id


@pytest.fixture(scope="session")
async def ts_lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Timesheet Lead", "L3")


@pytest.fixture(scope="session")
async def ts_head():
    """L2 department head: the floor for cross-user exports and reports."""
    return await _create_user(HEAD_EMAIL, HEAD_PASSWORD, "Timesheet Head", "L2")


@pytest.fixture
async def ts_employee():
    """A fresh employee per test so each owns its own current-week sheet."""
    tag = uuid4().hex[:8]
    email = f"ts.emp.{tag}@studioerp.dev"
    return await _create_user(email, "ts-emp-pass-123", f"TS Emp {tag}", "L5")


async def _make_project(name: str) -> int:
    from app.modules.projects.schemas import ProjectCreate
    from app.modules.projects import service as project_service
    from app.utils.enums import ProjectType

    async with AsyncSessionLocal() as db:
        project = await project_service.create_project(
            db,
            ProjectCreate(
                name=f"{name}-{uuid4().hex[:6]}",
                project_type=ProjectType.RESIDENTIAL,
                status="draft",
            ),
        )
        return project.id


def _today() -> date:
    return date.today()


def _week_start() -> str:
    today = _today()
    return (today - timedelta(days=today.weekday())).isoformat()


def _past_day_in_week() -> str | None:
    """Yesterday when it sits inside the same ISO week, else None (Mondays)."""
    yesterday = _today() - timedelta(days=1)
    if yesterday.weekday() <= _today().weekday() and (
        yesterday - timedelta(days=yesterday.weekday())
    ) == (_today() - timedelta(days=_today().weekday())):
        return yesterday.isoformat()
    return None


async def _save_week(client: AsyncClient, headers: dict, entries: list[dict]) -> object:
    return await client.put(
        "/api/v1/timesheets/week",
        json={"week_start": _week_start(), "entries": entries},
        headers=headers,
    )


async def _login_headers(client: AsyncClient, email: str, password: str) -> dict:
    return {"Authorization": f"Bearer {await _login(client, email, password)}"}


async def test_full_flow_with_pdf_receipt(ts_lead: User, ts_employee: User) -> None:
    project_id = await _make_project("Flow Project")

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)

        # Empty draft auto-creates for the current week.
        week = await client.get("/api/v1/timesheets/week", headers=emp_headers)
        assert week.status_code == 200
        sheet = week.json()
        assert sheet["status"] == "draft"
        assert sheet["entries"] == []
        assert sheet["days"] == []

        # Submitting an empty sheet is rejected.
        empty_submit = await client.post(
            f"/api/v1/timesheets/{sheet['id']}/submit", headers=emp_headers
        )
        assert empty_submit.status_code == 400

        # Drafts only accept TODAY's date.
        past = (
            _past_day_in_week() or (_today() - timedelta(days=_today().weekday() + 3)).isoformat()
        )
        assert past != _today().isoformat()
        denied_past = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": past, "hours": 1}],
        )
        assert denied_past.status_code == 400

        saved = await _save_week(
            client,
            emp_headers,
            [
                {
                    "project_id": project_id,
                    "date": _today().isoformat(),
                    "hours": 4.5,
                    "description": "Concept sketches",
                },
                {
                    "project_id": project_id,
                    "date": _today().isoformat(),
                    "hours": 3.25,
                    "description": "Client revisions",
                },
            ],
        )
        assert saved.status_code == 200
        body = saved.json()
        assert len(body["entries"]) == 2
        assert Decimal(str(body["total_hours"])) == Decimal("7.75")
        # Day rows mirror the logging: one draft day carrying both entries.
        assert len(body["days"]) == 1
        assert body["days"][0]["status"] == "draft"

        submitted = await client.post(
            f"/api/v1/timesheets/{body['id']}/submit", headers=emp_headers
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "submitted"
        assert submitted.json()["days"][0]["status"] == "submitted"

        # Editing a locked (submitted) day is blocked…
        locked = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": _today().isoformat(), "hours": 1}],
        )
        assert locked.status_code == 409

        # …while an empty save against a fully-locked sheet is a harmless no-op.
        noop = await _save_week(client, emp_headers, [])
        assert noop.status_code == 200

        # The sheet shows up in the lead's queue.
        queue = await client.get("/api/v1/timesheets/pending", headers=lead_headers)
        assert queue.status_code == 200
        assert any(row["id"] == body["id"] for row in queue.json()["items"])

        approved = await client.post(
            f"/api/v1/timesheets/{body['id']}/approve", headers=lead_headers
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["days"][0]["status"] == "approved"

        # Approved hours feed the project KPI exactly once.
        async with AsyncSessionLocal() as db:
            hours = await db.scalar(select(Project.hours_logged).where(Project.id == project_id))
        assert Decimal(hours) == Decimal("7.75")

        repeat_approve = await client.post(
            f"/api/v1/timesheets/{body['id']}/approve", headers=lead_headers
        )
        assert repeat_approve.status_code == 409
        async with AsyncSessionLocal() as db:
            hours_again = await db.scalar(
                select(Project.hours_logged).where(Project.id == project_id)
            )
        assert Decimal(hours_again) == Decimal("7.75")

        # ── PDF receipt ──
        own_pdf = await client.get(f"/api/v1/timesheets/{body['id']}/pdf", headers=emp_headers)
        assert own_pdf.status_code == 200
        assert own_pdf.headers["content-type"].startswith("application/pdf")
        assert own_pdf.content.startswith(b"%PDF")

        lead_pdf = await client.get(f"/api/v1/timesheets/{body['id']}/pdf", headers=lead_headers)
        assert lead_pdf.status_code == 200


async def test_reject_and_fix_window(ts_lead: User, ts_employee: User) -> None:
    project_id = await _make_project("Reject Project")

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)

        saved = await _save_week(
            client,
            emp_headers,
            [
                {
                    "project_id": project_id,
                    "date": _today().isoformat(),
                    "hours": 2.0,
                    "description": "Admin",
                }
            ],
        )
        sheet_id = saved.json()["id"]
        assert (
            await client.post(f"/api/v1/timesheets/{sheet_id}/submit", headers=emp_headers)
        ).status_code == 200

        rejected = await client.post(
            f"/api/v1/timesheets/{sheet_id}/reject",
            json={"reason": "Please split admin time per project"},
            headers=lead_headers,
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"
        assert rejected.json()["days"][0]["status"] == "rejected"

        # Only the REJECTED day reopens — stale past drafts stay locked.
        past_day = _past_day_in_week()
        if past_day is not None:
            stale = await _save_week(
                client,
                emp_headers,
                [{"project_id": project_id, "date": past_day, "hours": 3.0}],
            )
            assert stale.status_code == 400

        # The rejected day itself may be corrected, then resubmitted.
        resaved = await _save_week(
            client,
            emp_headers,
            [
                {
                    "project_id": project_id,
                    "date": _today().isoformat(),
                    "hours": 2.0,
                    "description": "Studio admin",
                },
                {
                    "project_id": project_id,
                    "date": _today().isoformat(),
                    "hours": 1.0,
                    "description": "Coordination",
                },
            ],
        )
        assert resaved.status_code == 200
        assert len(resaved.json()["entries"]) == 2

        resubmitted = await client.post(
            f"/api/v1/timesheets/{sheet_id}/submit", headers=emp_headers
        )
        assert resubmitted.status_code == 200
        assert resubmitted.json()["status"] == "submitted"
        assert resubmitted.json()["rejection_reason"] is None


async def test_single_day_review(ts_lead: User, ts_employee: User) -> None:
    """Day-scoped submit/approve/reject with per-day KPI credit."""
    project_id = await _make_project("Day Review Project")
    today_iso = _today().isoformat()

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)

        saved = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": today_iso, "hours": 6}],
        )
        sheet_id = saved.json()["id"]

        # Owner submits just this day.
        day_submitted = await client.post(
            f"/api/v1/timesheets/{sheet_id}/days/{today_iso}/submit",
            headers=emp_headers,
        )
        assert day_submitted.status_code == 200
        body = day_submitted.json()
        assert body["status"] == "submitted"
        assert body["days"][0]["status"] == "submitted"

        # Re-submitting the same day is a 409.
        repeat = await client.post(
            f"/api/v1/timesheets/{sheet_id}/days/{today_iso}/submit",
            headers=emp_headers,
        )
        assert repeat.status_code == 409

        # Lead approves the single day.
        day_approved = await client.post(
            f"/api/v1/timesheets/{sheet_id}/days/{today_iso}/approve",
            headers=lead_headers,
        )
        assert day_approved.status_code == 200
        assert day_approved.json()["status"] == "approved"

        async with AsyncSessionLocal() as db:
            hours = await db.scalar(select(Project.hours_logged).where(Project.id == project_id))
        assert Decimal(hours) == Decimal("6")


async def test_rejected_day_reopens_for_edit(ts_lead: User, ts_employee: User) -> None:
    project_id = await _make_project("Day Reject Project")
    today_iso = _today().isoformat()

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)

        saved = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": today_iso, "hours": 5}],
        )
        sheet_id = saved.json()["id"]
        await client.post(
            f"/api/v1/timesheets/{sheet_id}/days/{today_iso}/submit", headers=emp_headers
        )

        day_rejected = await client.post(
            f"/api/v1/timesheets/{sheet_id}/days/{today_iso}/reject",
            json={"reason": "Wrong project"},
            headers=lead_headers,
        )
        assert day_rejected.status_code == 200
        body = day_rejected.json()
        assert body["status"] == "rejected"
        assert body["days"][0]["status"] == "rejected"
        assert body["days"][0]["rejection_reason"] == "Wrong project"

        # The rejected day is editable again; corrected hours survive.
        fixed = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": today_iso, "hours": 7}],
        )
        assert fixed.status_code == 200
        assert len(fixed.json()["entries"]) == 1

        # No KPI credit yet — approval never happened.
        async with AsyncSessionLocal() as db:
            hours = await db.scalar(select(Project.hours_logged).where(Project.id == project_id))
        assert not hours


async def test_month_export_permissions_and_formats(
    ts_lead: User, ts_head: User, ts_employee: User
) -> None:
    project_id = await _make_project("Export Project")

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)
        head_headers = await _login_headers(client, HEAD_EMAIL, HEAD_PASSWORD)

        saved = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": _today().isoformat(), "hours": 3}],
        )
        assert saved.status_code == 200

        params = {
            "year": str(_today().year),
            "month": str(_today().month),
        }

        # Own-data XLSX export (zip container).
        xlsx = await client.get(
            "/api/v1/timesheets/export/month",
            params={**params, "format": "xlsx"},
            headers=emp_headers,
        )
        assert xlsx.status_code == 200
        assert xlsx.content.startswith(b"PK")

        # Own-data PDF export.
        pdf = await client.get(
            "/api/v1/timesheets/export/month",
            params={**params, "format": "pdf"},
            headers=emp_headers,
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        # Employees cannot export someone else's data…
        forbidden = await client.get(
            "/api/v1/timesheets/export/month",
            params={**params, "user_id": str(ts_lead.id)},
            headers=emp_headers,
        )
        assert forbidden.status_code == 403

        # …and an L3 lead is still below the L2 floor for other users.
        lead_forbidden = await client.get(
            "/api/v1/timesheets/export/month",
            params={**params, "user_id": str(ts_employee.id)},
            headers=lead_headers,
        )
        assert lead_forbidden.status_code == 403

        # …but L2+ can.
        allowed = await client.get(
            "/api/v1/timesheets/export/month",
            params={**params, "user_id": str(ts_employee.id)},
            headers=head_headers,
        )
        assert allowed.status_code == 200


async def test_timesheets_report_access(ts_head: User, ts_employee: User) -> None:
    project_id = await _make_project("Report Project")

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        head_headers = await _login_headers(client, HEAD_EMAIL, HEAD_PASSWORD)

        saved = await _save_week(
            client,
            emp_headers,
            [
                {
                    "project_id": project_id,
                    "date": _today().isoformat(),
                    "hours": 4,
                }
            ],
        )
        assert saved.status_code == 200

        params = {"from_date": _week_start(), "to_date": _today().isoformat()}

        # L5 staff are below the L2 floor; so is an L3 lead.
        denied = await client.get("/api/v1/reports/timesheets", params=params, headers=emp_headers)
        assert denied.status_code == 403

        ok = await client.get("/api/v1/reports/timesheets", params=params, headers=head_headers)
        assert ok.status_code == 200
        body = ok.json()
        assert Decimal(str(body["summary"]["total_hours"])) >= Decimal("4")
        matching = [r for r in body["rows"] if r["employee_name"] == ts_employee.name]
        assert matching and sum(r["hours"] for r in matching) >= 4


async def test_entry_validation_rules(ts_employee: User) -> None:
    project_id = await _make_project("Rules Project")
    other_project_id = await _make_project("Other Rules Project")
    today_iso = _today().isoformat()

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")

        # Entry far outside the selected week.
        outside = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": "2020-01-01", "hours": 1}],
        )
        assert outside.status_code == 400

        # Future dates can never be logged.
        tomorrow = (_today() + timedelta(days=1)).isoformat()
        future = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": tomorrow, "hours": 1}],
        )
        assert future.status_code == 400

        # Past dates are limited to the rejected fix window.
        past_day = _past_day_in_week()
        if past_day is not None:
            stale = await _save_week(
                client,
                emp_headers,
                [{"project_id": project_id, "date": past_day, "hours": 1}],
            )
            assert stale.status_code == 400

        # Multiple same-day entries across projects are fine.
        multi = await _save_week(
            client,
            emp_headers,
            [
                {"project_id": project_id, "date": today_iso, "hours": 3},
                {"project_id": other_project_id, "date": today_iso, "hours": 2},
            ],
        )
        assert multi.status_code == 200

        from app.modules.tasks.schemas import TaskCreate
        from app.modules.tasks import service as task_service

        async with AsyncSessionLocal() as db:
            task = await task_service.create_task(
                db,
                TaskCreate(title="Rules task", project_id=project_id),
                ts_employee,
            )
            task_id = task.id

        wrong_task = await _save_week(
            client,
            emp_headers,
            [
                {
                    "project_id": other_project_id,
                    "task_id": task_id,
                    "date": today_iso,
                    "hours": 1,
                }
            ],
        )
        assert wrong_task.status_code == 400

        right_task = await _save_week(
            client,
            emp_headers,
            [
                {
                    "project_id": project_id,
                    "task_id": task_id,
                    "date": today_iso,
                    "hours": 2,
                }
            ],
        )
        assert right_task.status_code == 200

        # More than 24h on a single day — no longer blocked.
        overloaded = await _save_week(
            client,
            emp_headers,
            [
                {"project_id": project_id, "date": today_iso, "hours": 20},
                {"project_id": project_id, "date": today_iso, "hours": 6},
            ],
        )
        assert overloaded.status_code == 200


async def test_permissions_and_privacy(ts_lead: User, ts_employee: User) -> None:
    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)

        saved = await _save_week(client, emp_headers, [])
        sheet_id = saved.json()["id"]

        # Staff cannot read someone else's sheet…
        detail = await client.get(f"/api/v1/timesheets/{sheet_id}", headers=lead_headers)
        assert detail.status_code == 200  # …but leads can.

        # Employees cannot access the pending queue or the admin listing.
        assert (
            await client.get("/api/v1/timesheets/pending", headers=emp_headers)
        ).status_code == 403
        assert (await client.get("/api/v1/timesheets", headers=emp_headers)).status_code == 403

        # Self-approval is blocked below the CEO.
        own = await client.get("/api/v1/timesheets/week", headers=lead_headers)
        own_id = own.json()["id"]
        self_approve = await client.post(
            f"/api/v1/timesheets/{own_id}/approve", headers=lead_headers
        )
        assert self_approve.status_code in (403, 409)

        # Approving an unsubmitted (draft) sheet is invalid.
        cross = await client.post(f"/api/v1/timesheets/{sheet_id}/approve", headers=lead_headers)
        assert cross.status_code == 409


async def test_review_hierarchy_rules(ts_lead: User, ts_employee: User) -> None:
    """Reviewers only act on strictly junior levels; the CEO (L0) is exempt."""
    tag = uuid4().hex[:8]
    peer = await _create_user(
        f"ts.peer.{tag}@studioerp.dev", "ts-peer-pass-123", f"TS Peer {tag}", "L3"
    )
    owner = await _create_user(
        f"ts.owner.{tag}@studioerp.dev", "ts-owner-pass-123", f"TS Owner {tag}", "L3"
    )
    ceo = await _create_user(
        f"ts.ceo.{tag}@studioerp.dev", "ts-ceo-pass-123", f"TS CEO {tag}", "L0"
    )
    project_id = await _make_project("Hierarchy Project")

    async with _client() as client:
        owner_headers = await _login_headers(client, owner.email, "ts-owner-pass-123")
        peer_headers = await _login_headers(client, peer.email, "ts-peer-pass-123")
        ceo_headers = await _login_headers(client, ceo.email, "ts-ceo-pass-123")

        # Same-level sheet: submitted by another L3.
        saved = await _save_week(
            client,
            owner_headers,
            [{"project_id": project_id, "date": _today().isoformat(), "hours": 2}],
        )
        assert saved.status_code == 200
        sheet_id = saved.json()["id"]
        submitted = await client.post(
            f"/api/v1/timesheets/{sheet_id}/submit", headers=owner_headers
        )
        assert submitted.status_code == 200

        # A same-level L3 cannot review: not in their queue, action 403.
        queue = await client.get("/api/v1/timesheets/pending", headers=peer_headers)
        assert queue.status_code == 200
        assert all(row["id"] != sheet_id for row in queue.json()["items"])
        peer_approve = await client.post(
            f"/api/v1/timesheets/{sheet_id}/approve", headers=peer_headers
        )
        assert peer_approve.status_code == 403
        assert "lower levels" in peer_approve.json()["detail"]

        # The strictly-senior lead sees a junior (L5) sheet in their queue.
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        junior_saved = await _save_week(
            client,
            emp_headers,
            [{"project_id": project_id, "date": _today().isoformat(), "hours": 2}],
        )
        assert junior_saved.status_code == 200
        junior_id = junior_saved.json()["id"]
        junior_submit = await client.post(
            f"/api/v1/timesheets/{junior_id}/submit", headers=emp_headers
        )
        assert junior_submit.status_code == 200
        lead_headers = await _login_headers(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_queue = await client.get("/api/v1/timesheets/pending", headers=lead_headers)
        assert any(row["id"] == junior_id for row in lead_queue.json()["items"])

        # The CEO sits above the hierarchy and may approve anyone…
        ceo_approve = await client.post(
            f"/api/v1/timesheets/{junior_id}/approve", headers=ceo_headers
        )
        assert ceo_approve.status_code == 200

        # …including themselves.
        own_save = await client.put(
            "/api/v1/timesheets/week",
            json={
                "week_start": _week_start(),
                "entries": [{"project_id": project_id, "date": _today().isoformat(), "hours": 1}],
            },
            headers=ceo_headers,
        )
        assert own_save.status_code == 200
        own_id = own_save.json()["id"]
        own_submit = await client.post(f"/api/v1/timesheets/{own_id}/submit", headers=ceo_headers)
        assert own_submit.status_code == 200
        self_approve = await client.post(
            f"/api/v1/timesheets/{own_id}/approve", headers=ceo_headers
        )
        assert self_approve.status_code == 200


async def test_timesheet_detail_report(ts_head: User, ts_employee: User) -> None:
    """Per-employee detail report: day/week/month grouping, filters, exports."""
    dept_id = await _make_department("Report Dept")
    other_dept_id = await _make_department("Other Dept")
    tag = uuid4().hex[:8]
    depped = await _create_user(
        f"ts.dept.{tag}@studioerp.dev",
        "ts-dept-pass-123",
        f"TS Dept Emp {tag}",
        "L5",
        department_id=dept_id,
    )
    project_id = await _make_project("Detail Project")

    async with _client() as client:
        emp_headers = await _login_headers(client, ts_employee.email, "ts-emp-pass-123")
        depped_headers = await _login_headers(client, depped.email, "ts-dept-pass-123")
        head_headers = await _login_headers(client, HEAD_EMAIL, HEAD_PASSWORD)

        for headers in (emp_headers, depped_headers):
            saved = await client.put(
                "/api/v1/timesheets/week",
                json={
                    "week_start": _week_start(),
                    "entries": [
                        {"project_id": project_id, "date": _today().isoformat(), "hours": 2},
                        {"project_id": project_id, "date": _today().isoformat(), "hours": 1},
                    ],
                },
                headers=headers,
            )
            assert saved.status_code == 200

        today = _today().isoformat()

        # Day view lists every entry line.
        day_report = await client.get(
            "/api/v1/reports/timesheets",
            params={"from_date": today, "to_date": today, "group_by": "day"},
            headers=head_headers,
        )
        assert day_report.status_code == 200
        body = day_report.json()
        assert body["summary"]["group_by"] == "day"
        assert len(body["employees"]) == 2
        first = next(e for e in body["employees"] if e["employee_name"] == depped.name)
        assert first["department"] is not None
        assert first["total_hours"] == 3.0
        assert len(first["groups"]) == 1
        assert len(first["groups"][0]["rows"]) == 2

        # Single-employee filter.
        solo = await client.get(
            "/api/v1/reports/timesheets",
            params={
                "from_date": today,
                "to_date": today,
                "employee_id": depped.id,
            },
            headers=head_headers,
        )
        assert solo.status_code == 200
        solo_body = solo.json()
        assert len(solo_body["employees"]) == 1
        assert solo_body["employees"][0]["user_id"] == depped.id

        # Department filter includes the member and excludes the level-less peer.
        by_dept = await client.get(
            "/api/v1/reports/timesheets",
            params={"from_date": today, "to_date": today, "department_id": dept_id},
            headers=head_headers,
        )
        assert by_dept.status_code == 200
        assert [e["user_id"] for e in by_dept.json()["employees"]] == [depped.id]
        empty = await client.get(
            "/api/v1/reports/timesheets",
            params={"from_date": today, "to_date": today, "department_id": other_dept_id},
            headers=head_headers,
        )
        assert empty.json()["employees"] == []

        # Week/month views roll entries up per project within the period.
        for group_by in ("week", "month"):
            rolled = await client.get(
                "/api/v1/reports/timesheets",
                params={
                    "from_date": today,
                    "to_date": today,
                    "group_by": group_by,
                    "employee_id": depped.id,
                },
                headers=head_headers,
            )
            assert rolled.status_code == 200
            groups = rolled.json()["employees"][0]["groups"]
            assert len(groups) == 1
            assert groups[0]["hours"] == 3.0
            assert len(groups[0]["rows"]) == 1  # both entries share one project

        # Exports: PDF magic bytes + XLSX PK zip header; staff still blocked.
        pdf = await client.get(
            "/api/v1/reports/timesheets",
            params={"from_date": today, "to_date": today, "format": "pdf"},
            headers=head_headers,
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        xlsx = await client.get(
            "/api/v1/reports/timesheets",
            params={"from_date": today, "to_date": today, "format": "xlsx"},
            headers=head_headers,
        )
        assert xlsx.status_code == 200
        assert xlsx.content.startswith(b"PK")
        denied = await client.get(
            "/api/v1/reports/timesheets",
            params={"from_date": today},
            headers=emp_headers,
        )
        assert denied.status_code == 403
