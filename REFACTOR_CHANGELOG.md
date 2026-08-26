# Refactor Changelog — Pre-Testing Overhaul Pass

Date: 2026-08-24 · Branch: `main` · Scope: last optimization pass before the
testing phase. Guiding rule applied throughout: *when in doubt, do less* —
every change below is behavior-preserving unless explicitly noted.

**Regression proof:** the full backend suite was run against a throwaway
Postgres 16 container with this pass's `app/` changes stashed (baseline) and
restored: the pass/fail sets are **identical** — 210 passed / 23 failed in
both runs. The 23 failures are pre-existing stale tests (see
"Flagged for human review"). Frontend `tsc --noEmit && vite build`,
backend `ruff check`, and all three import-linter contracts are green.

---

## Legend

Risk: LOW = cosmetic/internal only · MEDIUM = touches runtime behavior,
covered by targeted verification · HIGH = none in this pass (nothing
changes API contracts, auth behavior, or financial logic).
Revert: `git revert <commit>` unless noted.

---

## 1. Dead code & hygiene (Phase 1)

| File | Change | Why | Risk | Revert |
|---|---|---|---|---|
| `backend/.importlinter` | Removed phantom `app.modules.vendors.models`; added root `exclude_type_checking_imports = true` | Config referenced a deleted module → linter always errored, masking real results; TYPE_CHECKING-only imports created no runtime coupling | LOW | restore line |
| `backend/tests/__pycache__/` | Deleted stale bytecode incl. orphaned `test_vendors.*.pyc` | Untracked artifact of removed tests | LOW | n/a |
| 14 × unused imports/vars across `app/core/email.py`, `app/modules/{attendance,clients,employees,holidays,leave,payroll,settings}`, `app/seeds/demo.py`, `tests/test_walkthrough.py` | ruff F401/F811/F841/E741 fixes; `l`→`entry`, unused assignments → `_`-prefixed (all calls kept) | Zero-unused-code gate; mechanical, autofix-verified | LOW | `git checkout` |
| `backend/app/main.py` | Moved `RateLimitTrackerMiddleware` import to top (E402) | Style; import is circularity-free (verified) | LOW | move back |
| `DEPRECATION_LOG.md` (new) | Vendors tables, rate-limit triplication, idempotency keys, circuit breakers documented as kept/deferred with removal conditions | Safe-removal protocol: never delete silently, never touch migrations | LOW | delete file |

## 2. Dependencies (Phase 1)

| File | Change | Why | Risk | Revert |
|---|---|---|---|---|
| `backend/requirements.txt` | `python-multipart 0.0.20→0.0.31`, `PyJWT 2.10→2.13.*`, `aiosmtplib >=3,<4 → >=5.1,<6`, `fastapi 0.115→0.120.*` + explicit `starlette==0.49.*` | CVE patches (PYSEC-2026-1852, -3036…3040, -120/-175…-179, -2338, -1941, -1942). Details + residual starlette-1.x CVEs: `docs/adr/0004-dependency-cve-patching.md` | MEDIUM | previous pins + reinstall |
| `frontend/package-lock.json` | No change needed — `npm audit`: **0 vulnerabilities** | Audit gate satisfied | — | — |

Verification: full pytest re-run post-upgrade shows identical result set;
`aiosmtplib.send` kwargs verified via signature introspection; app boots.

## 3. Error handling & security (Phase 3)

| File | Change | Why | Risk | Revert |
|---|---|---|---|---|
| `backend/app/main.py` | Catch-all `@app.exception_handler(Exception)` → generic `{detail, request_id}` JSON + `X-Request-ID` header; real traceback logged internally only. Proven via injected failing route (no internals in body). Also fixed `root()` return annotation | Never leak stack traces; correlation IDs on errors | LOW-MEDIUM | remove handler |
| `backend/app/core/config.py`, `backend/app/core/email.py` | New `SMTP_TIMEOUT_SECONDS=30` wired into `aiosmtplib.send`; hardcoded `https://studioerp.dev/login` → new `FRONTEND_URL` setting (same default value) | External calls need timeouts; kill magic URL | LOW | remove params |
| `.env.example` | Added `SMTP_TIMEOUT_SECONDS`, `EMAIL_ENABLED`, `EMAIL_FROM`, `FRONTEND_URL`, `STORAGE_TIMEOUT_SECONDS`. Fixed doc bug: example showed `SMTP_FROM`, which pydantic never read (real var is `EMAIL_FROM`) | Config discoverability; backward-compatible additions only | LOW | revert file |

## 4. Robustness / performance (Phases 3+6+7)

| File | Change | Why | Risk | Revert |
|---|---|---|---|---|
| `backend/app/core/storage.py` | Rewritten: Supabase sync calls + local disk I/O offloaded via `asyncio.to_thread`, bounded by new `STORAGE_TIMEOUT_SECONDS=30`. Legacy `exists()` semantics intentionally preserved (see ADR-0003). LocalStorage roundtrip unit-verified | Event-loop blocking + infinite-hang elimination | MEDIUM | ADR-0003 revert |
| `backend/app/core/request_context.py` (new), `backend/app/main.py` | ContextVar request context (id/IP/user-agent) captured in existing middleware; IP prefers first `X-Forwarded-For` hop behind trusted proxies | Audit trail needs *from_ip* + correlation ID (ADR-0002) | LOW | remove capture call |
| `backend/app/modules/audit/service.py` | `log_audit()` auto-fills `request_id/ip_address/user_agent` from ambient context when not passed explicitly (explicit args still win) | Fields existed but were never populated by any caller | LOW | revert file |
| `backend/app/main.py` | Lifespan teardown now `await engine.dispose()` after scheduler stop | Graceful shutdown releases pooled DB connections (gunicorn already drains SIGTERM) | LOW | remove line |
| `frontend/src/api/client.ts` | Default axios `timeout: 30s`; exports `UPLOAD_TIMEOUT_MS = 120s` | UI could wait forever | LOW-MEDIUM | remove timeout |
| `frontend/src/api/{finance,employees,siteVisits}.ts` | Upload calls use `UPLOAD_TIMEOUT_MS` | Receipts/documents/photos must survive slow links | LOW | remove param |
| `frontend/src/lib/errors.ts` | `ECONNABORTED` → friendly "request timed out" message | Timeout UX; additive branch only | LOW | revert |

## 5. Structural refactor (Phase 2)

| File | Change | Why | Risk | Revert |
|---|---|---|---|---|
| `backend/app/modules/orgstructure/service.py` (new) | Department/org-level business rules extracted verbatim from routes; `list_departments`/`list_org_levels` relocated here from `employees.service` (single consumer, correct domain) | Service-layer rule; logic was untestable without HTTP | LOW | ADR-0005 revert |
| `backend/app/modules/orgstructure/routes.py` | Now pure auth + delegation; same paths, verbs, status codes, error messages | Zero business logic in controllers | LOW | ADR-0005 revert |
| `backend/app/modules/employees/service.py` | Removed the two relocated read functions | DRY/domain ownership | LOW | restore functions |

## 6. Naming / frontend hygiene (Phase 4)

| File | Change | Why | Risk | Revert |
|---|---|---|---|---|
| `frontend/src/features/dashboard/DashboardPageNew.tsx` → `DashboardPage.tsx` (+ `App.tsx`, component name) | Renamed via `git mv`; there is only one dashboard page | Misleading "New" suffix | LOW | rename back |

---

## Flagged for human review (not changed)

1. **26 stale backend tests fail on baseline** (pre-existing, proven by
   stash-baseline run): ~20 `tests/test_walkthrough.py` cases still POST the
   pre-auth-rewrite `"role"` field (rejected 422 by current schema), plus
   `test_clients.py::test_employee_blocked_from_clients_module`,
   `test_finance.py::test_update_draft_invoice_replaces_items`,
   `test_financial_isolation.py::test_client_profile_masks_deal_value_below_l1`.
   These belong to the upcoming testing phase; fixing them here would have
   mixed test-maintenance into a refactor pass. **First testing-phase task.**
2. **starlette 1.x CVEs** (5 findings): require fastapi ≥0.136 migration —
   scheduled after testing phase (`docs/adr/0004`). Accepted residual risk
   needs sign-off.
3. **README**: left untouched — working tree contains uncommitted branding/
   docs WIP by the team; folding it into this pass would entangle unrelated
   edits. Update README architecture section after that WIP is committed.
4. Rate-limit consolidation, idempotency-key infra, circuit breakers,
   contract-test tooling: deferred deliberately — rationale in
   `DEPRECATION_LOG.md`.
5. `lint-imports` should be added to CI (backend-lint job) so contract
   breaks cannot recur silently.

## Backward compatibility statement

No API field renamed/removed/re-typed; one additive error field
(`request_id`). No env var renamed (`SMTP_FROM` never worked — corrected to
the actual name `EMAIL_FROM`); five additive vars introduced with safe
defaults. No database schema change at all (migrations untouched).
