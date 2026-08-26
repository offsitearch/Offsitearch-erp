"""Client/CRM service.

Client CRUD operations, search, and communication tracking.
"""

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, User
from app.modules.clients.models import Client, ClientCommunication
from app.modules.clients.schemas import ClientCreate, ClientUpdate, CommunicationIn
from app.utils.enums import ClientType
from app.utils.errors import ClientError

_ZERO = Decimal("0.00")

# Financial fields (see docs/architecture/financial_access_policy.md):
# omitted from responses and rejected on writes for callers without
# financial access. deal_stage/GST/PAN stay operational per policy Q2.
FINANCIAL_CLIENT_FIELDS = ("budget_range",)


def _client_dict(client: Client, include_financial: bool = True) -> dict:
    data = {
        "id": client.id,
        "name": client.name,
        "client_type": client.client_type.value,
        "company_name": client.company_name,
        "contact_person": client.contact_person,
        "phone": client.phone,
        "phone_secondary": client.phone_secondary,
        "email": client.email,
        "address": client.address,
        "gst_number": client.gst_number,
        "pan_number": client.pan_number,
        "source": client.source,
        "referred_by": client.referred_by,
        "budget_range": client.budget_range,
        "interest": client.interest,
        "notes": client.notes,
        "deal_stage": client.deal_stage.value,
        "next_follow_up_date": client.next_follow_up_date,
        "next_follow_up_action": client.next_follow_up_action,
        "is_active": client.is_active,
        "created_at": client.created_at,
    }
    if not include_financial:
        data.pop("budget_range", None)
    return data


async def list_clients(
    db: AsyncSession,
    search: str | None,
    client_type: str | None,
    page: int,
    page_size: int,
    include_financial: bool = True,
) -> tuple[list[dict], int]:
    base = (
        select(Client, func.count(Project.id))
        .outerjoin(Project, Project.client_id == Client.id)
        .where(Client.is_active.is_(True))
        .group_by(Client.id)
    )
    count_stmt = select(func.count(Client.id)).where(Client.is_active.is_(True))

    if search:
        like = f"%{search}%"
        cond = or_(
            Client.name.ilike(like),
            Client.company_name.ilike(like),
            Client.email.ilike(like),
            Client.contact_person.ilike(like),
        )
        base = base.where(cond)
        count_stmt = count_stmt.where(cond)
    if client_type:
        base = base.where(Client.client_type == ClientType(client_type))
        count_stmt = count_stmt.where(Client.client_type == ClientType(client_type))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(base.order_by(Client.name).offset((page - 1) * page_size).limit(page_size))
    ).all()
    items = [
        {
            "id": client.id,
            "name": client.name,
            "client_type": client.client_type.value,
            "company_name": client.company_name,
            "contact_person": client.contact_person,
            "phone": client.phone,
            "email": client.email,
            "source": client.source,
            "budget_range": client.budget_range if include_financial else None,
            "deal_stage": client.deal_stage.value,
            "next_follow_up_date": client.next_follow_up_date,
            "is_active": client.is_active,
            "project_count": count,
        }
        for client, count in rows
    ]
    return items, total


async def create_client(db: AsyncSession, payload: ClientCreate) -> Client:
    if payload.referred_by is not None:
        referrer = await db.get(Client, payload.referred_by)
        if referrer is None or not referrer.is_active:
            raise ClientError("Referred-by client not found", 404)
    data = payload.model_dump()
    if data["email"] is not None:
        data["email"] = data["email"].lower()
    client = Client(**data)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def get_client(db: AsyncSession, client_id: int) -> Client:
    client = await db.get(Client, client_id)
    if client is None or not client.is_active:
        raise ClientError("Client not found", 404)
    return client


async def update_client(db: AsyncSession, client: Client, payload: ClientUpdate) -> Client:
    data = payload.model_dump(exclude_unset=True)
    if "referred_by" in data and data["referred_by"] is not None:
        if data["referred_by"] == client.id:
            raise ClientError("A client cannot refer themselves", 400)
        referrer = await db.get(Client, data["referred_by"])
        if referrer is None or not referrer.is_active:
            raise ClientError("Referred-by client not found", 404)
    if "email" in data and data["email"] is not None:
        data["email"] = data["email"].lower()
    for field, value in data.items():
        if value is not None:
            setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    return client


async def soft_delete(db: AsyncSession, client: Client) -> None:
    client.is_active = False
    await db.commit()


async def get_profile(db: AsyncSession, client_id: int, include_financial: bool = True) -> dict:
    client = await get_client(db, client_id)
    referred_name = None
    if client.referred_by:
        referrer = await db.get(Client, client.referred_by)
        referred_name = referrer.name if referrer else None

    project_rows = (
        (
            await db.execute(
                select(Project)
                .where(Project.client_id == client_id, Project.is_active.is_(True))
                .order_by(Project.id.desc())
            )
        )
        .scalars()
        .all()
    )
    projects = [
        {
            "id": project.id,
            "project_code": project.project_code,
            "name": project.name,
            "project_type": project.project_type.value,
            "status": project.status.value,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "progress_pct": project.progress_pct,
            "budget": project.budget if include_financial else None,
            "studio_fee": project.studio_fee if include_financial else None,
        }
        for project in project_rows
    ]

    comm_rows = (
        await db.execute(
            select(ClientCommunication, User.name)
            .join(User, User.id == ClientCommunication.user_id)
            .where(ClientCommunication.client_id == client_id)
            .order_by(ClientCommunication.occurred_at.desc())
        )
    ).all()
    communications = [
        {
            "id": comm.id,
            "client_id": comm.client_id,
            "user_id": comm.user_id,
            "user_name": user_name,
            "type": comm.type.value,
            "subject": comm.subject,
            "notes": comm.notes,
            "occurred_at": comm.occurred_at,
        }
        for comm, user_name in comm_rows
    ]

    total_budget = sum((project.budget or _ZERO) for project in project_rows)
    total_studio_fee = sum((project.studio_fee or _ZERO) for project in project_rows)

    return {
        "client": _client_dict(client, include_financial) | {"referred_name": referred_name},
        "projects": projects,
        "communications": communications,
        "financial_summary": {
            "total_projects": len(projects),
            "total_budget": total_budget if include_financial else None,
            "total_studio_fee": total_studio_fee if include_financial else None,
            "invoiced": _ZERO if include_financial else None,
            "received": _ZERO if include_financial else None,
            "outstanding": _ZERO if include_financial else None,
        },
    }


async def list_communications(db: AsyncSession, client_id: int) -> list[dict]:
    await get_client(db, client_id)
    rows = (
        await db.execute(
            select(ClientCommunication, User.name)
            .join(User, User.id == ClientCommunication.user_id)
            .where(ClientCommunication.client_id == client_id)
            .order_by(ClientCommunication.occurred_at.desc())
        )
    ).all()
    return [
        {
            "id": comm.id,
            "client_id": comm.client_id,
            "user_id": comm.user_id,
            "user_name": user_name,
            "type": comm.type.value,
            "subject": comm.subject,
            "notes": comm.notes,
            "occurred_at": comm.occurred_at,
        }
        for comm, user_name in rows
    ]


async def add_communication(
    db: AsyncSession, client_id: int, user: User, payload: CommunicationIn
) -> dict:
    await get_client(db, client_id)
    from app.utils.shared import utc_now

    comm = ClientCommunication(
        client_id=client_id,
        user_id=user.id,
        type=payload.type,
        subject=payload.subject,
        notes=payload.notes,
        occurred_at=payload.occurred_at or utc_now(),
    )
    db.add(comm)
    await db.commit()
    await db.refresh(comm)
    return {
        "id": comm.id,
        "client_id": comm.client_id,
        "user_id": comm.user_id,
        "user_name": user.name,
        "type": comm.type.value,
        "subject": comm.subject,
        "notes": comm.notes,
        "occurred_at": comm.occurred_at,
    }
