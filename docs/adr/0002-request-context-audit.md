# ADR-0002: Ambient request context for audit-trail completeness

- Date: 2026-08-24
- Status: Accepted
- Risk: LOW

## Context

The audit module already stored `request_id`, `ip_address` and
`user_agent` columns, and `log_audit()` accepted them as optional
parameters — but **no caller ever passed them**. Audit entries therefore
recorded *who / what / when* but never *from where*, weakening both the
security posture (incident forensics) and any compliance requirement for
an audit trail.

Threading `Request` through every service signature would touch every
module and couple services to the HTTP layer.

## Decision

Introduce `app/core/request_context.py`: three `ContextVar`s
(`request_id`, `client_ip`, `user_agent`) populated once by the existing
request-logging middleware. `log_audit()` now auto-fills any correlation
argument that was not passed explicitly.

Client IP resolution prefers the first hop of `X-Forwarded-For`
(production sits behind Render/nginx) and falls back to the direct socket
peer.

## Alternatives considered

- *Explicit parameter threading*: most "pure", but requires changing every
  route/service signature across 20 modules — a large, regression-prone
  diff inappropriate at a pre-testing gate.
- *Middleware writing audit rows itself*: rejected; middleware cannot know
  domain semantics of "state-changing".

## Consequences

Safe under concurrency: Starlette executes each request in its own task
with a copied context, so values cannot bleed between requests.
Background jobs (no ambient request) continue to work — fields stay
`None` unless explicitly provided. No API contract changed.
