"""Audit log viewing and export routes.

Endpoints: /audit-logs — list, filter, and CSV/XLSX-export audit trail. Admin roles only.
"""

import csv
import io
from collections import Counter
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: int | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    stmt = (
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
    )
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if from_date:
        stmt = stmt.where(AuditLog.created_at >= from_date)
    if to_date:
        stmt = stmt.where(AuditLog.created_at <= to_date)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user_name,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at,
        }
        for log, user_name in rows
    ]


@router.get("/count")
async def audit_log_count(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str | None = None,
) -> dict:
    stmt = select(func.count(AuditLog.id))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    total = (await db.execute(stmt)).scalar() or 0
    return {"total": total}


def _build_audit_xlsx(rows: list, action_counts: Counter, entity_counts: Counter) -> bytes:
    from app.utils.xlsx import write_xlsx

    num_cols = 5
    extra_before: list[list[tuple[str, str | None]]] = [
        [("Audit Log Export", "title")] + [("", None)] * (num_cols - 1),
        [(f"Total Entries: {len(rows)}", "subtitle")] + [("", None)] * (num_cols - 1),
        [("", None)] * num_cols,
        [("Activity Summary", "section")] + [("", None)] * (num_cols - 1),
    ]
    for action, count in action_counts.most_common(10):
        extra_before.append([(action, "summary_label"), (str(count), "summary_value")] + [("", None)] * (num_cols - 2))
    if entity_counts:
        extra_before.append([("", None)] * num_cols)
        extra_before.append([("Entity Breakdown", "section")] + [("", None)] * (num_cols - 1))
        for entity, count in entity_counts.most_common(10):
            extra_before.append([(entity, "summary_label"), (str(count), "summary_value")] + [("", None)] * (num_cols - 2))

    columns = ["ID", "User", "Action", "Entity Type", "Entity ID", "IP Address", "Timestamp"]
    col_styles = ["integer_border", "text_border", "text_border", "text_border", "text_border", "text_border", "text_border"]
    alt_col_styles = ["integer_alt", "text_alt", "text_alt", "text_alt", "text_alt", "text_alt", "text_alt"]

    detail_rows = [
        [
            log.id,
            user_name or "",
            log.action,
            log.entity_type,
            log.entity_id or "",
            log.ip_address or "",
            log.created_at.isoformat() if log.created_at else "",
        ]
        for log, user_name in rows
    ]

    return write_xlsx([{
        "name": "Audit Log",
        "columns": columns,
        "rows": detail_rows,
        "col_styles": col_styles,
        "alt_col_styles": alt_col_styles,
        "freeze_row": len(extra_before) + 1,
        "extra_rows_before": extra_before,
    }])


@router.get("/export")
async def export_audit_logs(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
) -> Response:
    stmt = (
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(5000)
    )
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if from_date:
        stmt = stmt.where(AuditLog.created_at >= from_date)
    if to_date:
        stmt = stmt.where(AuditLog.created_at <= to_date)
    rows = (await db.execute(stmt)).all()

    action_counts = Counter(log.action for log, _ in rows)
    entity_counts = Counter(log.entity_type for log, _ in rows)

    if format == "xlsx":
        content = _build_audit_xlsx(rows, action_counts, entity_counts)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="audit_logs.xlsx"'},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Audit Log Export"])
    writer.writerow([f"Total Entries: {len(rows)}"])
    writer.writerow([])
    writer.writerow(["Action Breakdown"])
    for action, count in action_counts.most_common():
        writer.writerow([action, count])
    if entity_counts:
        writer.writerow([])
        writer.writerow(["Entity Breakdown"])
        for entity, count in entity_counts.most_common():
            writer.writerow([entity, count])
    writer.writerow([])
    writer.writerow([])
    writer.writerow(
        ["ID", "User", "Action", "Entity Type", "Entity ID", "IP Address", "Timestamp"]
    )
    for log, user_name in rows:
        writer.writerow(
            [
                log.id,
                user_name or "",
                log.action,
                log.entity_type,
                log.entity_id or "",
                log.ip_address or "",
                log.created_at.isoformat() if log.created_at else "",
            ]
        )
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
