# ADR-0001: Global exception handler with correlation-ID error envelope

- Date: 2026-08-24
- Status: Accepted
- Risk: LOW

## Context

Before this change, an unhandled exception in any route produced
Starlette's default plain-text `Internal Server Error` response. There was
no way for a client or support engineer to correlate a failed request with
the server-side log entry, and there was no guarantee that future code
would not leak internals through ad-hoc error responses.

## Decision

Register a catch-all `Exception` handler in `app/main.py` that:

1. logs the real exception (with stack trace) to the structured JSON log,
   tagged with the request's `request_id`;
2. returns a generic JSON envelope `{detail, request_id}` with status 500;
3. echoes the correlation ID in the `X-Request-ID` response header.

Specific handlers (`HTTPException`, validation, `RateLimitExceeded`) are
unaffected — this only catches what nothing else handled.

## Alternatives considered

- *Middleware-level try/except around `call_next`*: rejected because it
  duplicates Starlette's `ServerErrorMiddleware` semantics and is easy to
  bypass when new middleware is inserted.
- *Returning `null` detail / empty body*: rejected; a stable machine-readable
  shape plus a correlation ID is more useful to both SPA and support.

## Consequences

Error responses gained one additive field (`request_id`). No existing field
changed or was removed. Stack traces never leave the process.
