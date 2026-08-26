"""Finance service.

Invoices, expenses, payments, PDF generation, and financial overview.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client, Project, User
from app.modules.finance.models import Expense, Invoice, InvoiceItem
from app.modules.finance.schemas import ExpenseCreate, InvoiceCreate, InvoiceUpdate
from app.utils.enums import ExpenseStatus, InvoiceStatus, PaymentMethod
from app.utils.errors import FinanceError
from app.modules.settings.service import get_studio_info
from app.utils.pdf import invoice_pdf
from app.utils.shared import now_local, q as _q, utc_now

_PENNY = Decimal("0.01")
logger = logging.getLogger(__name__)

_PENNY = Decimal("0.01")


def _today() -> date:
    return now_local().date()


def _status_for(invoice: Invoice, today: date) -> InvoiceStatus:
    if invoice.status == InvoiceStatus.CANCELLED:
        return InvoiceStatus.CANCELLED
    if invoice.paid_amount >= invoice.total:
        return InvoiceStatus.PAID
    if invoice.paid_amount > 0:
        return InvoiceStatus.PARTIAL
    if invoice.sent_at is not None and invoice.due_date < today:
        return InvoiceStatus.OVERDUE
    if invoice.sent_at is not None:
        return InvoiceStatus.SENT
    return InvoiceStatus.DRAFT


async def _items_for(db: AsyncSession, invoice_id: int) -> list[InvoiceItem]:
    rows = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id).order_by(InvoiceItem.id)
    )
    return list(rows.scalars().all())


def _invoice_dict(
    invoice: Invoice,
    items: list[InvoiceItem],
    client: Client | None,
    project_code: str | None,
    project_name: str | None = None,
) -> dict:
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "client_id": invoice.client_id,
        "client_name": client.name if client else None,
        "client_address": (client.address or None) if client else None,
        "client_gstin": (client.gst_number or None) if client else None,
        "project_id": invoice.project_id,
        "project_code": project_code,
        "project_name": project_name,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "subtotal": invoice.subtotal,
        "tax_percent": invoice.tax_percent,
        "tax_amount": invoice.tax_amount,
        "total": invoice.total,
        "status": _status_for(invoice, _today()).value,
        "sent_at": invoice.sent_at,
        "paid_amount": invoice.paid_amount,
        "payment_date": invoice.payment_date,
        "payment_method": invoice.payment_method.value if invoice.payment_method else None,
        "notes": invoice.notes,
        "terms": invoice.terms,
        "items": [
            {
                "id": item.id,
                "invoice_id": item.invoice_id,
                "description": item.description,
                "hsn_sac": item.hsn_sac,
                "quantity": item.quantity,
                "rate": item.rate,
                "amount": item.amount,
            }
            for item in items
        ],
    }


async def _next_invoice_number(db: AsyncSession, year: int) -> str:
    prefix = f"INV-{year}-"
    like = f"{prefix}%"
    numbers = (
        (await db.execute(select(Invoice.invoice_number).where(Invoice.invoice_number.like(like))))
        .scalars()
        .all()
    )
    nums = [int(n[len(prefix) :]) for n in numbers if n and n[len(prefix) :].isdigit()]
    return f"{prefix}{max(nums, default=0) + 1:03d}"


async def _validate_refs(db: AsyncSession, client_id: int, project_id: int | None) -> None:
    client = await db.get(Client, client_id)
    if client is None:
        raise FinanceError("Client not found", 404)
    if project_id is not None:
        project = await db.get(Project, project_id)
        if project is None:
            raise FinanceError("Project not found", 404)


def _totals(items: list[InvoiceItem], tax_percent: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = _q(sum((_q(item.quantity * item.rate) for item in items), Decimal("0")))
    tax_amount = _q(subtotal * tax_percent / Decimal("100"))
    return subtotal, tax_amount, _q(subtotal + tax_amount)


async def _make_items(invoice: Invoice, payload_items: list) -> list[InvoiceItem]:
    items = []
    for raw in payload_items:
        quantity = _q(raw.quantity)
        rate = _q(raw.rate)
        items.append(
            InvoiceItem(
                invoice=invoice,
                description=raw.description,
                hsn_sac=(raw.hsn_sac or None) if raw.hsn_sac else None,
                quantity=quantity,
                rate=rate,
                amount=_q(quantity * rate),
            )
        )
    return items


async def create_invoice(db: AsyncSession, payload: InvoiceCreate) -> dict:
    await _validate_refs(db, payload.client_id, payload.project_id)
    invoice = Invoice(
        invoice_number=await _next_invoice_number(db, payload.invoice_date.year),
        client_id=payload.client_id,
        project_id=payload.project_id,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        tax_percent=_q(payload.tax_percent),
        notes=payload.notes,
        terms=payload.terms,
    )
    items = await _make_items(invoice, payload.items)
    invoice.subtotal, invoice.tax_amount, invoice.total = _totals(items, payload.tax_percent)
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    items = await _items_for(db, invoice.id)
    client = await db.get(Client, invoice.client_id)
    project = await db.get(Project, invoice.project_id) if invoice.project_id else None
    return _invoice_dict(
        invoice,
        items,
        client,
        project.project_code if project else None,
        project.name if project else None,
    )


async def list_invoices(
    db: AsyncSession,
    status_: str | None = None,
    client_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = (
        select(Invoice, Client, Project.project_code)
        .join(Client, Client.id == Invoice.client_id)
        .outerjoin(Project, Project.id == Invoice.project_id)
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
    )
    if client_id is not None:
        stmt = stmt.where(Invoice.client_id == client_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Invoice.invoice_number.ilike(like))
    if status_ is None:
        # No status filter — use efficient SQL pagination
        count_stmt = (
            select(func.count()).select_from(Invoice).join(Client, Client.id == Invoice.client_id)
        )
        if client_id is not None:
            count_stmt = count_stmt.where(Invoice.client_id == client_id)
        if search:
            like = f"%{search}%"
            count_stmt = count_stmt.where(Invoice.invoice_number.ilike(like))
        total = (await db.scalar(count_stmt)) or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(stmt)).all()
        filtered = [(inv, client, pc) for inv, client, pc in rows]
    else:
        # Status filter requires runtime computation — load all, filter, paginate
        rows = (await db.execute(stmt)).all()
        today = _today()
        filtered = []
        for invoice, client, project_code in rows:
            effective = _status_for(invoice, today)
            if effective.value != status_:
                continue
            filtered.append((invoice, client, project_code))
        total = len(filtered)
        start = (page - 1) * page_size
        filtered = filtered[start : start + page_size]
    invoice_ids = [invoice.id for invoice, _, _ in filtered]
    items_by_invoice: dict[int, list[InvoiceItem]] = {}
    if invoice_ids:
        item_rows = (
            (
                await db.execute(
                    select(InvoiceItem)
                    .where(InvoiceItem.invoice_id.in_(invoice_ids))
                    .order_by(InvoiceItem.id)
                )
            )
            .scalars()
            .all()
        )
        for item in item_rows:
            items_by_invoice.setdefault(item.invoice_id, []).append(item)
    result = [
        _invoice_dict(invoice, items_by_invoice.get(invoice.id, []), client, project_code)
        for invoice, client, project_code in filtered
    ]
    return result, total


async def get_invoice(db: AsyncSession, invoice_id: int) -> dict:
    row = (
        await db.execute(
            select(Invoice, Client, Project.project_code, Project.name)
            .join(Client, Client.id == Invoice.client_id)
            .outerjoin(Project, Project.id == Invoice.project_id)
            .where(Invoice.id == invoice_id)
        )
    ).first()
    if row is None:
        raise FinanceError("Invoice not found", 404)
    invoice, client, project_code, project_name = row
    items = await _items_for(db, invoice.id)
    return _invoice_dict(invoice, items, client, project_code, project_name)


async def update_invoice(db: AsyncSession, invoice: Invoice, payload: InvoiceUpdate) -> dict:
    if invoice.status != InvoiceStatus.DRAFT:
        raise FinanceError("Only draft invoices can be edited")
    if payload.client_id is not None:
        await _validate_refs(db, payload.client_id, payload.project_id)
        invoice.client_id = payload.client_id
    if payload.project_id is not None:
        await _validate_refs(db, invoice.client_id, payload.project_id)
        invoice.project_id = payload.project_id
    if payload.invoice_date is not None:
        invoice.invoice_date = payload.invoice_date
    if payload.due_date is not None:
        invoice.due_date = payload.due_date
    if payload.tax_percent is not None:
        invoice.tax_percent = _q(payload.tax_percent)
    if payload.notes is not None:
        invoice.notes = payload.notes
    if payload.terms is not None:
        invoice.terms = payload.terms
    if payload.items is not None:
        existing = await _items_for(db, invoice.id)
        for item in existing:
            await db.delete(item)
        items = await _make_items(invoice, payload.items)
        db.add_all(items)
    items = await _items_for(db, invoice.id)
    invoice.subtotal, invoice.tax_amount, invoice.total = _totals(
        items, invoice.tax_percent or Decimal("0")
    )
    await db.commit()
    await db.refresh(invoice)
    client = await db.get(Client, invoice.client_id)
    project = await db.get(Project, invoice.project_id) if invoice.project_id else None
    items = await _items_for(db, invoice.id)
    return _invoice_dict(
        invoice,
        items,
        client,
        project.project_code if project else None,
        project.name if project else None,
    )


async def send_invoice(db: AsyncSession, invoice: Invoice) -> dict:
    if invoice.status == InvoiceStatus.CANCELLED:
        raise FinanceError("A cancelled invoice cannot be sent")
    if invoice.sent_at is not None:
        raise FinanceError("Invoice has already been sent")
    # Client-facing safeguard: near-empty descriptions must not go out on an
    # invoice (e.g. a stray "wd" placeholder). Block with a clear error.
    bad = [
        (idx + 1, item.description)
        for idx, item in enumerate(await _items_for(db, invoice.id))
        if len((item.description or "").strip()) < 3
    ]
    if bad:
        detail = ", ".join(f"line {n} ({desc!r})" for n, desc in bad[:5])
        raise FinanceError(
            f"Cannot send: line item description too short — {detail}. "
            "Give each fee head a clear client-facing description."
        )
    invoice.sent_at = utc_now()
    invoice.status = InvoiceStatus.SENT
    await db.commit()
    await db.refresh(invoice)
    return await get_invoice(db, invoice.id)


async def record_payment(
    db: AsyncSession, invoice: Invoice, amount: Decimal, method: str, payment_date: date | None
) -> dict:
    if invoice.status == InvoiceStatus.CANCELLED:
        raise FinanceError("Cannot record payment on a cancelled invoice")
    try:
        payment_method = PaymentMethod(method)
    except ValueError as exc:
        raise FinanceError("Invalid payment method") from exc
    if invoice.paid_amount + amount > invoice.total + _PENNY:
        raise FinanceError("Payment exceeds the outstanding balance")
    invoice.paid_amount = _q(invoice.paid_amount + amount)
    invoice.payment_method = payment_method
    invoice.payment_date = payment_date or _today()
    if invoice.sent_at is None:
        invoice.sent_at = utc_now()
    invoice.status = (
        InvoiceStatus.PAID if invoice.paid_amount >= invoice.total else InvoiceStatus.PARTIAL
    )
    await db.commit()
    await db.refresh(invoice)
    return await get_invoice(db, invoice.id)


def _pct(value: Decimal) -> str:
    """Trim trailing zeros: 9.00 -> '9', 18.50 -> '18.5'."""
    return f"{value.normalize():f}"


def _tax_breakup(
    studio_gstin: str | None,
    client_gstin: str | None,
    tax_percent: Decimal,
    tax_amount: Decimal,
) -> list[tuple[str, Decimal]]:
    """GST lines for the invoice PDF.

    Intra-state (both GSTINs share the first-2-digit state code): CGST + SGST
    at half the rate each. Inter-state: one IGST line at the full rate.
    When either side lacks a GSTIN the place of supply can't be determined —
    fall back to a single combined line and log the data gap.
    """
    if tax_amount <= 0:
        return []
    studio_code = (studio_gstin or "").strip()[:2]
    client_code = (client_gstin or "").strip()[:2]
    valid = lambda c: len(c) == 2 and c.isdigit()  # noqa: E731
    if valid(studio_code) and valid(client_code):
        if studio_code == client_code:
            cgst = _q(tax_amount / 2)
            sgst = _q(tax_amount - cgst)  # absorb rounding penny so halves always sum exactly
            half_rate = _q(tax_percent / 2)
            return [
                (f"CGST ({_pct(half_rate)}%)", cgst),
                (f"SGST ({_pct(half_rate)}%)", sgst),
            ]
        return [(f"IGST ({_pct(_q(tax_percent))}%)", _q(tax_amount))]
    if tax_amount > 0:
        logger.warning(
            "Invoice tax rendered as a single GST line - cannot determine place of supply "
            "(studio GSTIN=%r, client GSTIN=%r). Add GSTINs for a correct CGST/SGST split.",
            studio_gstin,
            client_gstin,
        )
    return [(f"GST ({_pct(_q(tax_percent))}%)", _q(tax_amount))]


_PAYMENT_SETTING_KEYS = ("bank_name", "account_name", "account_number", "ifsc_code", "upi_id")


async def build_invoice_pdf(db: AsyncSession, data: dict, studio_info: dict | None = None) -> bytes:
    if studio_info is None:
        studio_info = await get_studio_info(db)
    tax_lines = _tax_breakup(
        studio_info.get("gstin"),
        data.get("client_gstin"),
        data["tax_percent"],
        data["tax_amount"],
    )
    payment_details = {k: studio_info[k] for k in _PAYMENT_SETTING_KEYS if studio_info.get(k)}
    # Per-invoice terms win; otherwise fall back to the studio-wide default.
    terms = data.get("terms") or studio_info.get("default_terms")
    return invoice_pdf(
        invoice_number=data["invoice_number"],
        client_name=data["client_name"] or f"Client #{data['client_id']}",
        client_address=data.get("client_address"),
        client_gstin=data.get("client_gstin"),
        project_code=data.get("project_code"),
        project_name=data.get("project_name"),
        invoice_date=data["invoice_date"],
        due_date=data["due_date"],
        status=data["status"],
        items=data["items"],
        subtotal=data["subtotal"],
        tax_percent=data["tax_percent"],
        tax_amount=data["tax_amount"],
        total=data["total"],
        paid_amount=data["paid_amount"],
        notes=data.get("notes"),
        terms=terms,
        studio_info=studio_info,
        tax_lines=tax_lines or None,
        payment_details=payment_details or None,
    )


async def _expense_dict(
    db: AsyncSession, expense: Expense, projects: dict[int, "Project"] | None = None
) -> dict:
    if projects is not None:
        project = projects.get(expense.project_id) if expense.project_id else None
    else:
        project = await db.get(Project, expense.project_id) if expense.project_id else None
    return {
        "id": expense.id,
        "category": expense.category,
        "description": expense.description,
        "amount": expense.amount,
        "expense_date": expense.expense_date,
        "project_id": expense.project_id,
        "project_code": project.project_code if project else None,
        "paid_by": expense.paid_by,
        "receipt_path": expense.receipt_path,
        "status": expense.status.value,
        "approved_by": expense.approved_by,
        "approved_at": expense.approved_at,
    }


async def list_expenses(
    db: AsyncSession,
    category: str | None = None,
    project_id: int | None = None,
    status_: str | None = None,
    month: int | None = None,
    year: int | None = None,
    paid_by: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = select(Expense).order_by(Expense.expense_date.desc().nullslast(), Expense.id.desc())
    if paid_by is not None:
        stmt = stmt.where(Expense.paid_by == paid_by)
    if category:
        stmt = stmt.where(Expense.category == category)
    if project_id is not None:
        stmt = stmt.where(Expense.project_id == project_id)
    if status_:
        stmt = stmt.where(Expense.status == ExpenseStatus(status_))
    if month is not None and year is not None:
        start = date(year, month, 1)
        end = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
        stmt = stmt.where(Expense.expense_date >= start, Expense.expense_date < end)
    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Apply pagination
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    # Batch-fetch all referenced projects (eliminates N+1)
    project_ids = {e.project_id for e in rows if e.project_id}
    projects_map: dict[int, Project] = {}
    if project_ids:
        proj_rows = (
            (await db.execute(select(Project).where(Project.id.in_(project_ids)))).scalars().all()
        )
        projects_map = {p.id: p for p in proj_rows}
    items = [await _expense_dict(db, expense, projects_map) for expense in rows]
    return items, total


async def create_expense(
    db: AsyncSession,
    payload: ExpenseCreate,
    receipt_content: bytes | None = None,
    receipt_suffix: str = "",
) -> dict:
    if payload.project_id is not None:
        project = await db.get(Project, payload.project_id)
        if project is None:
            raise FinanceError("Project not found", 404)
    receipt_path = None
    if receipt_content is not None:
        from app.core.storage import get_storage

        filename = f"exp_{payload.expense_date or _today()}_{len(receipt_content)}{receipt_suffix}"
        storage_path = f"expenses/{filename}"
        storage = get_storage()
        await storage.upload(storage_path, receipt_content)
        receipt_path = storage_path
    expense = Expense(
        category=payload.category,
        description=payload.description,
        amount=_q(payload.amount),
        expense_date=payload.expense_date or _today(),
        project_id=payload.project_id,
        paid_by=payload.paid_by,
        receipt_path=receipt_path,
        status=ExpenseStatus.PENDING,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return await _expense_dict(db, expense)


async def decide_expense(db: AsyncSession, expense: Expense, approve: bool, admin: User) -> dict:
    target = ExpenseStatus.APPROVED if approve else ExpenseStatus.REJECTED
    from app.utils.state_machines import assert_transition

    assert_transition(expense.status, target, "expense")
    expense.status = target
    expense.approved_by = admin.id
    expense.approved_at = utc_now()
    await db.commit()
    await db.refresh(expense)
    return await _expense_dict(db, expense)


def _period_bounds(period: str) -> tuple[date, date]:
    today = _today()
    if period == "month":
        start = date(today.year, today.month, 1)
        end = (
            date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
        )
    elif period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, q_start_month, 1)
        end_month = q_start_month + 3
        end = date(today.year + (end_month - 1) // 12, ((end_month - 1) % 12) + 1, 1)
    elif period == "year":
        start = date(today.year, 1, 1)
        end = date(today.year + 1, 1, 1)
    else:
        start = date(1970, 1, 1)
        end = date(9999, 12, 31)
    return start, end


def _previous_bounds(period: str) -> tuple[date, date] | None:
    if period == "all":
        return None
    today = _today()
    if period == "month":
        cur_start = date(today.year, today.month, 1)
        prev_month_end = cur_start - timedelta(days=1)
        return date(prev_month_end.year, prev_month_end.month, 1), cur_start
    if period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        cur_start = date(today.year, q_start_month, 1)
        prev_start_month = q_start_month - 3
        if prev_start_month < 1:
            prev_start_month += 12
            prev_start = date(today.year - 1, prev_start_month, 1)
        else:
            prev_start = date(today.year, prev_start_month, 1)
        return prev_start, cur_start
    return date(today.year - 1, 1, 1), date(today.year, 1, 1)


async def _overview_metrics(db: AsyncSession, start: date, end: date) -> dict:
    invoiced = Decimal("0")
    received = Decimal("0")
    outstanding = Decimal("0")
    invoice_count = 0
    paid_count = 0
    overdue_count = 0

    stmt = (
        select(Invoice)
        .where(Invoice.invoice_date >= start, Invoice.invoice_date < end)
        .where(Invoice.status != InvoiceStatus.CANCELLED)
    )
    invoices = (await db.execute(stmt)).scalars().all()
    today = _today()
    for invoice in invoices:
        invoice_count += 1
        invoiced += invoice.total
        received += invoice.paid_amount
        outstanding += invoice.total - invoice.paid_amount
        effective = _status_for(invoice, today)
        if effective == InvoiceStatus.PAID:
            paid_count += 1
        if effective == InvoiceStatus.OVERDUE:
            overdue_count += 1

    expense_stmt = select(Expense).where(
        Expense.status == ExpenseStatus.APPROVED,
        Expense.expense_date >= start,
        Expense.expense_date < end,
    )
    expenses = (await db.execute(expense_stmt)).scalars().all()
    expense_total = sum((expense.amount for expense in expenses), Decimal("0"))
    expense_count = len(expenses)

    return {
        "invoiced": _q(invoiced),
        "received": _q(received),
        "outstanding": _q(outstanding),
        "expenses": _q(expense_total),
        "profit": _q(received - expense_total),
        "invoice_count": invoice_count,
        "paid_count": paid_count,
        "overdue_count": overdue_count,
        "expense_count": expense_count,
    }


async def finance_overview(db: AsyncSession, period: str, compare: bool = False) -> dict:
    start, end = _period_bounds(period)
    metrics = await _overview_metrics(db, start, end)
    result = {
        "period": period,
        "from": start,
        "to": end,
        **metrics,
    }
    if compare:
        previous = _previous_bounds(period)
        result["previous"] = await _overview_metrics(db, *previous) if previous else None
    return result
