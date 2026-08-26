"""Audit logging service.

Records audit trails for all write operations across the application.

Every entry captures *who / what / when* plus, when available, the
caller's IP and the request correlation ID. The correlation fields are
auto-filled from the ambient request context (see
``app.core.request_context``); callers may still override them
explicitly.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_context import current_request_context
from app.modules.audit.models import AuditLog
from app.modules.identity.models import User


async def log_audit(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str,
    *,
    entity_id: str | None = None,
    details: dict | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist an audit record for a state-changing operation.

    ``request_id`` / ``ip_address`` / ``user_agent`` default to the
    values captured by the request-context middleware; pass them
    explicitly only for out-of-band operations (e.g. scheduled jobs).
    """
    ambient = current_request_context()
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            request_id=request_id if request_id is not None else ambient["request_id"],
            ip_address=ip_address if ip_address is not None else ambient["ip_address"],
            user_agent=user_agent if user_agent is not None else ambient["user_agent"],
        )
    )
