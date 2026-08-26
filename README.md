# 🏛️ StudioERP — Architecture Studio ERP

A full-featured Enterprise Resource Planning (ERP) system built for architecture / design studios. It manages **attendance & leave**, **employees (HR)**, **projects**, **clients (CRM)**, **finance & accounting (GST invoicing)**, **payroll**, **tasks**, **site visits**, **reports & analytics**, and **internal communication** — plus one-click **Google Drive backups**.

> This repository was born from a client requirement ("we need an attendance system") that grew into a complete studio-management platform.

---

## 🚀 Quick Start (Docker)

```bash
# 1. Configure environment
copy .env.example .env

# 2. Start the full stack (db + backend + frontend)
docker compose up --build
```

| Service  | URL                        | Notes                     |
|----------|----------------------------|---------------------------|
| Frontend | http://localhost:5173      | Vite dev server (HMR)     |
| Backend  | http://localhost:8000      | FastAPI                   |
| API Docs | http://localhost:8000/docs | Swagger UI (dev only)     |
| Database | localhost:5432             | PostgreSQL 16             |

> See [docs/DOCKER.md](./docs/DOCKER.md) for production setup and troubleshooting.

---

## 🧱 Tech Stack

| Layer      | Technology                                   |
|------------|----------------------------------------------|
| Backend    | Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 |
| Database   | PostgreSQL 16 (Docker dev; PgBouncer in prod) |
| Frontend   | React 18 + TypeScript · Vite · Tailwind CSS  |
| Data layer | TanStack Query (server state) · Zustand (auth) · Axios |
| Auth       | JWT (access + refresh) · login by 6-digit User ID · org-level authorization (`L0 CEO … L6`) |
| Infra      | Docker & Docker Compose · Nginx (prod) · Render |

Full rationale and versions: [docs/TECH_STACK.md](./docs/TECH_STACK.md)

---

## 📚 Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture, monorepo layout, modular-monolith rules, data flow |
| [docs/TECH_STACK.md](./docs/TECH_STACK.md) | Every library chosen, version, and *why* |
| [docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) | Relational schema, enums, indexes, Alembic workflow |
| [docs/API_DESIGN.md](./docs/API_DESIGN.md) | REST API reference organized by module |
| [docs/FRONTEND.md](./docs/FRONTEND.md) | React app structure, routing, components, state management |
| [docs/DOCKER.md](./docs/DOCKER.md) | Docker dev/prod setup, Dockerfiles, commands, backups |
| [docs/PRODUCT_GUIDE.md](./docs/PRODUCT_GUIDE.md) | Plain-language product walkthrough for non-technical review |
| `_ai_context/` | Machine-readable project context (AI source of truth — start at `_ai_context/AI_INSTRUCTIONS.md`) |

---

## 📦 Project Structure

```
studio-erp/
├── backend/                  # FastAPI application — modular monolith
│   ├── app/
│   │   ├── main.py           # Entrypoint, middleware, router mount
│   │   ├── api/              # deps.py (auth + org-level guards), __init__.py (router registry)
│   │   ├── core/             # config, security, storage, email, rate limit
│   │   ├── db/               # session, base, init_db (+ first superuser seed)
│   │   ├── middleware/       # security headers, rate-limit tracker
│   │   ├── models/           # central model registry (cross-module reads)
│   │   ├── modules/          # domain modules — each owns its models/schemas/service/routes
│   │   ├── seeds/            # base company profile (Offsitearch) + optional demo data
│   │   └── utils/            # enums, state machines, org structure, pdf/xlsx writers
│   ├── alembic/versions/     # migrations 0001–0026
│   ├── tests/                # pytest (asyncio auto mode)
│   └── .importlinter         # machine-enforced module boundaries
├── frontend/                 # React + Vite + Tailwind
│   ├── src/
│   │   ├── features/         # Page/feature modules per domain
│   │   ├── components/ui/    # Shared UI primitives (DatePicker, CurrencyInput, …)
│   │   ├── api/              # One typed Axios module per backend domain
│   │   ├── layouts/ store/ hooks/ lib/
│   └── e2e/                  # Playwright specs
├── docs/                     # Human documentation set
├── docker-compose.yml        # Dev stack (db + backend + frontend)
├── docker-compose.prod.yml   # Production stack (Nginx)
└── .env.example              # Environment template
```

---

## 🗺️ Modules

1. **Dashboard** — role-aware home; revenue widgets visible to L0/L1 only
2. **Attendance & Leave** — check-in/out, calendar view, bulk entry, leave workflow *(primary client requirement)*
3. **Employee / HR** — directory, profiles, departments, org chart, department-wise designation catalog
4. **Project Management** — projects, phases/milestones, timeline; task board lives under Tasks
5. **Client Management (CRM)** — client profiles, pipeline deals, communication log
6. **Finance & Accounting** — GST-ready invoices (HSN/SAC line items, CGST/SGST/IGST PDF breakup), expenses, payments — all executive-only (L0/L1)
7. **Payroll** — payroll processing + PDF payslips (executive-only)
8. **Tasks** — kanban task board with checklists, linked to projects
9. **Site Visits** — visit logs with photo evidence + branded PDF reports
10. **Reports & Analytics** — attendance, project, financial, HR reports with CSV/XLSX export
11. **Settings & Admin** — company profile, attendance/leave policy, holidays, user administration, security, Google Drive backup (L0/L1)
12. **Communication** — notice board, meeting scheduler with RSVP, notification inbox, audit log

> Removed: **Vendors & Procurement** (feature cut, 2026-08-24). Documents/DMS was never implemented beyond schema.

---

## ✅ Current Status

Core platform is feature-complete and running through the full stack:

- **Backend**: FastAPI modular monolith — 20 domain modules under `app/modules/`, 26 registered routers, Alembic migrations `0001–0026`, import-linter-enforced boundaries.
- **Authorization**: org-level model (`L0 CEO > L1 Director > L2 Dept Head > L3 Lead > L4–L6 staff`) with rank-based guards. Financial data isolation is enforced server-side: any rupee figure (finance, payroll, salaries, project budgets/fees, client budget ranges) is **L0/L1 only**, mirrored in the UI.
- **Auth**: login by immutable 6-digit User ID (`YY####`); passwords generated server-side and shown exactly once; forced password-change gate; token-versioning evicts sessions on password events.
- **Invoicing**: structured GST line items (HSN/SAC, quantity × rate computed server-side), CGST/SGST vs IGST breakup on a branded monochrome invoice PDF; payslip and site-visit PDFs share the same letterhead system.
- **Backups**: Settings → Backup (L0/L1) — one-click Google Drive OAuth, manual or scheduled daily/weekly dumps (.json.gz), 30-file retention, encrypted tokens.
- **Frontend**: React SPA covering every module, warm-neutral brand design system, i18n (EN/HI), desktop-only layout, Playwright e2e suite scaffolding.

### Verification state

- Last documented full-green backend run: **187 passed** (financial-isolation boundary). A scripted auth-rewrite test migration (~24 suites) plus new isolation suites are **awaiting an owner-approved full pytest run** (intentional freeze).
- Static checks green: `ruff`, `lint-imports`, frontend `tsc --noEmit` + production build.

---

## 🔑 Local Dev Login

```bash
# Superuser is created on first startup from FIRST_SUPERUSER_EMAIL/PASSWORD.
# Login is by the immutable 6-digit User ID (YY####), NOT email.
# Find your superuser's ID after starting the stack:
docker compose exec db psql -U postgres -d offsite_erp \
  -c "SELECT login_id, email FROM users WHERE email='admin@studioerp.dev';"
```

You'll be prompted to set your own password on first login. Richer demo data: set `SEED_DEMO=true`.

---

## 🛠️ Development Commands

```bash
# Backend (from backend/)
pytest                 # async tests (currently frozen pending owner approval)
ruff check .           # lint (line-length 100)
lint-imports           # architecture contract check

# Frontend (from frontend/)
npm run build          # tsc --noEmit && vite build
npm run test:e2e       # Playwright

# Full stack
docker compose up --build
```
