"""Full product walkthrough for the seeded Offsite Architecture organisation.

Every seeded person completes their own walkthrough: one-time password
sign-in -> forced password change -> daily work across every module they
can touch, plus proof that every permission they must NOT have is denied.

The organisation itself is created by ``app.seeds.org_bootstrap`` so the
test database matches the live database exactly (same login ids, emails,
reporting lines, promotions and business data).

Tests are ordered bottom-up (L6 staff first, CEO last) so each person's
one-time password is still unused when their own walkthrough starts;
cross-role steps use co-workers whose walkthrough already ran.

Run:  .venv\\Scripts\\python.exe -m pytest tests/test_walkthrough.py -v
"""

from __future__ import annotations

import asyncio
import base64
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.main import app
from app.seeds.data import HOLIDAYS as SEED_HOLIDAYS
from app.seeds.org_bootstrap import OrgBootstrapError, bootstrap_org

API = "/api/v1"

# 1x1 transparent PNG used for photo uploads.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
    "YGBgAAAABQABh6FO1AAAAABJRU5ErkJggg=="
)
PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<<>>\n%%EOF"


def _holiday_dates() -> set[date]:
    days = set()
    for h in SEED_HOLIDAYS:
        raw = h["date"] if isinstance(h, dict) else getattr(h, "date")
        days.add(raw if isinstance(raw, date) else date.fromisoformat(str(raw)))
    return days


HOLIDAY_DATES = _holiday_dates()


# --------------------------------------------------------------------------
# Org manifest + HTTP helpers
# --------------------------------------------------------------------------

_ORG: dict | None = None


def _reset_schema() -> None:
    """Wipe and re-migrate the test database.

    Full-suite runs share the session DB with every other test module, so
    by the time the walkthrough executes, employees created elsewhere make
    a clean bootstrap impossible. Recreate the schema from scratch instead.
    """
    import asyncpg
    from alembic import command
    from alembic.config import Config

    from app.db.init_db import init_db

    url = os.environ["DATABASE_URL"]
    dbname = url.rsplit("/", 1)[1]
    admin_dsn = "postgresql://" + url.split("://", 1)[1].rsplit("/", 1)[0] + "/postgres"

    async def _recreate() -> None:
        conn = await asyncpg.connect(admin_dsn)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
            await conn.execute(f'CREATE DATABASE "{dbname}"')
        finally:
            await conn.close()

    asyncio.run(_recreate())
    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(cfg, "head")
    asyncio.run(init_db())


def _org() -> dict:
    global _ORG
    if _ORG is None:
        try:
            _ORG = asyncio.run(bootstrap_org())
        except OrgBootstrapError:
            _reset_schema()
            _ORG = asyncio.run(bootstrap_org())
    return _ORG


@pytest.fixture(scope="session")
def org(database_setup) -> dict:
    return _org()


def who(org: dict, key: str) -> dict:
    """Manifest row by key ('ceo' included)."""
    if key == "ceo":
        return org["ceo"]
    return next(e for e in org["employees"] if e["key"] == key)


@asynccontextmanager
async def api():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def login(c: httpx.AsyncClient, login_id: str, password: str) -> dict:
    r = await c.post(f"{API}/auth/login", json={"user_id": login_id, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def bearer(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['access_token']}"}


async def first_login(c: httpx.AsyncClient, person: dict) -> dict:
    """The documented first-login walkthrough; returns fresh token payload."""
    data = await login(c, person["login_id"], person["temp_password"])
    assert data["user"]["must_change_password"] is True
    h = bearer(data)
    assert data["user"]["login_id"] == person["login_id"]
    assert data["user"]["email"] == person["email"]

    # Every business endpoint is gated until the password is changed...
    blocked = await c.get(f"{API}/dashboard/summary", headers=h)
    assert blocked.status_code == 403
    assert "Password change required" in blocked.json()["detail"]
    # ...but /auth stays reachable.
    me = await c.get(f"{API}/auth/me", headers=h)
    assert me.status_code == 200

    r = await c.post(
        f"{API}/auth/change-password",
        json={"current_password": person["temp_password"], "new_password": person["password"]},
        headers=h,
    )
    assert r.status_code == 200, r.text

    # The old access token is invalidated immediately (token_version bump).
    stale = await c.get(f"{API}/dashboard/summary", headers=h)
    assert stale.status_code == 401

    data2 = await login(c, person["login_id"], person["password"])
    assert data2["user"]["must_change_password"] is False
    return data2


async def ready(c: httpx.AsyncClient, person: dict) -> dict:
    """Auth headers for a co-worker whose walkthrough already ran."""
    data = await login(c, person["login_id"], person["password"])
    return bearer(data)


async def level_ids(c: httpx.AsyncClient, headers: dict) -> dict[str, int]:
    r = await c.get(f"{API}/org-levels", headers=headers)
    assert r.status_code == 200, r.text
    return {row["code"]: row["id"] for row in r.json()}


def working_days(count: int, start: date | None = None) -> list[date]:
    """Next N working days (Mon-Fri, skipping seeded holidays)."""
    days: list[date] = []
    d = (start or datetime.now().date()) + timedelta(days=1)
    while len(days) < count:
        if d.weekday() < 5 and d not in HOLIDAY_DATES:
            days.append(d)
        d += timedelta(days=1)
    return days


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def ensure_submitted_sheet(
    c: httpx.AsyncClient, headers: dict, project_id: int, hours: str = "3.5"
) -> dict:
    """Log today on a project and submit the weekly sheet.

    If the sheet was already locked by an earlier step of the walkthrough
    (a senior approved it, etc.) the current state is returned as-is.
    """
    today = datetime.now().date()
    saved = await c.put(
        f"{API}/timesheets/week",
        headers=headers,
        json={
            "week_start": monday_of(today).isoformat(),
            "entries": [
                {
                    "project_id": project_id,
                    "date": today.isoformat(),
                    "hours": hours,
                    "description": "Walkthrough entry",
                }
            ],
        },
    )
    if saved.status_code == 200 and saved.json()["status"] == "draft":
        submitted = await c.post(f"{API}/timesheets/{saved.json()['id']}/submit", headers=headers)
        assert submitted.status_code == 200, submitted.text
        return submitted.json()

    week = await c.get(f"{API}/timesheets/week", headers=headers)
    assert week.status_code == 200, week.text
    sheet = week.json()
    assert sheet["status"] in ("submitted", "approved"), (
        f"unexpected sheet status {sheet['status']}: {saved.text}"
    )
    return sheet


async def apply_casual_leave(
    c: httpx.AsyncClient, headers: dict, reason: str, day: date | None = None
) -> dict:
    """Apply for a single casual leave; pass ``day`` to dodge prior bookings."""
    if day is None:
        day = working_days(1)[0]
    r = await c.post(
        f"{API}/leaves",
        headers=headers,
        json={
            "leave_type": "casual",
            "from_date": day.isoformat(),
            "to_date": day.isoformat(),
            "reason": reason,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def client_payload(name: str) -> dict:
    return {
        "name": name,
        "client_type": "individual",
        "contact_person": name,
        "phone": "+91 90000 00000",
        "email": f"{name.split()[0].lower()}@example.com",
    }


def project_payload(name: str, client_id: int | None = None) -> dict:
    body = {"name": name, "project_type": "residential", "location": "Mumbai"}
    if client_id:
        body["client_id"] = client_id
    return body


def task_payload(title: str, project_id: int, assignee: int) -> dict:
    return {"title": title, "project_id": project_id, "assigned_to": assignee}


# --------------------------------------------------------------------------
# Cross-cutting auth flows
# --------------------------------------------------------------------------


async def test_refresh_and_logout_flow(org):
    person = who(org, "tara")
    async with api() as c:
        data = await login(c, person["login_id"], person["temp_password"])
        refresh_token = data["refresh_token"]

        refreshed = await c.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token})
        assert refreshed.status_code == 200, refreshed.text
        new_refresh = refreshed.json()["refresh_token"]

        reuse = await c.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token})
        assert reuse.status_code == 401

        logout = await c.post(f"{API}/auth/logout", json={"refresh_token": new_refresh})
        assert logout.status_code == 200
        after = await c.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh})
        assert after.status_code == 401


async def test_bad_credentials_rejected(org):
    person = who(org, "rohan")
    async with api() as c:
        r = await c.post(
            f"{API}/auth/login", json={"user_id": person["login_id"], "password": "wrong-pass"}
        )
        assert r.status_code in (400, 401)


# --------------------------------------------------------------------------
# L6 Operations Executive (260009) - Sana Qureshi
# --------------------------------------------------------------------------


async def staff_core(
    c: httpx.AsyncClient, person: dict, project: dict, assigned_task_title: str | None = None
) -> None:
    """Everything every staff-band employee does in their walkthrough."""
    uid = person["id"]

    # Profile self-service.
    profile = await c.get(f"{API}/employees/{uid}", headers=c.headers)
    assert profile.status_code == 200
    updated = await c.patch(
        f"{API}/employees/{uid}",
        headers=c.headers,
        json={"phone": "+91 98765 00001", "skills": ["revit", "sketchup"]},
    )
    assert updated.status_code == 200, updated.text
    docs = await c.get(f"{API}/employees/{uid}/documents", headers=c.headers)
    assert docs.status_code == 200

    # Attendance: check-in then check-out.
    check_in = await c.post(f"{API}/attendance/check-in", headers=c.headers, json={})
    assert check_in.status_code == 201, check_in.text
    monthly = await c.get(f"{API}/attendance/me", headers=c.headers)
    assert monthly.status_code == 200
    check_out = await c.post(f"{API}/attendance/check-out", headers=c.headers, json={})
    assert check_out.status_code == 200, check_out.text

    # Holiday calendar is readable by everyone.
    holidays = await c.get(f"{API}/attendance/holidays", headers=c.headers)
    assert holidays.status_code == 200
    assert len(holidays.json()) >= 1

    # Leaves: balance -> apply -> cancel -> reapply (kept pending).
    balance = await c.get(f"{API}/leaves/balance", headers=c.headers)
    assert balance.status_code == 200
    types = {row["leave_type"] for row in balance.json()}
    assert {"casual", "sick"} <= types

    leave = await apply_casual_leave(c, c.headers, "Walkthrough cancellation demo")
    cancelled = await c.patch(f"{API}/leaves/{leave['id']}", headers=c.headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    await apply_casual_leave(c, c.headers, "Family function")
    mine = await c.get(f"{API}/leaves/mine", headers=c.headers)
    assert mine.status_code == 200 and mine.json()["total"] >= 1
    pending_denied = await c.get(f"{API}/leaves/pending", headers=c.headers)
    assert pending_denied.status_code == 403

    # Tasks: board, progress transitions, checklist.
    board = await c.get(f"{API}/tasks/board", headers=c.headers)
    assert board.status_code == 200
    all_tasks = await c.get(f"{API}/tasks?assignee={uid}&page_size=50", headers=c.headers)
    assert all_tasks.status_code == 200
    items = all_tasks.json()["items"]
    target = next(
        (t for t in items if assigned_task_title is None or t["title"] == assigned_task_title), None
    )
    assert target is not None, "expected a task assigned to this employee"
    for status in ("in_progress", "review"):
        if target["status"] == status:
            continue  # seeded tasks may already sit in this column
        moved = await c.patch(
            f"{API}/tasks/{target['id']}", headers=c.headers, json={"status": status}
        )
        assert moved.status_code == 200, moved.text
    item = await c.post(
        f"{API}/tasks/{target['id']}/checklist", headers=c.headers, json={"text": "Final QA pass"}
    )
    assert item.status_code == 201
    toggled = await c.patch(
        f"{API}/tasks/{target['id']}/checklist/{item.json()['id']}", headers=c.headers
    )
    assert toggled.status_code == 200 and toggled.json()["is_done"] is True
    create_task = await c.post(
        f"{API}/tasks",
        headers=c.headers,
        json=task_payload("Unauthorized task", project["id"], uid),
    )
    assert create_task.status_code == 403

    # Projects scoped to membership.
    projects = await c.get(f"{API}/projects", headers=c.headers)
    assert projects.status_code == 200
    ids = {p["id"] for p in projects.json()["items"]}
    assert project["id"] in ids
    detail = await c.get(f"{API}/projects/{project['id']}", headers=c.headers)
    assert detail.status_code == 200
    timeline = await c.get(f"{API}/projects/{project['id']}/timeline", headers=c.headers)
    assert timeline.status_code == 200

    # Timesheets: log today, submit, no review rights.
    await ensure_submitted_sheet(c, c.headers, project["id"], hours="2.5")
    history = await c.get(f"{API}/timesheets/mine", headers=c.headers)
    assert history.status_code == 200 and history.json()["total"] >= 1
    pending_ts = await c.get(f"{API}/timesheets/pending", headers=c.headers)
    assert pending_ts.status_code == 403

    # Meetings: see invited meetings, RSVP accepted (idempotent).
    meetings = await c.get(f"{API}/meetings", headers=c.headers)
    assert meetings.status_code == 200
    invited = meetings.json()["items"]
    if invited:
        m = invited[0]
        rsvp = await c.post(
            f"{API}/meetings/{m['id']}/rsvp?rsvp_status=accepted", headers=c.headers
        )
        assert rsvp.status_code == 200

    # Notices readable; creation denied.
    notices = await c.get(f"{API}/notices", headers=c.headers)
    assert notices.status_code == 200
    assert notices.json()["total"] >= 1
    notice_post = await c.post(f"{API}/notices", headers=c.headers, json={"title": "Spam"})
    assert notice_post.status_code == 403

    # Notifications round-trip.
    unread = await c.get(f"{API}/notifications/unread-count", headers=c.headers)
    assert unread.status_code == 200
    read_all = await c.post(f"{API}/notifications/read-all", headers=c.headers)
    assert read_all.status_code == 200

    # Dashboard hides revenue from staff.
    summary = await c.get(f"{API}/dashboard/summary", headers=c.headers)
    assert summary.status_code == 200
    assert summary.json()["revenue_this_month"] is None

    # Full denial matrix for the staff band.
    other = next(e for e in _org()["employees"] if e["id"] != uid)
    today = datetime.now().date()
    matrix = [
        ("GET", f"{API}/employees", None),
        ("GET", f"{API}/employees/{other['id']}", None),
        ("PATCH", f"{API}/employees/{other['id']}", {"designation": "hacked"}),
        ("POST", f"{API}/employees", {"name": "Ghost Hire"}),
        ("GET", f"{API}/employees/{other['id']}/salary", None),
        ("PUT", f"{API}/employees/{other['id']}/salary", {"ctc_annual": "100"}),
        ("GET", f"{API}/employees/{other['id']}/attendance-summary", None),
        ("GET", f"{API}/users", None),
        ("POST", f"{API}/users", {"name": "Ghost"}),
        ("POST", f"{API}/projects", project_payload("Ghost Project")),
        ("DELETE", f"{API}/projects/{project['id']}", None),
        ("POST", f"{API}/clients", client_payload("Ghost Client")),
        ("DELETE", f"{API}/clients/{_org()['clients'][0]['id']}", None),
        ("PATCH", f"{API}/clients/{_org()['clients'][0]['id']}", {"budget_range": "₹1 crore"}),
        ("POST", f"{API}/meetings", {"title": "Ghost", "scheduled_at": datetime.now().isoformat()}),
        (
            "POST",
            f"{API}/site-visits",
            {"project_id": project["id"], "visit_date": working_days(1)[0].isoformat()},
        ),
        (
            "PUT",
            f"{API}/settings",
            [{"group": "leave", "key": "casual_annual", "value": {"value": 1}}],
        ),
        ("POST", f"{API}/holidays", {"name": "Ghost", "date": working_days(1)[0].isoformat()}),
        ("GET", f"{API}/audit-logs", None),
        (
            "POST",
            f"{API}/attendance/bulk",
            {"date": today.isoformat(), "entries": [{"user_id": uid, "status": "present"}]},
        ),
        ("GET", f"{API}/attendance/today", None),
        ("GET", f"{API}/attendance/report", None),
        ("GET", f"{API}/reports/hr", None),
        ("GET", f"{API}/reports/timesheets", None),
        ("GET", f"{API}/reports/finance", None),
        ("GET", f"{API}/reports/projects", None),
        ("GET", f"{API}/payroll", None),
        ("GET", f"{API}/finance/overview", None),
        ("GET", f"{API}/invoices", None),
        (
            "POST",
            f"{API}/invoices",
            {
                "client_id": _org()["clients"][0]["id"],
                "invoice_date": today.isoformat(),
                "due_date": today.isoformat(),
                "items": [{"description": "ghost", "quantity": "1", "rate": "1"}],
            },
        ),
        ("GET", f"{API}/expenses?status=pending", None),
        ("GET", f"{API}/backup/status", None),
    ]
    for method, url, body in matrix:
        r = await c.request(method, url, headers=c.headers, json=body)
        assert r.status_code == 403, (
            f"{person['login_id']} {method} {url} -> {r.status_code}: {r.text}"
        )


async def test_walkthrough_l6_sana_operations(org):
    sana = who(org, "sana")
    async with api() as c:
        data = await first_login(c, sana)
        assert data["user"]["org_level_code"] == "L6"
        c.headers.update(bearer(data))

        # Sana files her own expense through the self-service route.
        expense = await c.post(
            f"{API}/finance/my-expenses",
            headers=c.headers,
            json={
                "category": "travel",
                "amount": "450",
                "description": "Client courier",
                "paid_by": "Sana Qureshi",
            },
        )
        assert expense.status_code == 201
        mine = await c.get(f"{API}/finance/my-expenses", headers=c.headers)
        assert mine.status_code == 200 and mine.json()["total"] >= 1

        await staff_core(
            c, sana, {"id": org["projects"][1]["id"]}, assigned_task_title="FF&E budget sheet"
        )


# --------------------------------------------------------------------------
# L5 Architect (260004) - Meera Krishnan (promoted L6 -> L5)
# --------------------------------------------------------------------------


async def test_walkthrough_l5_meera_promoted(org):
    meera = who(org, "meera")
    async with api() as c:
        data = await first_login(c, meera)
        # Promotion applied during seeding: L6 -> L5.
        assert data["user"]["org_level_code"] == "L5"
        c.headers.update(bearer(data))
        tasks = await c.get(f"{API}/tasks?assignee={meera['id']}", headers=c.headers)
        titles = [t["title"] for t in tasks.json()["items"]]
        assert "Concept floor plan revision 2" in titles
        await staff_core(
            c,
            meera,
            {"id": org["projects"][0]["id"]},
            assigned_task_title="Concept floor plan revision 2",
        )


# --------------------------------------------------------------------------
# L4 walkthroughs (260003, 260007, 260008)
# --------------------------------------------------------------------------


async def test_walkthrough_l4_rohan_bim(org):
    rohan = who(org, "rohan")
    async with api() as c:
        data = await first_login(c, rohan)
        assert data["user"]["org_level_code"] == "L4"
        c.headers.update(bearer(data))
        tasks = await c.get(f"{API}/tasks?assignee={rohan['id']}", headers=c.headers)
        titles = [t["title"] for t in tasks.json()["items"]]
        assert "LOD300 model update" in titles
        assert "Render set for sales gallery" in titles
        await staff_core(
            c, rohan, {"id": org["projects"][0]["id"]}, assigned_task_title="LOD300 model update"
        )


async def test_walkthrough_l4_ananya_landscape(org):
    ananya = who(org, "ananya")
    async with api() as c:
        data = await first_login(c, ananya)
        assert data["user"]["org_level_code"] == "L4"
        c.headers.update(bearer(data))
        tasks = await c.get(f"{API}/tasks?assignee={ananya['id']}", headers=c.headers)
        titles = [t["title"] for t in tasks.json()["items"]]
        assert "Native species planting list" in titles
        await staff_core(
            c,
            ananya,
            {"id": org["projects"][2]["id"]},
            assigned_task_title="Native species planting list",
        )


async def test_walkthrough_l4_devang_promoted(org):
    devang = who(org, "devang")
    async with api() as c:
        data = await first_login(c, devang)
        # Promotion applied during seeding: L5 -> L4.
        assert data["user"]["org_level_code"] == "L4"
        c.headers.update(bearer(data))
        await staff_core(
            c,
            devang,
            {"id": org["projects"][1]["id"]},
            assigned_task_title="Material board for living areas",
        )


# --------------------------------------------------------------------------
# L3 Project Manager (260006) - Kabir Anand
# --------------------------------------------------------------------------


async def test_walkthrough_l3_lead_kabir(org):
    kabir = who(org, "kabir")
    ananya = who(org, "ananya")

    async with api() as c:
        data = await first_login(c, kabir)
        assert data["user"]["org_level_code"] == "L3"
        h = bearer(data)

        # Project delivery: create -> phases -> team -> timeline.
        created = await c.post(
            f"{API}/projects",
            headers=h,
            json=project_payload("Kabir Site Documentation", org["clients"][0]["id"]),
        )
        assert created.status_code == 201, created.text
        proj = created.json()
        assert proj["status"] == "draft"
        assert proj["project_lead_id"] == kabir["id"]

        phase = await c.post(
            f"{API}/projects/{proj['id']}/phases", headers=h, json={"name": "Site Documentation"}
        )
        assert phase.status_code == 201, phase.text
        phase_upd = await c.patch(
            f"{API}/projects/{proj['id']}/phases/{phase.json()['id']}",
            headers=h,
            json={"completion_pct": "25"},
        )
        assert phase_upd.status_code == 200

        team_add = await c.post(
            f"{API}/projects/{proj['id']}/team",
            headers=h,
            json={"user_id": ananya["id"], "role": "Survey Support"},
        )
        assert team_add.status_code == 201, team_add.text
        team_rm = await c.delete(f"{API}/projects/{proj['id']}/team/{ananya['id']}", headers=h)
        assert team_rm.status_code == 204
        readd = await c.post(
            f"{API}/projects/{proj['id']}/team",
            headers=h,
            json={"user_id": ananya["id"], "role": "Survey Support"},
        )
        assert readd.status_code == 201

        timeline = await c.get(f"{API}/projects/{proj['id']}/timeline", headers=h)
        assert timeline.status_code == 200
        detail = await c.get(f"{API}/projects/{proj['id']}", headers=h)
        assert detail.status_code == 200

        # Tasks: create for a teammate; assignee progresses it; lead reassigns.
        task = await c.post(
            f"{API}/tasks",
            headers=h,
            json=task_payload("Verify plot boundaries", proj["id"], ananya["id"]),
        )
        assert task.status_code == 201, task.text
        tsk = task.json()

        ah = await ready(c, ananya)
        moved = await c.patch(
            f"{API}/tasks/{tsk['id']}", headers=ah, json={"status": "in_progress"}
        )
        assert moved.status_code == 200
        reassign = await c.patch(
            f"{API}/tasks/{tsk['id']}", headers=h, json={"assigned_to": kabir["id"]}
        )
        assert reassign.status_code == 200, reassign.text

        board = await c.get(f"{API}/tasks/board", headers=h)
        assert board.status_code == 200

        # Clients: pipeline work allowed; money fields are not.
        client = await c.post(
            f"{API}/clients", headers=h, json=client_payload("Kabir Referral Client")
        )
        assert client.status_code == 201, client.text
        cid = client.json()["id"]
        comm = await c.post(
            f"{API}/clients/{cid}/communications",
            headers=h,
            json={
                "type": "call",
                "subject": "Intro call",
                "notes": "Interested in renovation.",
                "occurred_at": datetime.now().isoformat(),
            },
        )
        assert comm.status_code == 201, comm.text
        profile = await c.get(f"{API}/clients/{cid}", headers=h)
        assert profile.status_code == 200
        budget_write = await c.patch(
            f"{API}/clients/{cid}", headers=h, json={"budget_range": "₹25-50 lakh"}
        )
        assert budget_write.status_code == 403
        client_delete = await c.delete(f"{API}/clients/{cid}", headers=h)
        assert client_delete.status_code == 403

        # Meetings: create + invite; organizer cannot RSVP to self.
        meeting = await c.post(
            f"{API}/meetings",
            headers=h,
            json={
                "title": "Site prep huddle",
                "meeting_type": "internal",
                "scheduled_at": datetime.combine(working_days(1)[0], time(11, 30)).isoformat(),
                "duration_minutes": 30,
                "attendee_ids": [ananya["id"]],
            },
        )
        assert meeting.status_code == 201, meeting.text
        mid = meeting.json()["id"]
        self_rsvp = await c.post(f"{API}/meetings/{mid}/rsvp?rsvp_status=accepted", headers=h)
        assert self_rsvp.status_code == 409
        attendee_rsvp = await c.post(f"{API}/meetings/{mid}/rsvp?rsvp_status=accepted", headers=ah)
        assert attendee_rsvp.status_code == 200
        updated_meeting = await c.patch(
            f"{API}/meetings/{mid}", headers=h, json={"duration_minutes": 45}
        )
        assert updated_meeting.status_code == 200

        # Site visits on his own project.
        visit = await c.post(
            f"{API}/site-visits",
            headers=h,
            json={
                "project_id": proj["id"],
                "visit_date": working_days(2)[0].isoformat(),
                "start_time": "10:00",
                "purpose": "Boundary verification",
            },
        )
        assert visit.status_code == 201, visit.text
        vid = visit.json()["id"]
        photo = await c.post(
            f"{API}/site-visits/{vid}/photos",
            headers=h,
            files={"file": ("boundary.png", PNG_BYTES, "image/png")},
            data={"caption": "North boundary"},
        )
        assert photo.status_code == 201, photo.text
        completed = await c.patch(
            f"{API}/site-visits/{vid}", headers=h, json={"status": "completed", "weather": "clear"}
        )
        assert completed.status_code == 200
        report_pdf = await c.get(f"{API}/site-visits/{vid}/report", headers=h)
        assert report_pdf.status_code == 200 and report_pdf.content[:5] == b"%PDF-"

        # Leave approvals within hierarchy (junior applies, lead decides).
        # Fresh dates: both already hold pending leaves on the next working
        # day from their own staff_core runs.
        leave = await apply_casual_leave(c, ah, "Family function", day=working_days(4)[1])
        approve = await c.post(f"{API}/leaves/{leave['id']}/approve", headers=h)
        assert approve.status_code == 200, approve.text

        own_leave = await apply_casual_leave(c, h, "Personal work", day=working_days(4)[2])
        self_approve = await c.post(f"{API}/leaves/{own_leave['id']}/approve", headers=h)
        assert self_approve.status_code == 409

        rejected_leave = await apply_casual_leave(c, ah, "Overlap risk", day=working_days(4)[3])
        rejected = await c.post(
            f"{API}/leaves/{rejected_leave['id']}/reject",
            headers=h,
            json={"reason": "Clashes with site visit"},
        )
        assert rejected.status_code == 200

        pending = await c.get(f"{API}/leaves/pending", headers=h)
        assert pending.status_code == 200
        availability = await c.get(
            f"{API}/leaves/team-availability",
            headers=h,
            params={
                "from_date": date.today().isoformat(),
                "to_date": working_days(5)[4].isoformat(),
            },
        )
        assert availability.status_code == 200

        # Attendance visibility (L3+).
        today_rows = await c.get(f"{API}/attendance/today", headers=h)
        assert today_rows.status_code == 200
        att_report = await c.get(
            f"{API}/attendance/report",
            headers=h,
            params={
                "from_date": working_days(1)[0].isoformat(),
                "to_date": date.today().isoformat(),
            },
        )
        assert att_report.status_code == 200

        # Timesheets: review queue + approval + weekly receipt.
        submitted = await ensure_submitted_sheet(c, ah, proj["id"])
        queue = await c.get(f"{API}/timesheets/pending", headers=h)
        assert queue.status_code == 200 and queue.json()["total"] >= 1
        approved_sheet = await c.post(f"{API}/timesheets/{submitted['id']}/approve", headers=h)
        assert approved_sheet.status_code == 200, approved_sheet.text
        pdf_receipt = await c.get(f"{API}/timesheets/{submitted['id']}/pdf", headers=h)
        assert pdf_receipt.status_code == 200 and pdf_receipt.content[:5] == b"%PDF-"

        own_sheet = await ensure_submitted_sheet(c, h, proj["id"], hours="2.0")
        own_review = await c.post(f"{API}/timesheets/{own_sheet['id']}/approve", headers=h)
        assert own_review.status_code == 403

        # People read access (L3+).
        users_list = await c.get(f"{API}/users", headers=h)
        assert users_list.status_code == 200
        employees = await c.get(f"{API}/employees", headers=h)
        assert employees.status_code == 200
        other_profile = await c.get(f"{API}/employees/{ananya['id']}", headers=h)
        assert other_profile.status_code == 200

        # Everything above L3 is out of bounds. (Notices stay org-wide
        # readable; only authoring them is restricted.)
        denials = [
            ("POST", f"{API}/notices", {"title": "nope"}),
            (
                "PUT",
                f"{API}/settings",
                [{"group": "leave", "key": "casual_annual", "value": {"value": 5}}],
            ),
            ("POST", f"{API}/holidays", {"name": "nope", "date": working_days(5)[0].isoformat()}),
            ("GET", f"{API}/audit-logs", None),
            (
                "POST",
                f"{API}/attendance/bulk",
                {
                    "date": datetime.now().date().isoformat(),
                    "entries": [{"user_id": ananya["id"], "status": "present"}],
                },
            ),
            ("GET", f"{API}/reports/timesheets", None),
            ("GET", f"{API}/reports/hr", None),
            ("GET", f"{API}/reports/finance", None),
            ("GET", f"{API}/payroll", None),
            ("GET", f"{API}/finance/overview", None),
            ("GET", f"{API}/backup/status", None),
            ("POST", f"{API}/employees", {"name": "Nope Hire"}),
            ("DELETE", f"{API}/projects/{proj['id']}", None),
        ]
        for method, url, body in denials:
            r = await c.request(method, url, headers=h, json=body)
            assert r.status_code == 403, f"{method} {url} -> {r.status_code}: {r.text}"

        summary = await c.get(f"{API}/dashboard/summary", headers=h)
        assert summary.json()["revenue_this_month"] is None


# --------------------------------------------------------------------------
# L2 Department Head (260002) - Ishaan Malhotra
# --------------------------------------------------------------------------


async def test_walkthrough_l2_dept_head_ishaan(org):
    ishaan = who(org, "ishaan")
    ceo = who(org, "ceo")
    meera = who(org, "meera")

    async with api() as c:
        data = await first_login(c, ishaan)
        assert data["user"]["org_level_code"] == "L2"
        h = bearer(data)

        levels = await level_ids(c, h)

        # Revenue stays hidden below L1 even for a department head.
        summary = await c.get(f"{API}/dashboard/summary", headers=h)
        assert summary.json()["revenue_this_month"] is None

        # Studio administration available at L2.
        settings = await c.get(f"{API}/settings", headers=h)
        assert settings.status_code == 200
        put_s = await c.put(
            f"{API}/settings",
            headers=h,
            json=[{"group": "attendance", "key": "late_threshold_minutes", "value": {"value": 20}}],
        )
        assert put_s.status_code == 200, put_s.text

        hol = await c.post(
            f"{API}/holidays",
            headers=h,
            json={"name": "Design Jam", "date": working_days(10)[-1].isoformat()},
        )
        assert hol.status_code == 201
        renamed = await c.patch(
            f"{API}/holidays/{hol.json()['id']}", headers=h, json={"name": "Design Jam (all day)"}
        )
        assert renamed.status_code == 200

        notice = await c.post(
            f"{API}/notices",
            headers=h,
            json={"title": "Architecture desk move", "body": "Weekend shuffle."},
        )
        assert notice.status_code == 201
        edited = await c.patch(
            f"{API}/notices/{notice.json()['id']}", headers=h, json={"is_pinned": True}
        )
        assert edited.status_code == 200

        audit = await c.get(f"{API}/audit-logs?page_size=5", headers=h)
        assert audit.status_code == 200

        # HR duties: onboarding strictly-junior only.
        depts = await c.get(f"{API}/departments", headers=h)
        dept_map = {d["name"]: d["id"] for d in depts.json()}
        bad_level = await c.post(
            f"{API}/employees",
            headers=h,
            json={
                "name": "Peer Level Hire",
                "department_id": dept_map["Architecture & Design"],
                "org_level_id": levels["L2"],
                "designation": "Designer",
            },
        )
        assert bad_level.status_code == 403

        senior_level = await c.post(
            f"{API}/employees",
            headers=h,
            json={
                "name": "Senior Level Hire",
                "department_id": dept_map["Architecture & Design"],
                "org_level_id": levels["L1"],
                "designation": "Director",
            },
        )
        assert senior_level.status_code == 403

        hired = await c.post(
            f"{API}/employees",
            headers=h,
            json={
                "name": "Aarav Sharma",
                "department_id": dept_map["Architecture & Design"],
                "org_level_id": levels["L3"],
                "designation": "Project Manager",
                "skills": ["rhino"],
                "date_of_joining": datetime.now().date().isoformat(),
            },
        )
        assert hired.status_code == 201, hired.text
        aarav_id = hired.json()["id"]

        employees = await c.get(f"{API}/employees", headers=h)
        assert employees.status_code == 200
        assert employees.json()["total"] >= 11

        # Attendance management (L2+).
        bulk = await c.post(
            f"{API}/attendance/bulk",
            headers=h,
            json={
                "date": (datetime.now().date() - timedelta(days=2)).isoformat(),
                "entries": [{"user_id": aarav_id, "status": "work_from_home"}],
            },
        )
        assert bulk.status_code == 200, bulk.text
        today_rows = await c.get(f"{API}/attendance/today", headers=h)
        assert today_rows.status_code == 200
        rep_json = await c.get(
            f"{API}/attendance/report",
            headers=h,
            params={
                "from_date": working_days(1)[0].isoformat(),
                "to_date": date.today().isoformat(),
            },
        )
        assert rep_json.status_code == 200
        rep_xlsx = await c.get(
            f"{API}/attendance/report",
            headers=h,
            params={
                "from_date": working_days(1)[0].isoformat(),
                "to_date": date.today().isoformat(),
                "format": "xlsx",
            },
        )
        assert rep_xlsx.status_code == 200 and rep_xlsx.content[:2] == b"PK"
        emp_summary = await c.get(f"{API}/employees/{aarav_id}/attendance-summary", headers=h)
        assert emp_summary.status_code == 200

        # Timesheets: admin list + day review of a junior + month export.
        mh = await ready(c, meera)
        submitted = await ensure_submitted_sheet(c, mh, org["projects"][0]["id"], hours="4.0")
        listing = await c.get(f"{API}/timesheets?status=submitted", headers=h)
        assert listing.status_code == 200
        today_iso = datetime.now().date().isoformat()
        day_approve = await c.post(
            f"{API}/timesheets/{submitted['id']}/days/{today_iso}/approve", headers=h
        )
        assert day_approve.status_code == 200, day_approve.text

        export = await c.get(
            f"{API}/timesheets/export/month"
            f"?month={datetime.now().month}&year={datetime.now().year}",
            headers=h,
        )
        assert export.status_code == 200 and export.content[:2] == b"PK"

        ts_report = await c.get(f"{API}/reports/timesheets?group_by=week", headers=h)
        assert ts_report.status_code == 200
        options = await c.get(f"{API}/reports/timesheets/options", headers=h)
        assert options.status_code == 200

        # Financial glass ceiling still applies to an L2 head.
        fin = await c.get(f"{API}/finance/overview", headers=h)
        assert fin.status_code == 403
        pay = await c.get(f"{API}/payroll", headers=h)
        assert pay.status_code == 403
        inv = await c.post(
            f"{API}/invoices",
            headers=h,
            json={
                "client_id": org["clients"][0]["id"],
                "invoice_date": datetime.now().date().isoformat(),
                "due_date": datetime.now().date().isoformat(),
                "items": [{"description": "x", "quantity": "1", "rate": "10"}],
            },
        )
        assert inv.status_code == 403
        sal = await c.get(f"{API}/employees/{meera['id']}/salary", headers=h)
        assert sal.status_code == 403
        budget_patch = await c.patch(
            f"{API}/projects/{org['projects'][0]['id']}", headers=h, json={"budget": "9999999"}
        )
        assert budget_patch.status_code == 403
        client_budget = await c.patch(
            f"{API}/clients/{org['clients'][0]['id']}",
            headers=h,
            json={"budget_range": "₹5-10 crore"},
        )
        assert client_budget.status_code == 403
        fin_report = await c.get(f"{API}/reports/finance", headers=h)
        assert fin_report.status_code == 403
        backup = await c.get(f"{API}/backup/status", headers=h)
        assert backup.status_code == 403

        # L1-only powers denied.
        users_create = await c.post(
            f"{API}/users", headers=h, json={"name": "Nope", "org_level_id": levels["L6"]}
        )
        assert users_create.status_code == 403
        client_del = await c.delete(f"{API}/clients/{org['clients'][0]['id']}", headers=h)
        assert client_del.status_code == 403
        purge = await c.post(f"{API}/employees/{meera['id']}/purge", headers=h)
        assert purge.status_code == 403

        assert ceo["login_id"] == "260001"


# --------------------------------------------------------------------------
# L1 Director (260010) - Vikram Sethi
# --------------------------------------------------------------------------


async def test_walkthrough_l1_director_vikram(org):
    vikram = who(org, "vikram")
    ceo = who(org, "ceo")
    sana = who(org, "sana")

    async with api() as c:
        data = await first_login(c, vikram)
        assert data["user"]["org_level_code"] == "L1"
        h = bearer(data)

        summary = await c.get(f"{API}/dashboard/summary", headers=h)
        assert summary.status_code == 200
        assert summary.json()["revenue_this_month"] is not None

        levels = await level_ids(c, h)

        # Executive-only surfaces open up.
        for path in (
            "/finance/overview",
            "/payroll",
            "/backup/status",
            "/reports/finance",
            "/reports/projects",
        ):
            r = await c.get(f"{API}{path}", headers=h)
            assert r.status_code == 200, f"{path}: {r.text}"

        # Create a user directly via /users (L1+), then regenerate password.
        created = await c.post(
            f"{API}/users",
            headers=h,
            json={
                "name": "Consultant Via Users",
                "org_level_id": levels["L4"],
                "designation": "Consultant",
            },
        )
        assert created.status_code == 201, created.text
        regen = await c.post(f"{API}/users/{created.json()['id']}/regenerate-password", headers=h)
        assert regen.status_code == 200

        # Onboarding via /employees with generated one-time credentials.
        depts = await c.get(f"{API}/departments", headers=h)
        dept_map = {d["name"]: d["id"] for d in depts.json()}
        onboarded = await c.post(
            f"{API}/employees",
            headers=h,
            json={
                "name": "Rhea Kulkarni",
                "department_id": dept_map["Business & Operations"],
                "org_level_id": levels["L6"],
                "designation": "Operations Executive",
                "gender": "Female",
                "date_of_joining": datetime.now().date().isoformat(),
            },
        )
        assert onboarded.status_code == 201, onboarded.text
        assert onboarded.json()["generated_password"]

        # Departments / holidays / notices / audit are L1-accessible.
        dept = await c.post(f"{API}/departments", headers=h, json={"name": "Sustainability Lab"})
        assert dept.status_code == 201
        assert (
            await c.delete(f"{API}/departments/{dept.json()['id']}", headers=h)
        ).status_code == 204

        hol = await c.post(
            f"{API}/holidays",
            headers=h,
            json={"name": "Directors Day Off", "date": working_days(20)[-1].isoformat()},
        )
        assert hol.status_code == 201
        await c.delete(f"{API}/holidays/{hol.json()['id']}", headers=h)

        notice = await c.post(
            f"{API}/notices",
            headers=h,
            json={"title": "Quarterly town hall", "importance": "high", "is_pinned": True},
        )
        assert notice.status_code == 201

        audit = await c.get(f"{API}/audit-logs?entity_type=user", headers=h)
        assert audit.status_code == 200

        reports_hr = await c.get(f"{API}/reports/hr", headers=h)
        assert reports_hr.status_code == 200

        # L1-only powers: delete a client and a project.
        client = await c.post(
            f"{API}/clients", headers=h, json=client_payload("Vikram Test Client")
        )
        assert client.status_code == 201
        assert (
            await c.delete(f"{API}/clients/{client.json()['id']}", headers=h)
        ).status_code == 204

        proj = await c.post(
            f"{API}/projects", headers=h, json=project_payload("Vikram Temp Project")
        )
        assert proj.status_code == 201
        assert (await c.delete(f"{API}/projects/{proj.json()['id']}", headers=h)).status_code == 204

        # Guard rails against seniors and CEO-only powers.
        patch_ceo = await c.patch(
            f"{API}/employees/{ceo['id']}", headers=h, json={"designation": "Overruled"}
        )
        assert patch_ceo.status_code == 403
        regen_ceo = await c.post(f"{API}/users/{ceo['id']}/regenerate-password", headers=h)
        assert regen_ceo.status_code == 403
        purge = await c.post(f"{API}/employees/{sana['id']}/purge", headers=h)
        assert purge.status_code == 403
        deactivate_ceo = await c.patch(
            f"{API}/employees/{ceo['id']}", headers=h, json={"is_active": False}
        )
        assert deactivate_ceo.status_code == 403

        # Roster reflects promotions exactly.
        employees = await c.get(f"{API}/employees?page_size=50", headers=h)
        assert employees.status_code == 200
        codes = {e["name"]: e["org_level_code"] for e in employees.json()["items"]}
        assert codes["Priya Nambiar"] == "L1"
        assert codes["Meera Krishnan"] == "L5"
        assert codes["Devang Shah"] == "L4"


# --------------------------------------------------------------------------
# CEO (260001, L0) - full executive tour
# --------------------------------------------------------------------------


async def test_walkthrough_ceo_260001(org):
    ceo = who(org, "ceo")
    rohan = who(org, "rohan")
    meera = who(org, "meera")
    ananya = who(org, "ananya")
    kabir = who(org, "kabir")

    async with api() as c:
        # The CEO account was provisioned with a known strong password.
        data = await login(c, ceo["login_id"], ceo["password"])
        assert data["user"]["must_change_password"] is False
        assert data["user"]["org_level_code"] == "L0"
        h = bearer(data)

        # -- Dashboard shows real revenue ---------------------------------
        summary = await c.get(f"{API}/dashboard/summary", headers=h)
        assert summary.status_code == 200, summary.text
        assert summary.json()["revenue_this_month"] is not None

        levels = await level_ids(c, h)

        # -- User administration (L1+) ------------------------------------
        users = await c.get(f"{API}/users", headers=h)
        assert users.status_code == 200
        assert len(users.json()) >= 11

        new_hire = await c.post(
            f"{API}/users",
            headers=h,
            json={
                "name": "Test Hire",
                "designation": "Junior Designer",
                "org_level_id": levels["L6"],
                "date_of_joining": datetime.now().date().isoformat(),
            },
        )
        assert new_hire.status_code == 201, new_hire.text
        hire_body = new_hire.json()
        assert hire_body["generated_password"]
        hire_id = hire_body["id"]

        promote = await c.patch(
            f"{API}/users/{hire_id}", headers=h, json={"org_level_id": levels["L5"]}
        )
        assert promote.status_code == 200, promote.text

        regen = await c.post(f"{API}/users/{hire_id}/regenerate-password", headers=h)
        assert regen.status_code == 200
        assert regen.json()["generated_password"]

        # -- Payroll (executive only) --------------------------------------
        today = datetime.now().date()
        run = await c.post(
            f"{API}/payroll/process", headers=h, json={"month": today.month, "year": today.year}
        )
        assert run.status_code == 200, run.text
        assert len(run.json()["entries"]) >= 11

        payslip = await c.get(
            f"{API}/payroll/{today.month}/{today.year}/payslips/{rohan['id']}", headers=h
        )
        assert payslip.status_code == 200
        assert payslip.content[:5] == b"%PDF-"

        payroll_get = await c.get(f"{API}/payroll?month={today.month}&year={today.year}", headers=h)
        assert payroll_get.status_code == 200

        # -- Finance -------------------------------------------------------
        overview = await c.get(f"{API}/finance/overview", headers=h)
        assert overview.status_code == 200

        invoice = await c.post(
            f"{API}/invoices",
            headers=h,
            json={
                "client_id": org["clients"][0]["id"],
                "project_id": org["projects"][0]["id"],
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=15)).isoformat(),
                "tax_percent": "18",
                "items": [{"description": "Design milestone", "quantity": "1", "rate": "50000"}],
            },
        )
        assert invoice.status_code == 201, invoice.text
        inv = invoice.json()

        sent = await c.post(f"{API}/invoices/{inv['id']}/send", headers=h)
        assert sent.status_code == 200
        paid = await c.post(
            f"{API}/invoices/{inv['id']}/payment",
            headers=h,
            json={"amount": "59000", "method": "upi"},
        )
        assert paid.status_code == 200
        inv_pdf = await c.get(f"{API}/invoices/{inv['id']}/pdf", headers=h)
        assert inv_pdf.status_code == 200 and inv_pdf.content[:5] == b"%PDF-"

        pending = await c.get(f"{API}/expenses?status=pending", headers=h)
        assert pending.status_code == 200
        exps = pending.json()["items"]
        assert len(exps) >= 2
        appr = await c.patch(
            f"{API}/expenses/{exps[0]['id']}/approve",
            headers=h,
            json={"approve": True, "note": "ok"},
        )
        assert appr.status_code == 200
        rej = await c.patch(
            f"{API}/expenses/{exps[1]['id']}/approve",
            headers=h,
            json={"approve": False, "note": "not billable"},
        )
        assert rej.status_code == 200

        my_exp = await c.post(
            f"{API}/finance/my-expenses",
            headers=h,
            json={"category": "office", "amount": "120", "description": "Stationery"},
        )
        assert my_exp.status_code == 201, my_exp.text

        # -- Reports incl. exports ----------------------------------------
        for path in ("/reports/projects", "/reports/finance", "/reports/hr", "/reports/timesheets"):
            r = await c.get(f"{API}{path}", headers=h)
            assert r.status_code == 200, f"{path}: {r.text}"
        csv_rep = await c.get(f"{API}/reports/projects?format=csv", headers=h)
        assert csv_rep.status_code == 200 and b"," in csv_rep.content
        xlsx_rep = await c.get(f"{API}/reports/hr?format=xlsx", headers=h)
        assert xlsx_rep.status_code == 200 and xlsx_rep.content[:2] == b"PK"
        pdf_rep = await c.get(f"{API}/reports/timesheets?format=pdf", headers=h)
        assert pdf_rep.status_code == 200 and pdf_rep.content[:5] == b"%PDF-"

        # -- Studio administration ----------------------------------------
        settings = await c.get(f"{API}/settings", headers=h)
        assert settings.status_code == 200
        put_setting = await c.put(
            f"{API}/settings",
            headers=h,
            json=[{"group": "leave", "key": "casual_annual", "value": {"value": 14}}],
        )
        assert put_setting.status_code == 200, put_setting.text

        holiday = await c.post(
            f"{API}/holidays",
            headers=h,
            json={"name": "Studio Foundation Day", "date": (working_days(30)[-1]).isoformat()},
        )
        assert holiday.status_code == 201, holiday.text
        hol = holiday.json()
        patched = await c.patch(
            f"{API}/holidays/{hol['id']}", headers=h, json={"name": "Foundation Day (renamed)"}
        )
        assert patched.status_code == 200
        deleted = await c.delete(f"{API}/holidays/{hol['id']}", headers=h)
        assert deleted.status_code == 200

        dept = await c.post(f"{API}/departments", headers=h, json={"name": "Research & Innovation"})
        assert dept.status_code == 201, dept.text
        dep_del = await c.delete(f"{API}/departments/{dept.json()['id']}", headers=h)
        assert dep_del.status_code == 204

        audit = await c.get(f"{API}/audit-logs", headers=h)
        assert audit.status_code == 200 and len(audit.json()) > 0
        count = await c.get(f"{API}/audit-logs/count", headers=h)
        assert count.status_code == 200 and count.json()["total"] > 0
        export = await c.get(f"{API}/audit-logs/export", headers=h)
        assert export.status_code == 200 and export.content.startswith(b"id,")

        backup_status = await c.get(f"{API}/backup/status", headers=h)
        assert backup_status.status_code == 200
        backup_hist = await c.get(f"{API}/backup/history", headers=h)
        assert backup_hist.status_code == 200

        # -- HR: salaries, documents, attendance --------------------------
        salary = await c.get(f"{API}/employees/{rohan['id']}/salary", headers=h)
        assert salary.status_code == 200
        sal_update = await c.put(
            f"{API}/employees/{rohan['id']}/salary", headers=h, json={"ctc_annual": "1260000"}
        )
        assert sal_update.status_code == 200
        assert Decimal(str(sal_update.json()["ctc_annual"])) == Decimal("1260000")

        doc = await c.post(
            f"{API}/employees/{meera['id']}/documents",
            params={"doc_type": "offer_letter"},
            files={"file": ("offer.pdf", PDF_BYTES, "application/pdf")},
            headers=h,
        )
        assert doc.status_code == 201, doc.text
        docs = await c.get(f"{API}/employees/{meera['id']}/documents", headers=h)
        assert docs.status_code == 200 and docs.json()["total"] >= 1
        doc_del = await c.delete(
            f"{API}/employees/{meera['id']}/documents/{doc.json()['id']}", headers=h
        )
        assert doc_del.status_code == 200

        bulk = await c.post(
            f"{API}/attendance/bulk",
            headers=h,
            json={
                "date": (datetime.now().date() - timedelta(days=1)).isoformat(),
                "entries": [{"user_id": ananya["id"], "status": "present"}],
            },
        )
        assert bulk.status_code == 200, bulk.text
        today_att = await c.get(f"{API}/attendance/today", headers=h)
        assert today_att.status_code == 200

        # -- Timesheet approval over a junior submission -------------------
        rh = await ready(c, rohan)
        submitted = await ensure_submitted_sheet(c, rh, org["projects"][0]["id"])
        approve = await c.post(f"{API}/timesheets/{submitted['id']}/approve", headers=h)
        assert approve.status_code == 200, approve.text

        # -- Business records lifecycle ------------------------------------
        notice = await c.post(
            f"{API}/notices",
            headers=h,
            json={
                "title": "ERP walkthrough week",
                "body": "Complete your walkthrough.",
                "importance": "medium",
            },
        )
        assert notice.status_code == 201
        meeting = await c.post(
            f"{API}/meetings",
            headers=h,
            json={
                "title": "All-hands",
                "scheduled_at": datetime.combine(working_days(3)[0], time(16, 0)).isoformat(),
                "attendee_ids": [kabir["id"]],
            },
        )
        assert meeting.status_code == 201, meeting.text

        client_create = await c.post(
            f"{API}/clients", headers=h, json=client_payload("Temp Client Co")
        )
        assert client_create.status_code == 201, client_create.text
        temp_client_id = client_create.json()["id"]

        proj_create = await c.post(
            f"{API}/projects", headers=h, json=project_payload("Temp Renovation Study")
        )
        assert proj_create.status_code == 201, proj_create.text
        temp_proj = proj_create.json()
        proj_del = await c.delete(f"{API}/projects/{temp_proj['id']}", headers=h)
        assert proj_del.status_code == 204
        client_del = await c.delete(f"{API}/clients/{temp_client_id}", headers=h)
        assert client_del.status_code == 204

        # Notifications round-trip
        unread = await c.get(f"{API}/notifications/unread-count", headers=h)
        assert unread.status_code == 200
        read_all = await c.post(f"{API}/notifications/read-all", headers=h)
        assert read_all.status_code == 200
