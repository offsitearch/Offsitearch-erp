import calendar
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import (
    Attendance,
    Holiday,
    OrgLevel,
    PayrollEntry,
    PayrollRun,
    SalaryComponent,
    User,
)
from app.utils.enums import AttendanceStatus

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

PAY_ADMIN_EMAIL = "pay.admin@studioerp.dev"
PAY_ADMIN_PASSWORD = "pay-admin-pass-123"
PAY_EMP_EMAIL = "pay.emp@studioerp.dev"
PAY_EMP_PASSWORD = "pay-emp-pass-123"

PAYROLL_MONTH = 12
PAYROLL_YEAR = 2099


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
async def pay_owner():
    return await _create_user(PAY_ADMIN_EMAIL, PAY_ADMIN_PASSWORD, "Payroll Owner", "L1")


@pytest.fixture(scope="session")
async def pay_employee():
    return await _create_user(PAY_EMP_EMAIL, PAY_EMP_PASSWORD, "Payroll Employee")


@pytest.fixture(scope="session")
async def pay_salary(pay_employee: User) -> SalaryComponent:
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(SalaryComponent).where(SalaryComponent.user_id == pay_employee.id)
        )
        if existing is not None:
            return existing
        salary = SalaryComponent(
            user_id=pay_employee.id,
            basic=50000,
            hra=20000,
            special_allowance=10000,
            pf_deduction=5000,
        )
        db.add(salary)
        await db.commit()
        await db.refresh(salary)
        return salary


@pytest.fixture(scope="session")
async def pay_attendance(pay_employee: User) -> None:
    async with AsyncSessionLocal() as db:
        last_day = calendar.monthrange(PAYROLL_YEAR, PAYROLL_MONTH)[1]
        for day in range(1, last_day + 1):
            day_date = date(PAYROLL_YEAR, PAYROLL_MONTH, day)
            if day_date.weekday() >= 5:
                continue
            existing = await db.scalar(
                select(Attendance).where(
                    Attendance.user_id == pay_employee.id, Attendance.date == day_date
                )
            )
            if existing is not None:
                continue
            db.add(
                Attendance(
                    user_id=pay_employee.id,
                    date=day_date,
                    status=AttendanceStatus.PRESENT,
                )
            )
        await db.commit()


@pytest.fixture(scope="session")
async def clean_payroll_run() -> None:
    async with AsyncSessionLocal() as db:
        run = await db.scalar(
            select(PayrollRun).where(
                PayrollRun.month == PAYROLL_MONTH, PayrollRun.year == PAYROLL_YEAR
            )
        )
        if run is not None:
            await db.execute(delete(PayrollEntry).where(PayrollEntry.payroll_run_id == run.id))
            await db.delete(run)
            await db.commit()


@pytest.fixture(scope="session")
async def weekend_holiday() -> date:
    holiday_date = date(PAYROLL_YEAR, PAYROLL_MONTH, 1)
    for day in range(1, 8):
        candidate = date(PAYROLL_YEAR, PAYROLL_MONTH, day)
        if candidate.weekday() == 5:
            holiday_date = candidate
            break
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Holiday).where(Holiday.date == holiday_date))
        if existing is None:
            db.add(Holiday(name="Weekend Holiday", date=holiday_date))
            await db.commit()
    yield holiday_date
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Holiday).where(Holiday.date == holiday_date))
        await db.commit()


async def test_payroll_process_and_payslip(
    pay_owner: User,
    pay_employee: User,
    pay_salary: SalaryComponent,
    pay_attendance: None,
    clean_payroll_run: None,
    weekend_holiday: date,
) -> None:
    assert weekend_holiday.weekday() == 5
    last_day = calendar.monthrange(PAYROLL_YEAR, PAYROLL_MONTH)[1]
    payable = sum(
        1 for day in range(1, last_day + 1) if date(PAYROLL_YEAR, PAYROLL_MONTH, day).weekday() < 5
    )

    async with _client() as client:
        token = await _login(client, PAY_ADMIN_EMAIL, PAY_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        preview = await client.get(
            f"/api/v1/payroll?month={PAYROLL_MONTH}&year={PAYROLL_YEAR}", headers=headers
        )
        assert preview.status_code == 200
        assert preview.json()["is_preview"] is True
        employee_entry = next(
            e for e in preview.json()["entries"] if e["user_id"] == pay_employee.id
        )
        assert employee_entry["working_days"] == payable

        processed = await client.post(
            "/api/v1/payroll/process",
            json={"month": PAYROLL_MONTH, "year": PAYROLL_YEAR},
            headers=headers,
        )
        assert processed.status_code == 200
        body = processed.json()
        assert body["is_preview"] is False
        assert body["status"] == "processed"
        assert body["id"] is not None
        entry = next(e for e in body["entries"] if e["user_id"] == pay_employee.id)
        assert entry["working_days"] == payable
        assert float(entry["gross_salary"]) == pytest.approx(80000.0)
        assert float(entry["deductions"]) == pytest.approx(5000.0)
        assert float(entry["net_pay"]) == pytest.approx(75000.0)

        again = await client.get(
            f"/api/v1/payroll?month={PAYROLL_MONTH}&year={PAYROLL_YEAR}", headers=headers
        )
        assert again.json()["is_preview"] is False
        assert again.json()["id"] == body["id"]

        redo = await client.post(
            "/api/v1/payroll/process",
            json={"month": PAYROLL_MONTH, "year": PAYROLL_YEAR},
            headers=headers,
        )
        assert redo.status_code == 409

        payslip = await client.get(
            f"/api/v1/payroll/{PAYROLL_MONTH}/{PAYROLL_YEAR}/payslips/{pay_employee.id}",
            headers=headers,
        )
        assert payslip.status_code == 200
        assert payslip.headers["content-type"].startswith("application/pdf")
        assert payslip.content.startswith(b"%PDF")


async def test_payroll_requires_admin(pay_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, PAY_EMP_EMAIL, PAY_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/payroll", headers=headers)
        assert response.status_code == 403


async def test_payroll_department_head_denied() -> None:
    """L2 Department Head is below the financial boundary: no payroll."""
    email = "pay.manager@studioerp.dev"
    password = "pay-manager-pass-123"
    await _create_user(email, password, "Payroll Manager", "L2")
    async with _client() as client:
        token = await _login(client, email, password)
        headers = {"Authorization": f"Bearer {token}"}
        for method, path in (
            ("GET", "/api/v1/payroll"),
            ("POST", "/api/v1/payroll/process"),
            ("GET", f"/api/v1/payroll/{PAYROLL_MONTH}/{PAYROLL_YEAR}/payslips/1"),
        ):
            response = await client.request(
                method,
                path,
                headers=headers,
                json=({"month": PAYROLL_MONTH, "year": PAYROLL_YEAR} if method == "POST" else None),
            )
            assert response.status_code == 403


async def _ensure_attendance(db, user_id: int, day_date: date, status: AttendanceStatus) -> None:
    existing = await db.scalar(
        select(Attendance).where(Attendance.user_id == user_id, Attendance.date == day_date)
    )
    if existing is None:
        db.add(Attendance(user_id=user_id, date=day_date, status=status))


async def test_payroll_proration_and_leave(
    pay_owner: User, pay_employee: User, pay_salary: SalaryComponent
) -> None:
    month, year = 1, 2100
    last_day = calendar.monthrange(year, month)[1]
    payable = sum(1 for day in range(1, last_day + 1) if date(year, month, day).weekday() < 5)
    weekdays = [
        date(year, month, d) for d in range(1, last_day + 1) if date(year, month, d).weekday() < 5
    ]

    async with AsyncSessionLocal() as db:
        for day in weekdays[:10]:
            await _ensure_attendance(db, pay_employee.id, day, AttendanceStatus.PRESENT)
        for day in weekdays[10:15]:
            await _ensure_attendance(db, pay_employee.id, day, AttendanceStatus.ON_LEAVE)
        await db.commit()

    async with _client() as client:
        token = await _login(client, PAY_ADMIN_EMAIL, PAY_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        preview = await client.get(f"/api/v1/payroll?month={month}&year={year}", headers=headers)
        assert preview.status_code == 200
        body = preview.json()
        assert body["is_preview"] is True
        entry = next(e for e in body["entries"] if e["user_id"] == pay_employee.id)
        assert entry["working_days"] == 15
        assert float(entry["gross_salary"]) == pytest.approx(80000 * 15 / payable)
        assert float(entry["deductions"]) == pytest.approx(5000 * 15 / payable)
        assert float(entry["net_pay"]) == pytest.approx(
            80000 * 15 / payable - 5000 * 15 / payable, abs=0.02
        )
        assert float(body["total_pay"]) == pytest.approx(float(entry["net_pay"]), abs=0.02)


async def test_weekday_holiday_affects_payable(
    pay_owner: User, pay_employee: User, pay_salary: SalaryComponent
) -> None:
    month, year = 4, 2100
    last_day = calendar.monthrange(year, month)[1]
    weekdays = [
        date(year, month, d) for d in range(1, last_day + 1) if date(year, month, d).weekday() < 5
    ]
    holiday = weekdays[0]
    assert holiday.weekday() < 5
    payable = len(weekdays) - 1

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Holiday).where(Holiday.date == holiday))
        if existing is None:
            db.add(Holiday(name="Weekday Holiday", date=holiday))
        for day in weekdays[1:]:
            await _ensure_attendance(db, pay_employee.id, day, AttendanceStatus.PRESENT)
        await db.commit()

    try:
        async with _client() as client:
            token = await _login(client, PAY_ADMIN_EMAIL, PAY_ADMIN_PASSWORD)
            headers = {"Authorization": f"Bearer {token}"}
            preview = await client.get(
                f"/api/v1/payroll?month={month}&year={year}", headers=headers
            )
            assert preview.status_code == 200
            entry = next(e for e in preview.json()["entries"] if e["user_id"] == pay_employee.id)
            assert entry["working_days"] == payable
            assert float(entry["gross_salary"]) == pytest.approx(80000.0)
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Holiday).where(Holiday.date == holiday))
            await db.commit()


async def test_payroll_payslip_404s(
    pay_owner: User, pay_employee: User, pay_salary: SalaryComponent
) -> None:
    unprocessed_month, unprocessed_year = 3, 2100
    processed_month, processed_year = 2, 2100

    async with _client() as client:
        token = await _login(client, PAY_ADMIN_EMAIL, PAY_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        # Unprocessed month → payslip 404.
        missing = await client.get(
            f"/api/v1/payroll/{unprocessed_month}/{unprocessed_year}/payslips/{pay_employee.id}",
            headers=headers,
        )
        assert missing.status_code == 404

        # Process a fresh month; pay_owner has no salary → not in the run.
        processed = await client.post(
            "/api/v1/payroll/process",
            json={"month": processed_month, "year": processed_year},
            headers=headers,
        )
        assert processed.status_code == 200
        run_entry_ids = {e["user_id"] for e in processed.json()["entries"]}
        assert pay_owner.id not in run_entry_ids
        assert pay_employee.id in run_entry_ids

        missing_entry = await client.get(
            f"/api/v1/payroll/{processed_month}/{processed_year}/payslips/{pay_owner.id}",
            headers=headers,
        )
        assert missing_entry.status_code == 404
