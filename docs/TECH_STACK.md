# 🧰 Tech Stack

Chosen for an **architecture studio ERP**: pragmatic, proven, fast to build, and easy for a small team to maintain. This page reflects the stack **as built** (verified against `backend/requirements.txt` and `frontend/package.json`, 2026-08-24).

---

## 1. Backend — Python 3.12 + FastAPI

| Component | Choice | Version | Why |
|-----------|--------|---------|-----|
| Language | Python | 3.12 | Modern typing, match statements, fast; huge ecosystem |
| Web framework | FastAPI | 0.120+ | Async-native, auto OpenAPI docs, Pydantic v2 integration, high performance |
| ORM | SQLAlchemy | 2.0+ (async) | Mature, explicit control, async engine end-to-end (`asyncpg` driver at runtime; `psycopg` for sync/Alembic paths) |
| Migrations | Alembic | 1.13+ | Industry-standard schema versioning; non-destructive upgrades |
| Validation/settings | Pydantic + pydantic-settings | 2.x | Data contracts + `Settings` from env vars with production validators |
| Auth tokens | PyJWT | 2.13.x | JWT access/refresh (HS256) incl. the `tvp` token-version claim |
| Password hashing | bcrypt | 4.0.x | Industry-standard hashing only — no plaintext anywhere |
| Rate limiting | slowapi | 0.1.9 | Login attempt tracking + request throttling |
| Email | aiosmtplib + Jinja2 templates | 3.x / 3.1+ | Scaffolded flows behind `EMAIL_ENABLED=false` by default |
| File storage | local `/app/uploads` **or** Supabase Storage | supabase>=2.0 optional | Storage abstraction in `core/storage.py`; swap via env vars |
| Backup crypto | cryptography (Fernet) | ≥42 | Encrypts Google OAuth tokens at rest |
| Google Drive | plain httpx REST calls | httpx 0.27+ | Deliberately no Google SDK — minimal surface for OAuth + Drive upload |
| PDF/XLSX/CSV exports | in-house writers (`utils/pdf.py`, `utils/xlsx.py`, stdlib csv) | — | Dependency-free, valid zip/PDF output; no ReportLab/openpyxl by policy |
| Prod server | gunicorn + uvicorn workers | 22.x | Production process management |
| Testing | pytest (+ pytest-asyncio auto mode, httpx client) | — | Unit + integration suites mirroring modules |
| Lint/format | ruff (line-length 100) | latest | Fast, single tool |
| Arch contracts | import-linter (`.importlinter`) | latest | Machine-enforced module boundaries |

### `requirements.txt` (actual)

```
fastapi==0.120.*
starlette==0.49.*   # pinned for CVE fixes PYSEC-2026-1941/1942
uvicorn[standard]==0.30.*
sqlalchemy[asyncio]==2.0.*
psycopg[binary]==3.1.*
asyncpg==0.29.*
alembic==1.13.*
pydantic==2.*
pydantic-settings==2.*
email-validator==2.*
PyJWT==2.13.*
bcrypt==4.0.*
python-multipart==0.0.31 # CVE fixes: PYSEC-2026-1852/3036-3040
httpx==0.27.*
slowapi==0.1.9
aiosmtplib>=3.0,<4.0
Jinja2>=3.1,<4.0
supabase>=2.0,<3.0
gunicorn==22.*
cryptography>=42
```

> **Policy**: exports are in-house writers — do not add openpyxl/reportlab without asking. The Google Drive integration uses plain httpx on purpose.

---

## 2. Frontend — React 18 + TypeScript + Vite + Tailwind

| Component | Choice | Version | Why |
|-----------|--------|---------|-----|
| Framework | React | 18.3.x | Largest ecosystem; team familiarity |
| Language | TypeScript | 5.5.x | Catches contract bugs against the API (`build` runs `tsc --noEmit`) |
| Build tool | Vite | 8.2.x | Instant HMR, fast prod builds, first-class React support |
| Styling | Tailwind CSS | 3.4.x | Utility-first over CSS-variable design tokens (warm-neutral brand + gold accent) |
| Routing | react-router-dom | 7.x | Standard SPA routing with lazy routes + guards |
| Server state | TanStack Query | 5.x | Caching, retries, invalidation — kills boilerplate |
| Client state | Zustand | 4.5.x | Minimal global state (auth store only) |
| HTTP | Axios | 1.7.x | Interceptors: bearer injection + single-flight token refresh |
| i18n | i18next + react-i18next + browser language detector | 24 / 15 / 8 | EN/HI locales bundled from `src/locales/` |
| Icons | lucide-react | 0.441 | Consistent, lightweight |
| E2E tests | Playwright | 1.62.x | `npm run test:e2e` (persona-based specs in `frontend/e2e/`) |

In-house UI primitives instead of a component kit: `components/ui/` (Button, Modal, Toast, ConfirmDialog, StatusBadge, Skeleton, Breadcrumbs, TrendChip, DatePicker, TimeInput, CurrencyInput, EmptyState, MetricCard, NotificationBadge, PageHeader, SectionCard). No shadcn/ui, Recharts, TanStack Table, React Hook Form or drag-and-drop lib is installed.

---

## 3. Database — PostgreSQL 16

- Primary relational store. Everything (attendance, HR, projects, finance) is relational — Postgres is the right call.
- Row Level Security enabled via migration `0015_enable_rls`.
- Connection pooling in production via PgBouncer (`pgbouncer.ini`).
- Full schema: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md).

---

## 4. Infrastructure — Docker & Compose

| Piece | Role |
|-------|------|
| `postgres:16-alpine` | Database container |
| Backend image (python:3.12-slim) | Runs Alembic migrations on start + uvicorn (dev) / gunicorn (prod) |
| Frontend image (node → nginx multi-stage) | Dev: Vite HMR · Prod: static build behind Nginx |
| Named volumes | `pgdata` (DB), `uploads` (files) |
| Healthchecks | Backend waits for DB healthy; frontend waits for backend |

Full setup + commands: [DOCKER.md](./DOCKER.md)

---

## 5. Environment Variables (`.env.example`)

```ini
# ── Postgres ─────────────────────────────
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=offsite_erp
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres

# ── Backend core ─────────────────────────
SECRET_KEY=change-me-in-production      # REQUIRED strong value in production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development                 # production triggers guards + hides /docs
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ── Bootstrap / seed ─────────────────────
FIRST_SUPERUSER_EMAIL=admin@studioerp.dev
FIRST_SUPERUSER_PASSWORD=change-me      # must change in production
SEED_DEMO=false                         # true → demo dataset
LOGIN_MAX_ATTEMPTS=5
LOGIN_RATE_WINDOW_SECONDS=300

# ── Email (optional, off by default) ─────
EMAIL_ENABLED=false
SMTP_HOST= SMTP_PORT=587 SMTP_USER= SMTP_PASSWORD=
EMAIL_FROM=noreply@studioerp.dev

# ── Google Drive backup (optional) ───────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/backup/google/callback
BACKUP_UI_REDIRECT=http://localhost:5173/settings?tab=backup

# ── Supabase Storage (optional) ──────────
SUPABASE_URL= SUPABASE_KEY=
SUPABASE_STORAGE_BUCKET=studio-erp-uploads

# ── Frontend (Vite-prefixed) ─────────────
VITE_API_BASE_URL=/api/v1
VITE_APP_NAME=StudioERP

# ── Ports ────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

Full reference: `_ai_context/ENV_VARIABLES.md`.

---

## 6. Versioning & Upgrade Policy

- Pin compatible ranges in `requirements.txt` and `package.json` for reproducible builds.
- Alembic owns all schema changes — never `create_all()` in production; never edit applied migrations.
- Dependabot/renovate-style updates welcome once cadence justifies it.
