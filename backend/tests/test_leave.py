from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import Attendance, LeaveBalance, OrgLevel, User
from app.modules.leave.schemas import LeaveApplyRequest
from app.modules.leave import service as leave_service
from app.utils.enums import AttendanceStatus, LeaveStatus, LeaveType
from app.utils.errors import LeaveError

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

LEAVE_EMPLOYEE_EMAIL = "leave.employee@studioerp.dev"
LEAVE_EMPLOYEE_PASSWORD = "employee-pass-123"

APPROVER_EMAIL = "leave.approver@studioerp.dev"
APPROVER_PASSWORD = "approver-pass-123"
LEAD_EMAIL = "leave.lead@studioerp.dev"
LEAD_PASSWORD = "lead-pass-123"


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


def _next_monday() -> date:
    day = date.today() + timedelta(days=1)
    while day.weekday() != 0:
        day += timedelta(days=1)
    return day


@pytest.fixture(scope="session")
async def leave_employee():
    return await _create_user(LEAVE_EMPLOYEE_EMAIL, LEAVE_EMPLOYEE_PASSWORD, "Leave Employee")


@pytest.fixture(scope="session")
async def approver():
    return await _create_user(APPROVER_EMAIL, APPROVER_PASSWORD, "Leave Approver", "L1")


@pytest.fixture(scope="session")
async def lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Leave Lead", "L3")


async def test_apply_leave_creates_pending(leave_employee: User) -> None:
    start = _next_monday()
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=2),
                reason="Family function",
            ),
        )
        assert leave.status == LeaveStatus.PENDING
        assert float(leave.total_days) == 3.0


async def test_apply_leave_in_past_rejected(leave_employee: User) -> None:
    async with AsyncSessionLocal() as db:
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.apply_leave(
                db,
                leave_employee,
                LeaveApplyRequest(
                    leave_type=LeaveType.CASUAL,
                    from_date=date.today() - timedelta(days=10),
                    to_date=date.today() - timedelta(days=8),
                ),
            )
        assert exc_info.value.status_code == 400


async def test_insufficient_balance_rejected(leave_employee: User) -> None:
    start = _next_monday() + timedelta(days=28)
    async with AsyncSessionLocal() as db:
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.apply_leave(
                db,
                leave_employee,
                LeaveApplyRequest(
                    leave_type=LeaveType.CASUAL,
                    from_date=start,
                    to_date=start + timedelta(days=20),
                ),
            )
        assert "Insufficient" in exc_info.value.message
        assert exc_info.value.status_code == 409


async def test_overlapping_leave_rejected(leave_employee: User) -> None:
    start = _next_monday() + timedelta(days=56)
    async with AsyncSessionLocal() as db:
        await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=1),
            ),
        )
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.apply_leave(
                db,
                leave_employee,
                LeaveApplyRequest(
                    leave_type=LeaveType.SICK,
                    from_date=start + timedelta(days=1),
                    to_date=start + timedelta(days=2),
                ),
            )
        assert "Overlaps" in exc_info.value.message


async def test_approve_updates_balance_and_marks_attendance(
    leave_employee: User, approver: User
) -> None:
    start = _next_monday() + timedelta(days=84)
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=1),
                reason="Two days off",
            ),
        )
        approved = await leave_service.approve_leave(db, approver, leave.id)
        assert approved.status == LeaveStatus.APPROVED
        assert approved.approved_by == approver.id

        balances = {
            row["leave_type"]: row
            for row in await leave_service.get_balances(db, leave_employee.id, start.year)
        }
        assert float(balances["casual"]["used"]) == 2.0

        on_leave = (
            (
                await db.execute(
                    select(Attendance).where(
                        Attendance.user_id == leave_employee.id,
                        Attendance.status == AttendanceStatus.ON_LEAVE,
                    )
                )
            )
            .scalars()
            .all()
        )
        on_leave_days = {row.date for row in on_leave}
        expected = {start, start + timedelta(days=1)}
        assert expected.issubset(on_leave_days)


async def test_reject_leave(leave_employee: User, approver: User) -> None:
    start = _next_monday() + timedelta(days=112)
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.SICK,
                from_date=start,
                to_date=start,
                reason="Not well",
            ),
        )
        rejected = await leave_service.reject_leave(db, approver, leave.id, "Doctor note required")
        assert rejected.status == LeaveStatus.REJECTED
        assert rejected.rejection_reason == "Doctor note required"


async def test_cancel_only_pending(leave_employee: User, approver: User) -> None:
    start = _next_monday() + timedelta(days=140)
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=2),
            ),
        )
        approved = await leave_service.approve_leave(db, approver, leave.id)
        with pytest.raises(LeaveError):
            await leave_service.cancel_leave(db, leave_employee, approved.id)

        pending = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.SICK,
                from_date=start + timedelta(days=7),
                to_date=start + timedelta(days=7),
            ),
        )
        cancelled = await leave_service.cancel_leave(db, leave_employee, pending.id)
        assert cancelled.status == LeaveStatus.CANCELLED


async def test_pending_queue_and_team_availability(leave_employee: User, approver: User) -> None:
    start = _next_monday() + timedelta(days=168)
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=2),
                reason="Queue test",
            ),
        )
        queue, _total = await leave_service.pending_queue(db)
        assert any(row["id"] == leave.id for row in queue)

        availability = await leave_service.team_availability(db, start, start + timedelta(days=2))
        assert any(
            row["user_id"] == leave_employee.id and row["status"] == "pending"
            for row in availability
        )


async def test_lead_cannot_approve_own_leave(lead: User) -> None:
    start = _next_monday() + timedelta(days=224)
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            lead,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=1),
                reason="Own leave",
            ),
        )
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.approve_leave(db, lead, leave.id)
        assert "own" in exc_info.value.message
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.reject_leave(db, lead, leave.id, "nope")
        assert "own" in exc_info.value.message


async def test_lead_approves_employee_via_api_and_employee_blocked(
    leave_employee: User, lead: User
) -> None:
    start = _next_monday() + timedelta(days=252)
    async with AsyncSessionLocal() as db:
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=1),
                reason="API approval",
            ),
        )
        leave_id = leave.id

    async with _client() as client:
        lead_token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        pending = await client.get("/api/v1/leaves/pending", headers=lead_headers)
        assert pending.status_code == 200
        assert any(row["id"] == leave_id for row in pending.json()["items"])

        approved = await client.post(f"/api/v1/leaves/{leave_id}/approve", headers=lead_headers)
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        emp_token = await _login(client, LEAVE_EMPLOYEE_EMAIL, LEAVE_EMPLOYEE_PASSWORD)
        emp_headers = {"Authorization": f"Bearer {emp_token}"}
        forbidden = await client.get("/api/v1/leaves/pending", headers=emp_headers)
        assert forbidden.status_code == 403


async def test_leave_api_endpoints(leave_employee: User, approver: User) -> None:
    async with _client() as client:
        employee_token = await _login(client, LEAVE_EMPLOYEE_EMAIL, LEAVE_EMPLOYEE_PASSWORD)
        headers = {"Authorization": f"Bearer {employee_token}"}

        start = _next_monday() + timedelta(days=196)
        response = await client.post(
            "/api/v1/leaves",
            json={
                "leave_type": "casual",
                "from_date": start.isoformat(),
                "to_date": start.isoformat(),
                "reason": "API test",
            },
            headers=headers,
        )
        assert response.status_code == 201
        leave_id = response.json()["id"]
        assert response.json()["status"] == "pending"

        balance = await client.get("/api/v1/leaves/balance", headers=headers)
        assert balance.status_code == 200
        casual = next(b for b in balance.json() if b["leave_type"] == "casual")
        assert float(casual["remaining"]) == float(casual["allocated"]) - float(casual["used"])

        mine = await client.get("/api/v1/leaves/mine", headers=headers)
        assert any(entry["id"] == leave_id for entry in mine.json()["items"])

        # cancel own pending leave
        cancelled = await client.patch(f"/api/v1/leaves/{leave_id}", headers=headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        approver_token = await _login(client, APPROVER_EMAIL, APPROVER_PASSWORD)
        admin_headers = {"Authorization": f"Bearer {approver_token}"}
        pending = await client.get("/api/v1/leaves/pending", headers=admin_headers)
        assert pending.status_code == 200


# ── Regression: atomic leave balance update (Item 3) ──


async def test_approve_rejects_when_balance_exceeded(leave_employee: User, approver: User) -> None:
    """Regression: approve_leave must raise 409 when balance is insufficient.

    Previously, the read-modify-write pattern allowed two concurrent approvals
    to both succeed, exceeding the allocated balance. The fix uses an atomic
    UPDATE ... WHERE used + days <= allocated, so a ceiling breach returns
    rowcount=0 and raises LeaveError.
    """
    start = _next_monday() + timedelta(days=280)
    async with AsyncSessionLocal() as db:
        # Set the balance to only 1 remaining day
        balance = (
            (
                await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.user_id == leave_employee.id,
                        LeaveBalance.leave_type == LeaveType.CASUAL,
                        LeaveBalance.year == start.year,
                    )
                )
            )
            .scalars()
            .first()
        )
        if balance is None:
            await leave_service.ensure_balances(db, leave_employee.id, start.year)
            balance = (
                (
                    await db.execute(
                        select(LeaveBalance).where(
                            LeaveBalance.user_id == leave_employee.id,
                            LeaveBalance.leave_type == LeaveType.CASUAL,
                            LeaveBalance.year == start.year,
                        )
                    )
                )
                .scalars()
                .first()
            )
        balance.used = balance.allocated - Decimal("1.00")
        await db.commit()

        # Apply a 3-day leave (exceeds remaining 1 day)
        leave = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.CASUAL,
                from_date=start,
                to_date=start + timedelta(days=2),
                reason="Balance ceiling test",
            ),
        )
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.approve_leave(db, approver, leave.id)
        assert exc_info.value.status_code == 409
        assert "balance" in exc_info.value.message.lower()


async def test_concurrent_approve_only_one_succeeds(leave_employee: User, approver: User) -> None:
    """Regression: two approvals for leaves of the same type cannot both increment
    the balance past the allocation ceiling.

    This test sequentially approves two leaves that together exactly fill the
    remaining balance, then verifies a third approval is rejected.
    """
    start = _next_monday() + timedelta(days=308)
    async with AsyncSessionLocal() as db:
        # Reset balance to exactly 4 days used
        balance = (
            (
                await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.user_id == leave_employee.id,
                        LeaveBalance.leave_type == LeaveType.SICK,
                        LeaveBalance.year == start.year,
                    )
                )
            )
            .scalars()
            .first()
        )
        if balance is None:
            await leave_service.ensure_balances(db, leave_employee.id, start.year)
            balance = (
                (
                    await db.execute(
                        select(LeaveBalance).where(
                            LeaveBalance.user_id == leave_employee.id,
                            LeaveBalance.leave_type == LeaveType.SICK,
                            LeaveBalance.year == start.year,
                        )
                    )
                )
                .scalars()
                .first()
            )
        # Sick leave is allocated 8 days; set used to 6 so only 2 remain
        balance.used = Decimal("6.00")
        await db.commit()

        # Approve 1-day leave (OK: 6+1=7 <= 8)
        leave1 = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.SICK,
                from_date=start,
                to_date=start,
                reason="Partial fill 1",
            ),
        )
        await leave_service.approve_leave(db, approver, leave1.id)

        # Approve another 1-day leave (OK: 7+1=8 <= 8)
        leave2 = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.SICK,
                from_date=start + timedelta(days=7),
                to_date=start + timedelta(days=7),
                reason="Partial fill 2",
            ),
        )
        await leave_service.approve_leave(db, approver, leave2.id)

        # Third approval must fail (8+1=9 > 8)
        leave3 = await leave_service.apply_leave(
            db,
            leave_employee,
            LeaveApplyRequest(
                leave_type=LeaveType.SICK,
                from_date=start + timedelta(days=14),
                to_date=start + timedelta(days=14),
                reason="Should fail",
            ),
        )
        with pytest.raises(LeaveError) as exc_info:
            await leave_service.approve_leave(db, approver, leave3.id)
        assert exc_info.value.status_code == 409
