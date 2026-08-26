"""Payroll run and payslip routes.

Endpoints: /payroll — run payroll, view history, generate payslips.
Payroll is financial data: executive band only (L0/L1) via
require_financial_access — see docs/architecture/financial_access_policy.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_financial_access
from app.db.session import get_db
from app.models import User
from app.modules.payroll.schemas import PayrollRunOut
from app.modules.payroll import service as payroll_service
from app.utils.errors import PayrollError
from app.utils.shared import domain_error, now_local

router = APIRouter(prefix="/payroll", tags=["payroll"])


class ProcessPayrollIn(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2100)


@router.get("", response_model=PayrollRunOut)
async def get_payroll(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: int = Query(default_factory=lambda: now_local().date().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: now_local().date().year, ge=2020, le=2100),
) -> dict:
    return await payroll_service.get_run(db, month, year)


@router.post("/process", response_model=PayrollRunOut)
async def process_payroll(
    payload: ProcessPayrollIn,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        return await payroll_service.process_run(db, payload.month, payload.year, current_user)
    except PayrollError as exc:
        raise domain_error(exc) from exc


@router.get("/{month}/{year}/payslips/{user_id}")
async def download_payslip(
    month: int,
    year: int,
    user_id: int,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        content, filename = await payroll_service.get_payslip(db, month, year, user_id)
    except PayrollError as exc:
        raise domain_error(exc) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
