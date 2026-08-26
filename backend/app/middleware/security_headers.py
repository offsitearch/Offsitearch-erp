"""Security headers middleware for FastAPI.

Adds industry-standard security headers to all responses,
replacing the nginx-only headers that don't apply on Render/Vercel.
"""

import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Prevent embedding
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]

        if is_production:
            # HSTS — only in production (HTTPS)
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

            # Content Security Policy — restrictive default
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

            # Permissions policy — disable unnecessary browser features
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), payment=()"
            )

        return response
