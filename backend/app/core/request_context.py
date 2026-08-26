"""Ambient per-request context: correlation ID, client IP, user agent.

ContextVars give each request an isolated view — Starlette executes every
request in its own asyncio task with a copied context, so concurrent
requests can never see or overwrite each other's values.

The audit service reads this context so state-changing operations record
*who / what / when / from_ip / correlation_id* without every call site
having to pass them explicitly (explicit arguments still win).
"""

from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip", default=None)
user_agent_ctx: ContextVar[str | None] = ContextVar("user_agent", default=None)

# Set by the reverse proxy / load balancer in production (Render, nginx).
FORWARDED_FOR_HEADER = "x-forwarded-for"
USER_AGENT_HEADER = "user-agent"


def capture_request_context(
    request_id: str | None,
    client_ip: str | None,
    user_agent: str | None,
) -> None:
    """Store the current request's correlation data for later consumers."""
    request_id_ctx.set(request_id)
    client_ip_ctx.set(client_ip)
    user_agent_ctx.set(user_agent)


def current_request_context() -> dict[str, Any]:
    """Return ``{request_id, ip_address, user_agent}`` for this request."""
    return {
        "request_id": request_id_ctx.get(),
        "ip_address": client_ip_ctx.get(),
        "user_agent": user_agent_ctx.get(),
    }
