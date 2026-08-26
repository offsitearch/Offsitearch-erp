# Offsite ERP — System Architecture

Offsite ERP is a full-stack, single-repo ERP for an architecture studio
(Offsitearch): a React 18 SPA talks to a FastAPI **modular monolith** over a
versioned JSON API, backed by PostgreSQL 16.

```
┌────────────────────────────────────────────────────────────────────┐
│                             BROWSER                                │
│  React 18 SPA (Vite · TypeScript · Tailwind)                       │
│  TanStack Query (server state) · Zustand (auth store)              │
│  Axios client → Bearer JWT → /api/v1                               │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ HTTPS · REST/JSON
                 ┌─────────────▼──────────────┐
                 │  NGINX (prod, nginx.prod.conf)   │
                 │  static frontend + /api reverse proxy
                 │  (dev: Vite dev-server proxy instead)
                 └─────────────┬──────────────┘
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                FASTAPI APP  (backend/app/main.py)                  │
│  middleware: GZip · CORS · SecurityHeaders · RateLimitTracker      │
│              request-id + structured JSON logging                  │
│  ┌──────────────────── app/modules/<name>/ (×20) ───────────────┐  │
│  │  routes.py → service.py → repository/models.py               │  │
│  │  attendance audit backup clients dashboard employees finance │  │
│  │  holidays identity leave meetings notices notifications      │  │
│  │  orgstructure payroll projects reports settings site_visits  │  │
│  │  tasks                                                       │  │
│  └───────────────────────────────┬──────────────────────────────┘  │
│  shared: app/core · app/utils · app/db · app/models · app/seeds   │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ async SQLAlchemy 2.0 (asyncpg)
                ┌──────────────▼───────────────┐
                │  PostgreSQL 16               │
                │  (+ PgBouncer in prod; RLS on)│
                └──────────────────────────────┘
```

---

## 1. Monorepo layout

```
/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # FastAPI factory, middleware, lifespan
│  │  ├─ api/               # central router registry + deps + system/rate-limit routes
│  │  ├─ core/              # config, security (bcrypt/JWT), rate limit, email, storage
│  │  ├─ db/                # async engine/session, Base, startup seeding
│  │  ├─ middleware/        # security headers, rate-limit tracker
│  │  ├─ models/            # cross-module model registry (import boundary)
│  │  ├─ modules/<name>/    # the 20 feature modules (see §2)
│  │  ├─ seeds/             # reference data + optional demo dataset
│  │  └─ utils/             # enums, state machines, org structure, pdf/xlsx writers
│  ├─ alembic/              # migrations 0001–0026
│  ├─ entrypoint.sh         # alembic upgrade head → gunicorn (uvicorn workers)
│  └─ .importlinter         # architecture enforcement contracts
├─ frontend/
│  └─ src/
│     ├─ App.tsx            # lazy route table + auth/level gates
│     ├─ api/<domain>.ts    # typed Axios clients per domain
│     ├─ features/<domain>/ # page components grouped by domain
│     ├─ components/ui/     # design-system primitives
│     ├─ layouts/AppLayout  # sidebar shell + force-change-password gate
│     ├─ store/authStore.ts # Zustand auth state
│     └─ locales/{en,hi}.json
├─ docker-compose.yml       # dev stack
├─ docker-compose.prod.yml  # prod stack (nginx edge)
├─ render.yaml              # Render blueprint (API only)
├─ pgbouncer.ini            # transaction pooling config (e.g. Supabase pooler)
└─ docs/
```

---

## 2. Backend: modular monolith

The backend is **not** layered (`app/services`, `app/repositories` are long
gone). Each feature lives in `backend/app/modules/<name>/` and owns its own
tables, schemas, business rules and HTTP surface:

| Module | Owns |
|---|---|
| `attendance` | daily check-in records (+ `repository.py`, `defaults.py`) |
| `audit` | tamper-evident action log |
| `backup` | Google Drive config, run history, APScheduler jobs (`scheduler.py`) |
| `clients` | CRM: clients, communications, deal pipeline fields |
| `dashboard` | aggregated cross-module stats |
| `employees` | employee documents, directory/org-chart reads |
| `finance` | invoices, invoice items, expenses (3 routers) |
| `holidays` | holiday calendar |
| `identity` | users, login, refresh tokens, user admin (`users_admin.py`, `repository.py`) |
| `leave` | leave requests, balances (+ `defaults.py`) |
| `meetings` | meetings + attendee RSVPs |
| `notices` | notice board |
| `notifications` | per-user notification feed |
| `orgstructure` | departments + org levels (2 routers) |
| `payroll` | payroll runs, entries, salary components |
| `projects` | projects, phases, team (+ `defaults.py`) |
| `reports` | report generation (PDF/XLSX downloads) |
| `settings` | key–value app settings incl. company profile used on invoices |
| `site_visits` | site visits + photos |
| `tasks` | tasks + checklist |

**Central registry.** `app/api/__init__.py` mounts **26 routers** under
`/api/v1`: `system`, `auth`, `users`, `dashboard`, `attendance`, `leave`,
`employees`, `departments`, `org_levels`, `projects`, `clients`, `tasks`,
`finance`, `invoices`, `expenses`, `payroll`, `settings`, `holidays`,
`notices`, `meetings`, `notifications`, `site_visits`, `audit`, `reports`,
`backup`, `rate_limit`.

### Request flow

```
HTTP request
  → route handler      (app/modules/<name>/routes.py)
      deps: bearer JWT auth, require_min_level / financial gates,
            Pydantic body/query validation, slowapi rate limits
  → service            (service.py)   business rules, state machines, RBAC scoping
  → models/repository  (models.py, repository.py)  async SQLAlchemy queries
  ← response schema    (schemas.py)   Pydantic serialization
```

Routes never touch the DB directly; services never shape HTTP responses;
modules never import each other's models (see §5).

---

## 3. Authentication & authorization

### Identity model

- **Login handle**: immutable 6-digit **User ID** `login_id` formatted
  `YY####` (year of joining + per-year sequence, e.g. `260001`). Email is
  contact metadata only — it is *not* a login credential.
- **Passwords**: bcrypt hashes only. The legacy `password_plain` column was
  dropped by migration `0024`; generated one-time passwords are shown exactly
  once in create/regenerate responses.
- **Forced rotation**: `users.must_change_password` blocks every endpoint
  except `/api/v1/auth/*` until the password is changed (frontend mirrors this
  with a gate in `AppLayout`).
- **Session revocation**: JWTs carry a `tvp` (token-version) claim matching
  `users.token_version`. Every password event bumps the column, instantly
  invalidating outstanding access **and** refresh tokens.
- **Tokens**: HS256 JWTs signed server-side — access ~30 min, refresh ~7 days
  (refresh JTIs are persisted in `refresh_tokens` so they can be revoked).
- Login is rate-limited (default 5 attempts / 300 s window).

### Org-level RBAC (no role enum)

Authorization is driven by organizational levels stored as **rows** in
`org_levels` (L0–L6). Canonical ranks live in `app.utils.shared.LEVEL_RANK`
(lower = more senior):

| Level | Name | Band |
|---|---|---|
| L0 | CEO | executive |
| L1 | Director | executive |
| L2 | Department Head | leadership |
| L3 | Project / Team Lead | management |
| L4 | Sr. Professional | staff (self-service band) |
| L5 | Professional | staff |
| L6 | Intern | staff |

- Route guards use `require_min_level("Lx")` dependency factories; users with
  no level rank as least-privileged and are always rejected.
- Staff band (L4–L6) is scoped to self-service data via `is_staff_band`.
- Designations and departments never grant permissions — they are HR metadata.

### Financial-data boundary (client mandate)

Invoices, expenses, payroll, salaries, budgets, deal values and revenue
figures are restricted to **L0 CEO and L1 Director only**
(`FINANCIAL_LEVEL = "L1"`). Enforcement points:

- `api.deps.require_financial_access()` guards every financially-sensitive
  endpoint (writes return 403 below L1);
- `has_financial_access()` is used when serializing so money fields are
  omitted/redacted for unauthorized callers (projects/clients redact budget,
  fees, deal values).

---

## 4. Cross-cutting concerns

| Concern | Implementation |
|---|---|
| Rate limiting | slowapi limiter keyed by remote address; `RateLimitTrackerMiddleware` records hits; dedicated `/rate_limit` status router |
| Security headers | `SecurityHeadersMiddleware` (CSP, HSTS, frame denial, …) |
| Compression | GZip middleware (min size configurable) |
| Observability | UUID `request_id` per request (`X-Request-ID` header), structured JSON logs with method/path/status/duration |
| Audit trail | `audit_logs` rows capture actor, action, entity, JSON details, `ip_address`, `user_agent`, `request_id` |
| Defense in depth | Row Level Security enabled on all public tables (migration `0015`) as a backstop if credentials leak |
| Config | Pydantic settings from `.env`; production guard refuses default secrets |
| Background work | Backup scheduler started/stopped in the FastAPI lifespan |

---

## 5. Import boundaries (enforced)

`.importlinter` contracts keep the monolith honest:

1. **core-independent** — `app.core` and `app.utils` never import from
   `app.modules` or `app.api`.
2. **model-boundaries** — module `models.py` files are mutually independent;
   cross-module reads go through services or the `app.models` registry.
3. **no-main-from-modules** — modules never import `app.main`.

---

## 6. Frontend architecture

- **Stack**: React 18 + Vite + TypeScript, TanStack Query for server state,
  Zustand (`store/authStore.ts`) for tokens/session, react-router-dom.
- **API layer**: one Axios instance (`api/client.ts`) with base URL `/api/v1`;
  request interceptor injects the bearer token, response interceptor performs
  transparent `/auth/refresh` retry once, then hard-redirects to `/login`.
  Domain clients (`api/projects.ts`, `api/finance.ts`, …) expose typed calls.
- **Routing**: `App.tsx` declares a lazy-loaded route table wrapped in
  `RequireAuth`; privileged subtrees use `<RequireRole minLevel="Lx" />`
  (mirrors backend levels):
  - `minLevel="L3"` — leave approvals, employee directory/profiles, clients
  - `minLevel="L2"` — departments, settings
  - `minLevel="L1"` — finance dashboard/invoices/expenses, payroll, reports
- **Shell**: `layouts/AppLayout.tsx` renders sidebar navigation and forces
  the change-password flow when required.
- **UI kit**: `components/ui` primitives (Button, Modal, Toast, DatePicker,
  TimeInput, CurrencyInput, StatusBadge, MetricCard, Skeleton, …) plus
  `components/` (ConfirmDialog, ErrorBoundary, MobileBlockScreen).
- **i18n**: English + Hindi catalogs (`locales/en.json`, `locales/hi.json`).
- **Desktop-only**: `MobileBlockScreen` blocks small viewports by product
  decision.

---

## 7. Deployment topologies

| Target | Files | Shape |
|---|---|---|
| Dev (Docker) | `docker-compose.yml` | postgres:16-alpine + backend (`alembic upgrade head && uvicorn --reload`) + frontend (Vite HMR); source mounted for hot reload |
| Prod (Docker) | `docker-compose.prod.yml`, `nginx.prod.conf` | nginx edge serves built SPA, proxies `/api` → backend running gunicorn + uvicorn workers behind healthchecks |
| Render | `render.yaml`, `backend/entrypoint.sh` | managed web service: `entrypoint.sh` runs migrations then gunicorn (`WEB_CONCURRENCY` workers); healthcheck `/api/v1/system/ready` |
| Managed Postgres | `pgbouncer.ini` | transaction-mode pooling (e.g. Supabase pooler) sized for the async engine |

Migrations run automatically: **`alembic upgrade head` executes on every
backend boot** (compose command or entrypoint), followed by idempotent
reference-data seeding (`app.db.init_db`).

---

_Last Updated: 2026-08-24_
