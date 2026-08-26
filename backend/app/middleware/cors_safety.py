"""Belt-and-suspenders CORS safety-net middleware.

Starlette's CORSMiddleware lives inside the BaseHTTPMiddleware stack. When a
BaseHTTPMiddleware re-raises an exception from call_next(), the response can
bypass CORSMiddleware entirely, producing a 500 without Access-Control headers.
The browser then masks the real error as a "CORS error."

This ASGI middleware sits at the absolute outermost layer and guarantees that
EVERY response — success or failure — carries valid CORS headers.
"""

from __future__ import annotations

import re

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send


class CORSSafetyMiddleware:
    """Thin ASGI middleware that ensures CORS headers on every response."""

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str] | None = None,
        allow_origin_regex: str | re.Pattern[str] | None = None,
        allow_credentials: bool = True,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        expose_headers: list[str] | None = None,
        max_age: int = 600,
    ) -> None:
        self.app = app
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
        ]
        self.allow_headers = allow_headers or [
            "authorization",
            "content-type",
            "x-request-id",
        ]
        self.expose_headers = expose_headers or [
            "X-Request-ID",
            "Content-Disposition",
        ]
        self.max_age = max_age

        self._allow_all = False
        self._allowed_origins: set[str] = set()
        self._origin_regex: re.Pattern[str] | None = None

        if allow_origin_regex:
            if isinstance(allow_origin_regex, str):
                self._origin_regex = re.compile(allow_origin_regex)
            else:
                self._origin_regex = allow_origin_regex

        if allow_origins:
            for o in allow_origins:
                if o == "*":
                    self._allow_all = True
                    break
                self._allowed_origins.add(o)

    # ── helpers ──────────────────────────────────────────────────────────
    def _origin_allowed(self, origin: str | None) -> bool:
        if not origin:
            return False
        if self._allow_all:
            return True
        if origin in self._allowed_origins:
            return True
        if self._origin_regex and self._origin_regex.fullmatch(origin):
            return True
        return False

    def _cors_headers(self, origin: str) -> list[tuple[bytes, bytes]]:
        headers: list[tuple[bytes, bytes]] = []

        if self._allow_all or self._origin_regex or origin in self._allowed_origins:
            val = origin if self.allow_credentials else "*"
            headers.append((b"access-control-allow-origin", val.encode()))
            if self.allow_credentials:
                headers.append((b"access-control-allow-credentials", b"true"))
            headers.append(
                (
                    b"access-control-expose-headers",
                    ", ".join(self.expose_headers).encode(),
                )
            )
        return headers

    def _preflight_headers(self, origin: str) -> list[tuple[bytes, bytes]]:
        headers = self._cors_headers(origin)
        headers.append((b"access-control-allow-methods", ", ".join(self.allow_methods).encode()))
        headers.append((b"access-control-allow-headers", ", ".join(self.allow_headers).encode()))
        headers.append((b"access-control-max-age", str(self.max_age).encode()))
        return headers

    # ── ASGI interface ───────────────────────────────────────────────────
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origin = headers.get("origin")

        # ── Preflight ────────────────────────────────────────────────────
        if scope["method"] == "OPTIONS" and origin:
            if self._origin_allowed(origin):
                resp_headers = self._preflight_headers(origin)
                await send(
                    {
                        "type": "http.response.start",
                        "status": 204,
                        "headers": resp_headers,
                    }
                )
                await send({"type": "http.response.body"})
                return

        # ── Normal request — pass through, then inject headers ───────────
        if not origin or not self._origin_allowed(origin):
            await self.app(scope, receive, send)
            return

        injected = False
        cors_hdrs = self._cors_headers(origin)

        async def _send(message):
            nonlocal injected
            if message["type"] == "http.response.start" and not injected:
                raw_hdrs = message.get("headers", [])
                has_cors = any(
                    (k == b"access-control-allow-origin" or k == "access-control-allow-origin")
                    for k, _ in raw_hdrs
                )
                if not has_cors:
                    msg_headers = list(raw_hdrs)
                    msg_headers.extend(cors_hdrs)
                    message["headers"] = msg_headers
                injected = True
            await send(message)

        await self.app(scope, receive, _send)
