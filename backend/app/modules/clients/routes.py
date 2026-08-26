"""Client management routes.

Endpoints: /clients — CRUD, communication history, profile. Financial
fields (budget_range, deal values, financial summaries) follow the
financial access policy: visible/writable by L0/L1 only — see
docs/architecture/financial_access_policy.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.clients.models import Client
from app.modules.clients.schemas import (
    ClientCreate,
    ClientOut,
    ClientPage,
    ClientProfileOut,
    ClientUpdate,
    CommunicationIn,
    CommunicationOut,
)
from app.modules.clients import service as client_service
from app.modules.audit.service import log_audit
from app.utils.errors import ClientError
from app.utils.shared import domain_error, get_or_404, has_financial_access

router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)


def _reject_financial_writes(payload, current_user: User) -> None:
    """budget_range is a deal value: only L0/L1 may set it."""
    if has_financial_access(current_user):
        return
    if "budget_range" in payload.model_fields_set and payload.budget_range is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Financial fields require executive access",
        )


@router.get("", response_model=ClientPage, response_model_exclude_none=True)
async def list_clients(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=100),
    client_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ClientPage:
    items, total = await client_service.list_clients(
        db,
        search,
        client_type,
        page,
        page_size,
        include_financial=has_financial_access(current_user),
    )
    return ClientPage(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=ClientOut,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
)
async def create_client(
    payload: ClientCreate,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    _reject_financial_writes(payload, current_user)
    try:
        client = await client_service.create_client(db, payload)
    except ClientError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "client", entity_id=str(client.id))
    await db.commit()
    return client_service._client_dict(client, has_financial_access(current_user))


@router.get("/{client_id}", response_model=ClientProfileOut, response_model_exclude_none=True)
async def get_client_profile(
    client_id: int,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        return await client_service.get_profile(
            db, client_id, include_financial=has_financial_access(current_user)
        )
    except ClientError as exc:
        raise domain_error(exc) from exc


@router.patch("/{client_id}", response_model=ClientOut, response_model_exclude_none=True)
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    client = await get_or_404(db, Client, client_id)
    if not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    _reject_financial_writes(payload, current_user)
    try:
        updated = await client_service.update_client(db, client, payload)
    except ClientError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "client", entity_id=str(client_id))
    await db.commit()
    return client_service._client_dict(updated, has_financial_access(current_user))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    client = await get_or_404(db, Client, client_id)
    if not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    await client_service.soft_delete(db, client)
    await log_audit(db, current_user, "delete", "client", entity_id=str(client_id))
    await db.commit()


@router.get("/{client_id}/communications", response_model=list[CommunicationOut])
async def list_communications(
    client_id: int,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    try:
        return await client_service.list_communications(db, client_id)
    except ClientError as exc:
        raise domain_error(exc) from exc


@router.post(
    "/{client_id}/communications",
    response_model=CommunicationOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_communication(
    client_id: int,
    payload: CommunicationIn,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        result = await client_service.add_communication(db, client_id, current_user, payload)
    except ClientError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "client_communication", entity_id=str(client_id))
    await db.commit()
    return result
