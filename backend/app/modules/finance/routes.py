"""Finance routes: /finance summary, /invoices, /expenses.

All financial data is restricted to the executive band (L0 CEO / L1
Director) via require_financial_access — see
docs/architecture/financial_access_policy.md.
"""

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_financial_access
from app.core.config import settings as _cfg
from app.core.storage import get_storage
from app.db.session import get_db
from app.models import Expense, Invoice, User
from app.modules.finance.schemas import (
    ExpenseCreate,
    ExpenseDecisionIn,
    ExpenseOut,
    InvoiceCreate,
    InvoiceOut,
    InvoicePaymentIn,
    InvoiceUpdate,
)
from app.modules.finance import service as finance_service
from app.core.schemas import PaginatedResponse
from app.modules.audit.service import log_audit
from app.core.email import send_invoice_email
from app.utils.errors import FinanceError
from app.utils.shared import domain_error, get_or_404
from app.utils.upload import ALLOWED_RECEIPT_EXTENSIONS, validate_upload

finance_router = APIRouter(prefix="/finance", tags=["finance"])
invoices_router = APIRouter(prefix="/invoices", tags=["invoices"])
expenses_router = APIRouter(prefix="/expenses", tags=["expenses"])

logger = logging.getLogger(__name__)


@finance_router.get("/overview")
async def finance_overview(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: str = Query(default="month", pattern="^(month|quarter|year|all)$"),
    compare: bool = Query(default=False),
) -> dict:
    return await finance_service.finance_overview(db, period, compare=compare)


@finance_router.get("/my-expenses", response_model=PaginatedResponse[ExpenseOut])
async def list_my_expenses(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await finance_service.list_expenses(
        db,
        category,
        project_id,
        status_,
        month,
        year,
        paid_by=current_user.name,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@finance_router.post("/my-expenses", response_model=ExpenseOut, status_code=201)
async def create_my_expense(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: ExpenseCreate,
) -> dict:
    payload.paid_by = current_user.name
    return await finance_service.create_expense(db, payload)


@invoices_router.get("", response_model=PaginatedResponse[InvoiceOut])
async def list_invoices(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_: str | None = Query(default=None, alias="status"),
    client_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await finance_service.list_invoices(
        db, status_, client_id, search, page, page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@invoices_router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        result = await finance_service.create_invoice(db, payload)
    except FinanceError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "invoice", entity_id=str(result["id"]))
    await db.commit()
    return result


@invoices_router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        return await finance_service.get_invoice(db, invoice_id)
    except FinanceError as exc:
        raise domain_error(exc) from exc


@invoices_router.patch("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    invoice = await get_or_404(db, Invoice, invoice_id)
    try:
        result = await finance_service.update_invoice(db, invoice, payload)
    except FinanceError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "invoice", entity_id=str(invoice_id))
    await db.commit()
    return result


@invoices_router.post("/{invoice_id}/send", response_model=InvoiceOut)
async def send_invoice(
    invoice_id: int,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # Eager-load the client: the email below reads it after the service
    # commits, and a lazy load here would raise MissingGreenlet.
    result = (
        await db.execute(
            select(Invoice).options(selectinload(Invoice.client)).where(Invoice.id == invoice_id)
        )
    ).scalar_one_or_none()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    invoice = result
    try:
        result = await finance_service.send_invoice(db, invoice)
    except FinanceError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "send", "invoice", entity_id=str(invoice_id))
    await db.commit()
    if _cfg.email_enabled and invoice.client and invoice.client.email:
        await send_invoice_email(
            invoice.client.email,
            invoice.client.name,
            result.get("invoice_number", ""),
            str(result.get("total", "")),
            str(result.get("due_date", "")),
        )
    return result


@invoices_router.post("/{invoice_id}/payment", response_model=InvoiceOut)
async def record_payment(
    invoice_id: int,
    payload: InvoicePaymentIn,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    invoice = await get_or_404(db, Invoice, invoice_id)
    try:
        result = await finance_service.record_payment(
            db, invoice, payload.amount, payload.method, payload.payment_date
        )
    except FinanceError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "payment", "invoice", entity_id=str(invoice_id))
    await db.commit()
    return result


@invoices_router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        data = await finance_service.get_invoice(db, invoice_id)
    except FinanceError as exc:
        raise domain_error(exc) from exc
    content = await finance_service.build_invoice_pdf(db, data)
    filename = f"{data['invoice_number']}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@expenses_router.get("", response_model=PaginatedResponse[ExpenseOut])
async def list_expenses(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await finance_service.list_expenses(
        db, category, project_id, status_, month, year, page=page, page_size=page_size
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@expenses_router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Annotated[str, Form(min_length=1, max_length=80)],
    amount: Annotated[Decimal, Form(gt=0)],
    description: Annotated[str | None, Form()] = None,
    expense_date: Annotated[date | None, Form()] = None,
    project_id: Annotated[int | None, Form()] = None,
    paid_by: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> dict:
    receipt_content = None
    receipt_suffix = ""
    if file is not None:
        receipt_content = await file.read()
        receipt_suffix = validate_upload(
            file, receipt_content, allowed=ALLOWED_RECEIPT_EXTENSIONS, label="receipt"
        )
    payload = ExpenseCreate(
        category=category,
        description=description,
        amount=amount,
        expense_date=expense_date,
        project_id=project_id,
        paid_by=paid_by,
    )
    try:
        result = await finance_service.create_expense(db, payload, receipt_content, receipt_suffix)
    except FinanceError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "expense", entity_id=str(result["id"]))
    await db.commit()
    return result


@expenses_router.patch("/{expense_id}/approve", response_model=ExpenseOut)
async def decide_expense(
    expense_id: int,
    payload: ExpenseDecisionIn,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    expense = await get_or_404(db, Expense, expense_id)
    try:
        result = await finance_service.decide_expense(db, expense, payload.approve, current_user)
    except FinanceError as exc:
        raise domain_error(exc) from exc
    action = "approve" if payload.approve else "reject"
    await log_audit(db, current_user, action, "expense", entity_id=str(expense_id))
    await db.commit()
    return result


@expenses_router.get("/{expense_id}/receipt")
async def download_receipt(
    expense_id: int,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    expense = await get_or_404(db, Expense, expense_id)
    if not expense.receipt_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No receipt uploaded")
    storage = get_storage()
    try:
        content = await storage.download(expense.receipt_path)
    except Exception:
        logger.exception(
            "Receipt download failed for expense %s (path=%s)", expense_id, expense.receipt_path
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt file missing from storage"
        )
    filename = Path(expense.receipt_path).name
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
