from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import select
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User
from app.modules.attendance.repository import attendance_repository
from app.modules.attendance.schemas import AttendanceUpdateRequest, CheckInRequest, CheckOutRequest
from app.seeds.data import ATTENDANCE_SETTINGS
from app.modules.attendance import service as attendance_service
from app.utils.enums import AttendanceStatus
from app.utils.errors import AttendanceError

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

EMPLOYEE_EMAIL = "attendance.employee@studioerp.dev"
EMPLOYEE_PASSWORD = "employee-pass-123"
LEAD_EMAIL = "attendance.lead@studioerp.dev"
LEAD_PASSWORD = "lead-pass-123"


def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


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
async def employee():
    return await _create_user(EMPLOYEE_EMAIL, EMPLOYEE_PASSWORD, "Test Employee")


@pytest.fixture(scope="session")
async def lead():
    return await _create_user(LEAD_EMAIL, LEAD_PASSWORD, "Test Lead", "L3")


async def test_check_in_check_out_service_flow(employee: User) -> None:
    check_in_time = datetime(2026, 8, 10, 4, 30, tzinfo=timezone.utc)  # 10:00 IST → late 60
    check_out_time = datetime(2026, 8, 10, 12, 30, tzinfo=timezone.utc)  # 8h raw

    async with AsyncSessionLocal() as db:
        record = await attendance_service.check_in(
            db, employee, CheckInRequest(method="web"), now=check_in_time
        )
        assert record.date == date(2026, 8, 10)
        assert record.status == AttendanceStatus.LATE
        assert record.late_minutes == 60

        # duplicate check-in is rejected
        with pytest.raises(AttendanceError):
            await attendance_service.check_in(
                db, employee, CheckInRequest(method="web"), now=check_in_time
            )

        record = await attendance_service.check_out(
            db, employee, CheckOutRequest(), now=check_out_time
        )
        assert record.check_out_time == check_out_time
        assert float(record.total_hours) == 8.0


async def test_check_out_without_check_in_rejected(employee: User) -> None:
    with pytest.raises(AttendanceError) as exc_info:
        async with AsyncSessionLocal() as db:
            await attendance_service.check_out(db, employee, CheckOutRequest())
    assert exc_info.value.status_code == 404


async def test_late_and_half_day_logic() -> None:
    cfg = {key: dict(value) for key, value in ATTENDANCE_SETTINGS.items()}
    work = cfg["working_hours"]
    late = cfg["late_policy"]

    status, minutes = attendance_service.compute_check_in_status(
        datetime.combine(date(2026, 8, 10), time(8, 55)), work, late
    )
    assert (status, minutes) == (AttendanceStatus.PRESENT, 0)

    status, minutes = attendance_service.compute_check_in_status(
        datetime.combine(date(2026, 8, 10), time(9, 20)), work, late
    )
    assert (status, minutes) == (AttendanceStatus.LATE, 20)

    status, minutes = attendance_service.compute_check_in_status(
        datetime.combine(date(2026, 8, 10), time(11, 30)), work, late
    )
    assert (status, minutes) == (AttendanceStatus.HALF_DAY, 150)


async def test_total_hours_subtracts_break() -> None:
    work = dict(ATTENDANCE_SETTINGS["working_hours"])
    check_in = datetime(2026, 8, 10, 3, 30, tzinfo=timezone.utc)
    check_out = datetime(2026, 8, 10, 12, 30, tzinfo=timezone.utc)
    assert float(attendance_service.compute_total_hours(check_in, check_out, work)) == 9.0


async def test_http_check_in_flow(employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMPLOYEE_EMAIL, EMPLOYEE_PASSWORD)
        today = attendance_service.now_local().date()

        check_in = await client.post(
            "/api/v1/attendance/check-in",
            headers={"Authorization": f"Bearer {token}"},
            json={"method": "web"},
        )
        assert check_in.status_code == 201
        body = check_in.json()
        assert body["user_id"] == employee.id
        assert body["date"] == today.isoformat()
        assert body["status"] in {"present", "late", "half_day"}

        duplicate = await client.post(
            "/api/v1/attendance/check-in",
            headers={"Authorization": f"Bearer {token}"},
            json={"method": "web"},
        )
        assert duplicate.status_code == 409

        check_out = await client.post(
            "/api/v1/attendance/check-out",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert check_out.status_code == 200
        assert check_out.json()["check_out_time"] is not None

        summary = await client.get(
            "/api/v1/attendance/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert summary.status_code == 200
        assert summary.json()["user"]["email"] == EMPLOYEE_EMAIL


async def test_admin_endpoints_denied_for_employee(employee: User) -> None:
    async with _client() as client:
        token = await _login(client, EMPLOYEE_EMAIL, EMPLOYEE_PASSWORD)
        today = await client.get(
            "/api/v1/attendance/today", headers={"Authorization": f"Bearer {token}"}
        )
        users = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        report = await client.get(
            "/api/v1/attendance/report?from_date=2026-08-01&to_date=2026-08-31",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert today.status_code == 403
    assert users.status_code == 403
    assert report.status_code == 403


async def test_lead_views_attendance_but_cannot_edit(lead: User, employee: User) -> None:
    async with _client() as client:
        token = await _login(client, LEAD_EMAIL, LEAD_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        today = await client.get("/api/v1/attendance/today", headers=headers)
        assert today.status_code == 200

        by_date = await client.get("/api/v1/attendance/date/2026-08-10", headers=headers)
        assert by_date.status_code == 200

        report = await client.get(
            "/api/v1/attendance/report?from_date=2026-08-01&to_date=2026-08-31",
            headers=headers,
        )
        assert report.status_code == 200

        bulk = await client.post(
            "/api/v1/attendance/bulk",
            headers=headers,
            json={
                "date": "2026-08-10",
                "entries": [{"user_id": employee.id, "status": "present"}],
            },
        )
        assert bulk.status_code == 403

        record = await client.get("/api/v1/attendance/me", headers=headers)
        assert record.status_code == 200


async def test_admin_bulk_and_employee_summary(employee: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)

        today = await client.get(
            "/api/v1/attendance/today", headers={"Authorization": f"Bearer {token}"}
        )
        assert today.status_code == 200

        bulk = await client.post(
            "/api/v1/attendance/bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "date": "2026-08-11",
                "entries": [{"user_id": employee.id, "status": "present"}],
            },
        )
        assert bulk.status_code == 200

        summary = await client.get(
            f"/api/v1/attendance/employee/{employee.id}?month=8&year=2026",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert summary.status_code == 200
        assert summary.json()["user"]["id"] == employee.id


async def test_holidays_list() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        response = await client.get(
            "/api/v1/attendance/holidays?year=2026",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert {"Republic Day", "Independence Day", "Diwali"} <= names


async def test_report_csv() -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        response = await client.get(
            "/api/v1/attendance/report?from_date=2026-08-01&to_date=2026-08-31&format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Name" in response.text


async def test_check_out_twice_rejected(employee: User) -> None:
    async with AsyncSessionLocal() as db:
        check_in_time = datetime(2026, 8, 12, 4, 0, tzinfo=timezone.utc)
        check_out_time = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        await attendance_service.check_in(
            db, employee, CheckInRequest(method="web"), now=check_in_time
        )
        await attendance_service.check_out(db, employee, CheckOutRequest(), now=check_out_time)
        with pytest.raises(AttendanceError, match="Already checked out"):
            await attendance_service.check_out(db, employee, CheckOutRequest(), now=check_out_time)


async def test_bulk_mark_updates_existing_with_times(employee: User) -> None:
    admin = await _create_user(
        "attendance.admin@studioerp.dev", "att-admin-pass-123", "Attendance Admin", "L1"
    )
    bulk_date = date(2026, 8, 13)

    async with AsyncSessionLocal() as db:
        await attendance_service.bulk_mark(
            db,
            admin,
            bulk_date,
            [
                type(
                    "Entry",
                    (),
                    {
                        "user_id": employee.id,
                        "status": AttendanceStatus.PRESENT,
                        "notes": None,
                        "check_in_time": None,
                        "check_out_time": None,
                    },
                )()
            ],
        )

    # Second pass updates the same record with explicit times → total_hours recomputed.
    check_in = datetime(2026, 8, 13, 3, 30, tzinfo=timezone.utc)
    check_out = datetime(2026, 8, 13, 12, 30, tzinfo=timezone.utc)
    async with AsyncSessionLocal() as db:
        await attendance_service.bulk_mark(
            db,
            admin,
            bulk_date,
            [
                type(
                    "Entry",
                    (),
                    {
                        "user_id": employee.id,
                        "status": AttendanceStatus.PRESENT,
                        "notes": "fixed",
                        "check_in_time": check_in,
                        "check_out_time": check_out,
                    },
                )()
            ],
        )
        updated = await attendance_repository.get_by_user_date(db, employee.id, bulk_date)
    assert updated is not None
    assert updated.status == AttendanceStatus.PRESENT
    assert float(updated.total_hours) == 9.0
    assert updated.notes == "fixed"


async def test_update_record_recomputes_status(employee: User) -> None:
    async with AsyncSessionLocal() as db:
        await attendance_service.check_in(
            db,
            employee,
            CheckInRequest(method="web"),
            now=datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc),
        )
        record = await attendance_repository.get_by_user_date(db, employee.id, date(2026, 8, 14))

        # Admin moves check-in later → status + late minutes recomputed.
        late_in = datetime(2026, 8, 14, 4, 30, tzinfo=timezone.utc)  # 10:00 IST
        payload = AttendanceUpdateRequest(
            status=None, check_in_time=late_in, check_out_time=None, notes=None
        )
        updated = await attendance_service.update_record(db, record.id, payload)
    assert updated.status == AttendanceStatus.LATE
    assert updated.late_minutes == 60


async def test_update_record_clears_times_with_explicit_null(employee: User) -> None:
    async with AsyncSessionLocal() as db:
        await attendance_service.check_in(
            db,
            employee,
            CheckInRequest(method="web"),
            now=datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc),
        )
        await attendance_service.check_out(
            db, employee, CheckOutRequest(), now=datetime(2026, 8, 15, 6, 0, tzinfo=timezone.utc)
        )
        record = await attendance_repository.get_by_user_date(db, employee.id, date(2026, 8, 15))
        assert record.total_hours > 0

        # Admin clears the times explicitly → hours reset, status stays as given.
        payload = AttendanceUpdateRequest(
            status=AttendanceStatus.ABSENT, check_in_time=None, check_out_time=None, notes=None
        )
        updated = await attendance_service.update_record(db, record.id, payload)
    assert updated.check_in_time is None
    assert updated.check_out_time is None
    assert updated.total_hours == 0
    assert updated.status == AttendanceStatus.ABSENT


async def test_recheck_in_after_times_cleared(employee: User) -> None:
    async with AsyncSessionLocal() as db:
        await attendance_service.check_in(
            db,
            employee,
            CheckInRequest(method="web"),
            now=datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc),
        )
        record = await attendance_repository.get_by_user_date(db, employee.id, date(2026, 8, 15))
        await attendance_service.update_record(
            db,
            record.id,
            AttendanceUpdateRequest(
                status=AttendanceStatus.ABSENT, check_in_time=None, check_out_time=None
            ),
        )

        # A cleared record can be checked in again without a duplicate row.
        again = await attendance_service.check_in(
            db,
            employee,
            CheckInRequest(method="web"),
            now=datetime(2026, 8, 15, 4, 30, tzinfo=timezone.utc),
        )
        assert again.id == record.id
        assert again.check_in_time is not None
        assert again.check_out_time is None

        with pytest.raises(AttendanceError) as exc_info:
            await attendance_service.check_in(
                db,
                employee,
                CheckInRequest(method="web"),
                now=datetime(2026, 8, 15, 5, 0, tzinfo=timezone.utc),
            )
        assert exc_info.value.status_code == 409


async def test_update_record_not_found() -> None:
    with pytest.raises(AttendanceError) as exc_info:
        async with AsyncSessionLocal() as db:
            await attendance_service.update_record(db, 999999, AttendanceUpdateRequest())
    assert exc_info.value.status_code == 404


async def test_monthly_records_totals(employee: User) -> None:
    async with AsyncSessionLocal() as db:
        records, totals = await attendance_service.monthly_records(db, employee.id, 2026, 8)
    assert isinstance(totals, dict)
    assert sum(totals.values()) == len(records)


async def test_rows_for_date_filters(employee: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        today = await client.get("/api/v1/attendance/today?status=present", headers=headers)
    assert today.status_code == 200
    assert isinstance(today.json(), list)


async def test_to_local_treats_naive_as_utc() -> None:
    naive = datetime(2026, 8, 10, 4, 30)
    local = attendance_service.to_local(naive)
    assert local.tzinfo is not None
    assert local.utcoffset() is not None
