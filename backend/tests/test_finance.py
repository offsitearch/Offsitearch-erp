import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models import OrgLevel, User

SUPERUSER_EMAIL = settings.first_superuser_email
SUPERUSER_PASSWORD = settings.first_superuser_password

FIN_ADMIN_EMAIL = "fin.admin@studioerp.dev"
FIN_ADMIN_PASSWORD = "fin-admin-pass-123"
FIN_EMP_EMAIL = "fin.emp@studioerp.dev"
FIN_EMP_PASSWORD = "fin-emp-pass-123"


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
async def fin_admin():
    return await _create_user(FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD, "Finance Director", "L1")


@pytest.fixture(scope="session")
async def fin_employee():
    return await _create_user(FIN_EMP_EMAIL, FIN_EMP_PASSWORD, "Finance Employee")


async def _make_client(headers: dict) -> int:
    async with _client() as client:
        created = await client.post(
            "/api/v1/clients",
            json={"name": "Finance Client Ltd", "client_type": "company"},
            headers=headers,
        )
        assert created.status_code == 201
        return created.json()["id"]


async def _make_project(headers: dict, client_id: int) -> int:
    async with _client() as client:
        created = await client.post(
            "/api/v1/projects",
            json={
                "name": "Finance Test Tower",
                "project_type": "commercial",
                "client_id": client_id,
                "status": "draft",
            },
            headers=headers,
        )
        assert created.status_code == 201
        return created.json()["id"]


async def test_invoice_workflow_and_overview(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        client_id = await _make_client(headers)
        project_id = await _make_project(headers, client_id)

        created = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "project_id": project_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "tax_percent": 18,
                "items": [
                    {"description": "Concept design", "quantity": 2, "rate": 500},
                    {"description": "Permit drawings", "quantity": 1, "rate": 500},
                ],
                "terms": "Net 30 days",
            },
            headers=headers,
        )
        assert created.status_code == 201
        body = created.json()
        assert body["invoice_number"].startswith("INV-2026-")
        assert float(body["subtotal"]) == pytest.approx(1500.0)
        assert float(body["tax_amount"]) == pytest.approx(270.0)
        assert float(body["total"]) == pytest.approx(1770.0)
        assert body["status"] == "draft"
        assert body["client_name"] == "Finance Client Ltd"
        invoice_id = body["id"]

        sent = await client.post(f"/api/v1/invoices/{invoice_id}/send", headers=headers)
        assert sent.status_code == 200
        assert sent.json()["status"] == "sent"

        partial = await client.post(
            f"/api/v1/invoices/{invoice_id}/payment",
            json={"amount": 1000, "method": "bank_transfer", "payment_date": "2026-08-12"},
            headers=headers,
        )
        assert partial.status_code == 200
        assert partial.json()["status"] == "partial"
        assert float(partial.json()["paid_amount"]) == pytest.approx(1000.0)

        paid = await client.post(
            f"/api/v1/invoices/{invoice_id}/payment",
            json={"amount": 770, "method": "upi"},
            headers=headers,
        )
        assert paid.status_code == 200
        assert paid.json()["status"] == "paid"

        pdf = await client.get(f"/api/v1/invoices/{invoice_id}/pdf", headers=headers)
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF")

        detail = await client.get(f"/api/v1/invoices/{invoice_id}", headers=headers)
        assert detail.status_code == 200
        assert len(detail.json()["items"]) == 2

        # The finance director (L1) reads the invoiced/received figures
        # under the unified financial-access policy.
        overview = await client.get("/api/v1/finance/overview?period=month", headers=headers)
        assert overview.status_code == 200
        data = overview.json()
        assert float(data["invoiced"]) >= 1770.0
        assert float(data["received"]) >= 1770.0
        assert float(data["profit"]) == pytest.approx(
            float(data["received"]) - float(data["expenses"])
        )


async def test_employee_cannot_access_finance(fin_employee: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_EMP_EMAIL, FIN_EMP_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": 1,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "items": [{"description": "Nope", "quantity": 1, "rate": 10}],
            },
            headers=headers,
        )
        assert response.status_code == 403
        overview = await client.get("/api/v1/finance/overview", headers=headers)
        assert overview.status_code == 403


async def test_expenses_and_overview(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}

        approved = await client.post(
            "/api/v1/expenses",
            data={
                "category": "material",
                "description": "HPL sheets",
                "amount": "250.50",
                "paid_by": "A. Rao",
            },
            files={"file": ("receipt.pdf", b"%PDF-1.4 sample receipt", "application/pdf")},
            headers=headers,
        )
        assert approved.status_code == 201
        approved_id = approved.json()["id"]
        assert approved.json()["status"] == "pending"
        assert approved.json()["receipt_path"] is not None

        decision = await client.patch(
            f"/api/v1/expenses/{approved_id}/approve",
            json={"approve": True},
            headers=headers,
        )
        assert decision.status_code == 200
        assert decision.json()["status"] == "approved"

        rejected = await client.post(
            "/api/v1/expenses",
            data={"category": "travel", "description": "Site cab", "amount": "100.00"},
            headers=headers,
        )
        assert rejected.status_code == 201
        rejected_id = rejected.json()["id"]
        rejected_decision = await client.patch(
            f"/api/v1/expenses/{rejected_id}/approve",
            json={"approve": False},
            headers=headers,
        )
        assert rejected_decision.json()["status"] == "rejected"

        listing = await client.get("/api/v1/expenses", headers=headers)
        assert listing.status_code == 200
        assert len(listing.json()) >= 2

        # Revenue aggregates are part of the same financial boundary.
        overview = await client.get("/api/v1/finance/overview?period=month", headers=headers)
        assert overview.status_code == 200
        data = overview.json()
        assert float(data["expenses"]) >= 250.50
        assert data["expense_count"] >= 1


async def test_invoice_number_increments(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        first = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "items": [{"description": "One", "quantity": 1, "rate": 100}],
            },
            headers=headers,
        )
        assert first.status_code == 201
        first_number = first.json()["invoice_number"]
        second = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-11",
                "due_date": "2026-09-11",
                "items": [{"description": "Two", "quantity": 1, "rate": 200}],
            },
            headers=headers,
        )
        assert second.status_code == 201
        second_number = second.json()["invoice_number"]
        seq = int(first_number.rsplit("-", 1)[1])
        assert second_number == f"INV-2026-{seq + 1:03d}"


async def test_update_draft_invoice_replaces_items(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        created = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "tax_percent": 18,
                "items": [{"description": "A", "quantity": 1, "rate": 100}],
            },
            headers=headers,
        )
        invoice_id = created.json()["id"]

        updated = await client.patch(
            f"/api/v1/invoices/{invoice_id}",
            json={
                "tax_percent": 10,
                "items": [
                    {"description": "Branding", "quantity": 2, "rate": 150},
                    {"description": "Consulting", "quantity": 1, "rate": 100},
                ],
            },
            headers=headers,
        )
        assert updated.status_code == 200
        body = updated.json()
        assert float(body["subtotal"]) == pytest.approx(400.0)
        assert float(body["tax_amount"]) == pytest.approx(40.0)
        assert float(body["total"]) == pytest.approx(440.0)
        assert [item["description"] for item in body["items"]] == [
            "Branding",
            "Consulting",
        ]

        # Non-draft invoices cannot be edited.
        sent = await client.post(f"/api/v1/invoices/{invoice_id}/send", headers=headers)
        assert sent.status_code == 200, sent.text
        rejected = await client.patch(
            f"/api/v1/invoices/{invoice_id}",
            json={"terms": "Net 10"},
            headers=headers,
        )
        assert rejected.status_code == 409


async def test_send_invoice_errors(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        created = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "items": [{"description": "One", "quantity": 1, "rate": 100}],
            },
            headers=headers,
        )
        invoice_id = created.json()["id"]

        sent = await client.post(f"/api/v1/invoices/{invoice_id}/send", headers=headers)
        assert sent.status_code == 200
        assert sent.json()["status"] == "sent"

        again = await client.post(f"/api/v1/invoices/{invoice_id}/send", headers=headers)
        assert again.status_code == 409


async def test_record_payment_errors_and_auto_send(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        created = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "items": [{"description": "One", "quantity": 1, "rate": 1000}],
            },
            headers=headers,
        )
        invoice_id = created.json()["id"]

        invalid_method = await client.post(
            f"/api/v1/invoices/{invoice_id}/payment",
            json={"amount": 100, "method": "bitcoin"},
            headers=headers,
        )
        assert invalid_method.status_code == 409

        # Payment on an unsent invoice auto-sends it.
        partial = await client.post(
            f"/api/v1/invoices/{invoice_id}/payment",
            json={"amount": 400, "method": "cash", "payment_date": "2026-08-12"},
            headers=headers,
        )
        assert partial.status_code == 200
        assert partial.json()["status"] == "partial"
        assert partial.json()["sent_at"] is not None

        overpayment = await client.post(
            f"/api/v1/invoices/{invoice_id}/payment",
            json={"amount": 900, "method": "cash"},
            headers=headers,
        )
        assert overpayment.status_code == 409


async def test_payment_and_send_rejected_when_cancelled(fin_admin: User) -> None:
    from sqlalchemy import select

    from app.models import Invoice
    from app.utils.enums import InvoiceStatus

    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        created = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "items": [{"description": "One", "quantity": 1, "rate": 100}],
            },
            headers=headers,
        )
        invoice_id = created.json()["id"]

        async with AsyncSessionLocal() as db:
            invoice = await db.scalar(select(Invoice).where(Invoice.id == invoice_id))
            invoice.status = InvoiceStatus.CANCELLED
            await db.commit()

        send = await client.post(f"/api/v1/invoices/{invoice_id}/send", headers=headers)
        assert send.status_code == 409
        payment = await client.post(
            f"/api/v1/invoices/{invoice_id}/payment",
            json={"amount": 100, "method": "cash"},
            headers=headers,
        )
        assert payment.status_code == 409


async def test_overdue_and_list_filters(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        overdue = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-01",
                "due_date": "2020-01-01",
                "items": [{"description": "Old", "quantity": 1, "rate": 500}],
            },
            headers=headers,
        )
        invoice_id = overdue.json()["id"]
        await client.post(f"/api/v1/invoices/{invoice_id}/send", headers=headers)

        paid_invoice = await client.post(
            "/api/v1/invoices",
            json={
                "client_id": client_id,
                "invoice_date": "2026-08-10",
                "due_date": "2026-09-10",
                "items": [{"description": "Paid", "quantity": 1, "rate": 200}],
            },
            headers=headers,
        )
        paid_id = paid_invoice.json()["id"]
        await client.post(
            f"/api/v1/invoices/{paid_id}/payment",
            json={"amount": 200, "method": "upi"},
            headers=headers,
        )

        listing = await client.get("/api/v1/invoices", headers=headers)
        all_ids = [row["id"] for row in listing.json()["items"]]
        assert invoice_id in all_ids and paid_id in all_ids
        by_status = await client.get(
            f"/api/v1/invoices?status={overdue.json()['invoice_number']}", headers=headers
        )
        assert by_status.status_code == 200
        by_status = await client.get("/api/v1/invoices?status=overdue", headers=headers)
        assert invoice_id in [row["id"] for row in by_status.json()["items"]]
        by_client = await client.get(f"/api/v1/invoices?client_id={client_id}", headers=headers)
        assert invoice_id in [row["id"] for row in by_client.json()["items"]]
        by_search = await client.get(
            f"/api/v1/invoices?search={overdue.json()['invoice_number']}", headers=headers
        )
        assert [row["id"] for row in by_search.json()["items"]] == [invoice_id]


async def test_get_invoice_and_pdf_404(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        missing = await client.get("/api/v1/invoices/999999", headers=headers)
        assert missing.status_code == 404
        missing_pdf = await client.get("/api/v1/invoices/999999/pdf", headers=headers)
        assert missing_pdf.status_code == 404


async def test_expense_project_and_month_filters(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, FIN_ADMIN_EMAIL, FIN_ADMIN_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        client_id = await _make_client(headers)
        project_id = await _make_project(headers, client_id)

        old = await client.post(
            "/api/v1/expenses",
            data={
                "category": "software",
                "description": "AutoCAD license",
                "amount": "5000.00",
                "expense_date": "2025-01-15",
                "project_id": str(project_id),
                "paid_by": "R. Iyer",
            },
            headers=headers,
        )
        assert old.status_code == 201
        old_id = old.json()["id"]
        assert old.json()["project_code"] is not None

        filtered = await client.get(
            f"/api/v1/expenses?project_id={project_id}&month=1&year=2025", headers=headers
        )
        assert old_id in [row["id"] for row in filtered.json()["items"]]
        filtered_other_month = await client.get(
            "/api/v1/expenses?month=6&year=2025", headers=headers
        )
        assert old_id not in [row["id"] for row in filtered_other_month.json()["items"]]

        bad_project = await client.post(
            "/api/v1/expenses",
            data={"category": "other", "amount": "10.00", "project_id": "999999"},
            headers=headers,
        )
        assert bad_project.status_code == 404

        no_receipt = await client.get(f"/api/v1/expenses/{old_id}/receipt", headers=headers)
        assert no_receipt.status_code == 404


async def test_period_bounds_unit() -> None:
    from datetime import date as _date

    from app.modules.finance import service as finance_service

    today = _date.today()
    month_start, month_end = finance_service._period_bounds("month")
    assert month_start == _date(today.year, today.month, 1)
    assert month_end.month == (today.month % 12) + 1

    q_start_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start, quarter_end = finance_service._period_bounds("quarter")
    assert quarter_start == _date(today.year, q_start_month, 1)
    assert quarter_end > quarter_start

    year_start, year_end = finance_service._period_bounds("year")
    assert year_start == _date(today.year, 1, 1)
    assert year_end == _date(today.year + 1, 1, 1)

    all_start, all_end = finance_service._period_bounds("all")
    assert all_start.year == 1970
    assert all_end.year == 9999


async def test_overview_quarter_year_all(fin_admin: User) -> None:
    async with _client() as client:
        token = await _login(client, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        headers = {"Authorization": f"Bearer {token}"}
        for period in ("quarter", "year", "all"):
            overview = await client.get(
                f"/api/v1/finance/overview?period={period}", headers=headers
            )
            assert overview.status_code == 200
            data = overview.json()
            assert data["period"] == period
            assert float(data["invoiced"]) >= 0
            assert data["invoice_count"] >= 0
