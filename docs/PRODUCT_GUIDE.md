# OFFSITE ERP — Product Guide

_A plain-language walkthrough of what this application is, everything it does, and how it works. Written so that anyone — technical or not — can read it end-to-end and understand the product before deciding what to add, remove, or improve._

_Date: 2026-08-23 · Status: v1 feature-complete, final verification pending_

---

## 1. What This Project Is

**OFFSITE ERP** is an internal management platform for an architecture/design studio. It started when the client asked for "an attendance system" and grew into a full studio operating system covering:

> **Attendance & leaves · People/HR · Projects · Clients (CRM) · Finance & Payroll · Tasks · Site Visits · Reports · Internal communication · Google Drive backups**

Everything lives behind one login, on one desktop web app. It is **not** a public website and **not** mobile-friendly by design — it's a tool for the studio's own team, used on office computers.

### The one-sentence pitch

_"A single place where the studio tracks who showed up, who's working on what, which client/project is at which stage, what money came in and went out, and what the team needs to know today."_

---

## 2. Who Uses It

Every person signs in with a **6-digit User ID** (like `260001`) and a password. Each account belongs to an **organization level** that controls what they see:

| Level | Title | Sees / does |
|-------|-------|-------------|
| **L0** | CEO | Everything |
| **L1** | Director | Everything (with CEO). Together L0+L1 are "executives" — the only people who can see **any money figures** |
| **L2** | Department Head | Operational admin: holidays, notices, bulk attendance, departments, settings, non-financial oversight. **No money figures** |
| **L3** | Lead / Project Lead | Team-level work: approves leaves/expenses, manages clients & deals, sees employee directory, schedules meetings/site visits |
| **L4–L6** | Staff / Junior / Intern | Self-service: check in/out, apply for leave, do assigned tasks, read notices, claim expenses |

**The most important rule in the product:** money data (revenue, invoices, expenses, salaries, payroll, project budgets, client budgets) is **visible only to L0/L1**. Even a Department Head (L2) cannot see a single rupee figure. This was an explicit client requirement and is enforced in the backend, not just hidden in the UI.

---

## 3. How It Works (in plain words)

```
┌─────────────────┐         ┌──────────────────────┐        ┌────────────┐
│  React web app  │ ──API──▶│  FastAPI backend     │ ────▶  │ PostgreSQL │
│  (what users    │ (JSON + │  (rules, permissions,│        │ (database: │
│   see & click)  │  tokens)│  business logic)     │        │  all data) │
└─────────────────┘         └──────────────────────┘        └────────────┘
```

- **One codebase, three parts**: a React frontend (the screens), a FastAPI Python backend (the brain), and a PostgreSQL database (the memory). All shipped together with Docker.
- **Login**: you enter your User ID + password. The backend verifies them and issues two signed digital passes (JWTs): a short-lived *access token* (~30 min) and a long-lived *refresh token* (7 days). Every screen call carries the access pass; when it expires the app silently renews it.
- **Permissions**: every API endpoint checks *who you are* and *your level* before answering. The UI hides things too, but the backend is the real gatekeeper — hiding alone is never trusted.
- **Money boundary**: a central rule (`has_financial_access`) decides money visibility. Money fields are stripped from responses entirely below L1 — they're not just blanked out, they never reach the browser.
- **Audit trail**: sensitive actions (approvals, edits to records, password resets…) are logged with who/what/when/IP/request-id.
- **Runs locally or deployed** via Docker Compose (dev) or an Nginx production stack; a Render cloud config also exists.

---

## 4. Signing In & Passwords

This area was recently rebuilt around security best practices:

1. **No email logins.** Everyone logs in with their User ID (`YY####`: first two digits = joining year, rest = sequence; e.g. someone joining in 2026 could be `260014`). IDs are permanent and shown on profiles and the Users admin screen.
2. **Passwords are generated, never chosen by admins.** When an executive creates an employee (or resets their access), the system generates a random temporary password and shows it **exactly once** on screen. Nobody — including the CEO — can go back and view anyone's password later.
3. **First-login force-change.** New/reset users are locked out of every screen until they set their own password (a full-screen "Set your new password" page).
4. **Instant session kill.** Any password event invalidates all of that user's existing logins everywhere (via a version counter inside the tokens).
5. **"Forgot password?"** = ask an executive to regenerate. There is deliberately no email-based self-reset (email is switched off in v1 — see §10).
6. Users can always change their own password from **Settings → Security**.

There is also a rate limiter: repeated failed logins get throttled (5 attempts / 5 minutes).

---

## 5. Complete Page-by-Page Tour

_The left sidebar groups everything into four sections. Access levels shown are minimums; higher levels always included._

### 5.1 Dashboard (`/dashboard`) — everyone

The home screen. A greeting, then widgets:

- **KPI cards** — total team members, present today, on leave/late today, active projects.
- **Revenue this month** — 💰 executives (L0/L1) only.
- **Attendance trend** — line chart of daily presence over recent weeks.
- **Today's people** — live list of who checked in/out, who hasn't.
- **Active projects** — current projects with status chips.
- **Upcoming deadlines** — tasks/projects due soon.
- **Latest notices** — recent announcements.
- **Revenue snapshot + overdue-invoice alert** — executives only; the alert warns about unpaid invoices past due.

### 5.2 Studio section (work)

#### Projects (`/projects`)
- **List** — all projects the user may see (staff see only their projects), filter by status/type; managers create projects.
- **Kanban board** (`/projects/board`) — drag-and-drop task cards across To-do → In progress → Review → Done.
- **Detail page** (`/projects/:id`) with four tabs:
  - _Overview_ — description, client, dates, team; budget & studio-fee figures visible to executives only.
  - _Phases_ — design-phase breakdown (concept → design → review → construction…) each with dates, progress %, and (for executives) fees.
  - _Team_ — members with roles; leads add/remove people.
  - _Timeline_ — Gantt-style visual of phases against the calendar.
- Managers can edit/archive projects; money fields are rejected server-side if a non-executive tries to save them.

#### Tasks (`/tasks`) — everyone
Personal + assignable kanban board: priorities, due dates, assignees, project links. Assigning notifies the person.

#### Clients (`/clients`) — L3+
- **List** — searchable client cards (individual/company/developer/government), lead+ create/edit, director+ delete. Budget-range badges are executive-only.
- **Profile** (`/clients/:id`) — full relationship view: contact persons, communication log (every call/email/meeting/site visit recorded), **deals pipeline** (Lead → Proposal → Negotiation → Won/Lost) with attached fees, linked projects, and a finance summary panel (totals invoiced/received/outstanding — executives only).

### 5.3 People section

#### Attendance (`/attendance`) — tabbed page
- **My Attendance** (everyone) — big Check-in / Check-out button (web-based, timestamps + IP recorded), live worked-hours counter, personal month calendar showing presence/holidays/leaves, history list.
- **Today** (L3+) — studio-wide roster for any date: who's present/absent/late/WFH, department filter; leads/admins can **correct** a record (audit-logged); CSV export.
- **Calendar** (L3+) — month grid per department with color-coded statuses and totals.
- **Bulk Entry** (L2+) — mark attendance for many people at once (e.g., office-wide WFH day).

Late/grace/half-day rules come from configurable settings, not hardcoded values.

#### Leaves (`/leaves`)
- **My Leaves** (everyone) — remaining-balance cards per type, request history with statuses.
- **Apply** (everyone) — pick type (casual, sick, earned, compensatory, maternity, paternity, work-from-home, unpaid), date range, reason. Overlapping requests are blocked; balances enforced.
- **Approvals** (L3+) — pending queue; approve/reject with a comment. Decisions update balances automatically and notify the applicant.

#### Employees (L3+)
- **Directory** (`/employees`) — searchable team roster with photos, department, level, status. Leads can onboard new employees: a guided form creates the account and immediately shows a **one-time card with the new User ID + temporary password** to hand over securely.
- **Profile** (`/employees/:id`) — deep HR record: personal details, job info (department, level, designation — designation options auto-filtered by level), reporting manager, joining date. Sub-sections: attendance summary, leave history, **documents** (upload/download offer letters, IDs, certificates), and a **salary section visible to L0/L1 only**.
- **Org Chart** (`/employees/org-chart`, L3+) — visual reporting tree; drag-free promote/edit dialogs.
- **Departments** (`/departments`, L2+) — create departments, assign heads, manage org levels (L1+ for levels).

### 5.4 Studio Life section (communication)

- **Notices** (`/notices`) — announcement board; importance badges (low/med/high), pinned items stay on top, publish/expiry windows control visibility; admins post/edit/delete.
- **Meetings** (`/meetings`) — upcoming meetings as cards; schedule internal/client/site/video meetings, multi-select attendees (they get notified), recipients **RSVP accept/decline**, organizer marks complete or cancels.
- **Notifications** (`/notifications`) — personal inbox fed automatically by the system: leave decisions, task assignments, meeting invites, etc. Unread count badge in the sidebar/header; mark one or all read.
- **Site Visits** (`/site-visits`) — field-visit register: leads log a visit against a project, attach **photo evidence**, generate a branded **PDF report**, mark complete, delete.

### 5.5 Administration section

#### Finance (L0/L1 — invisible to everyone else, including L2)
- **Overview** (`/finance/overview`) — revenue, expenses, profit, outstanding receivables with period filters and charts.
- **Invoices** (`/finance/invoices`) — full lifecycle: create with line items → send → record payments (partial or full) → auto-status becomes Partial/Paid/Overdue → download PDF.
- **Expenses** (`/finance/expenses`) — company expenses with categories, receipts, approval workflow.
- **Payroll** (`/finance/payroll`) — pick a month → system generates payroll from attendance + salary data → review entries → process (Draft → Processed) → download individual **payslip PDFs**.

#### My Expenses (`/finance/my-expenses`) — everyone
The one money screen staff can see: submit their own expense claims (travel, materials…), attach receipts, track approval status. They see only their own claims, never amounts belonging to others.

#### Reports (`/reports`) — L1+ (see §11 note)
Four report builders, each with CSV/Excel export:
- **Attendance** — date-range × department presence reports.
- **Projects** — status/portfolio report.
- **Finance** — revenue/expense reports (true executive territory).
- **HR** — headcount and utilization by month.

#### Settings (`/settings`) — L2+
Tabs:
1. **Company** — name, logo, address, registration details (used across exports/PDFs).
2. **Attendance Policy** — working hours, grace period, half-day rules.
3. **Leave Policy** — yearly quotas per leave type.
4. **Holidays** — holiday calendar with recurring yearly flags.
5. **Users** — the user-administration table: search, create users (auto-generates User ID + one-time password), edit level/department/designation, set a hardened new password, **Reset password** (director-only action generating a fresh one-time password), activate/deactivate accounts.
6. **Security** — change your own password (current → new).
7. **Backup** — **L0/L1 only**: connect Google Drive in one click, run a backup now or set an automatic daily/weekly schedule, download the raw `.json.gz` file, view backup history.

> Interface language (English/Hindi) is switched from the profile menu / browser detection via i18n, not a settings tab.

---

## 6. Feature × Level Permission Matrix

| Capability | L0/L1 | L2 | L3 | L4–L6 |
|---|---|---|---|---|
| Dashboard (full, with revenue) | ✅ | ✅ minus money | ✅ minus money | ✅ minus money |
| Check-in/out, my attendance | ✅ | ✅ | ✅ | ✅ |
| Today's roster / corrections | ✅ | ✅ | ✅ | ❌ |
| Bulk attendance | ✅ | ✅ | ❌ | ❌ |
| Apply/approve leaves | ✅ | ✅ | ✅ | apply only |
| Employee directory & profiles | ✅ | ✅ | ✅ | ❌ (own profile via header) |
| Salary figures | ✅ | ❌ | ❌ | ❌ (own payslip via payroll) |
| Departments manage | ✅ | ✅ | ❌ | ❌ |
| Projects (view own/work) | ✅ | ✅ | ✅ | ✅ (assigned only) |
| Create/manage projects | ✅ | ✅ | lead-assigned | ❌ |
| Project budget/fee figures | ✅ | ❌ | ❌ | ❌ |
| Clients & deals | ✅ | ✅ | ✅ | ❌ |
| Delete client | ✅ | ❌ | ❌ | ❌ |
| Client budget range | ✅ | ❌ | ❌ | ❌ |
| Tasks board | ✅ | ✅ | ✅ | ✅ |
| Finance (invoices/expenses/overview) | ✅ | ❌ | ❌ | ❌ |
| Payroll processing | ✅ | ❌ | ❌ | ❌ |
| My expense claims | ✅ | ✅ | ✅ | ✅ |
| Reports page | ✅ | ❌ (see §11) | ❌ | ❌ |
| Settings & holidays & notices mgmt | ✅ | ✅ | ❌ | ❌ |
| Create users / reset passwords | ✅ (regenerate: L1+ only, junior targets) | ❌ | ❌ | ❌ |
| Backups (Google Drive / download) | ✅ | ❌ | ❌ | ❌ |

---

## 7. Rules the System Enforces Automatically

- **Status machines** — every lifecycle follows fixed transitions, e.g. invoices `draft→sent→partial/paid(+overdue/cancelled)`, leaves `pending→approved/rejected(→cancelled)`, payroll `draft→processed`, projects through their design phases. Illegal jumps are refused by the backend and covered by automated tests.
- **Balance enforcement** — leave applications beyond remaining balance or overlapping dates fail.
- **Auto-notifications** — leave decisions, task assignments, meeting invites create inbox items without anyone remembering to send them.
- **Audit logging** — approvals, corrections, user/password changes, settings edits, deletions: all recorded with actor, timestamp, IP, request ID (queryable via API; no UI screen yet — §11).
- **Financial redaction** — below L1, money keys are physically removed from API responses and money writes return `403`; dashboards null out revenue; reports close entirely.
- **Session hygiene** — deactivated users are locked out instantly even mid-session; password changes evict every logged-in device; refresh tokens are single-use and revocable (logout works).
- **Production guards** — the app refuses to boot in production mode with default passwords/secrets, and disables API docs publicly.

---

## 8. Security Summary (non-technical)

| Concern | How it's handled |
|---|---|
| Password theft | Only bcrypt hashes stored; the old plaintext column was **removed** from the database entirely |
| Password snooping by admins | Impossible — passwords are generated, shown once, hashed; executives can only *reset*, never *view* |
| Stolen session tokens | Short expiry, silent renewal, instant invalidation on password events, single-use refresh tokens |
| Privilege escalation | Rank checks: you can't edit/reset someone senior to you; level changes restricted |
| Brute-force login | Rate limiting + attempt tracking |
| Data interception | HTTPS-ready deployment, Bearer-token scheme, CORS allow-list |
| Tampering with requests | Server-side permission checks on **every** endpoint; UI hiding is cosmetic only |
| Secrets in code | Environment-variable configuration with strong-secret validators for production |

---

## 9. Tech Stack (for reference)

- **Frontend**: React 18 + TypeScript + Tailwind CSS, TanStack Query (data fetching), Zustand (login state), i18next (EN/HI), Vite build.
- **Backend**: Python FastAPI (async), SQLAlchemy 2, Pydantic v2, Alembic migrations (24 so far), slowapi rate limiter, import-linter enforcing clean module boundaries (20 domain modules).
- **Database**: PostgreSQL 16 with Row-Level Security enabled.
- **Infra**: Docker Compose dev stack; Nginx production compose; Render cloud config; PgBouncer connection pooling.
- **Quality gates**: ~24 pytest suites (auth, permissions matrix, state machines, end-to-end walkthrough), TypeScript strict typecheck, ruff linting.

---

## 10. Deliberate Limitations of v1

These are known and intentional — worth confirming they stay acceptable:

1. **Email is off.** Nothing sends emails: not password resets, not invoice delivery, not meeting invites. All notification is in-app. (SMTP config exists, waiting on a decision.)
2. **Desktop-only.** Phones/tablets show a friendly "open on a computer" screen.
3. **Documents are per-person only.** Files attach to employee profiles (HR docs) and expenses/site-visits (receipts/photos). There is no general studio document management (drawings, DWGs, contracts library) — see §11.
4. **Forgot password = human process.** An executive regenerates; no automated recovery exists.
5. **Single organisation.** One studio per installation; no multi-company/multi-tenant mode.
6. **Check-in methods.** Currently web check-in (IP/timestamp recorded). QR-code/GPS methods exist as data labels but aren't built as flows.
7. **Audit log has no UI screen.** Data is captured; viewing requires API access.

---

## 11. Discussion Points for v1 Hardening

Candidates to raise with seniors, roughly in impact order:

### Possibly missing (add?)
1. **Studio Document Center** — a shared library for drawings/contracts/templates with folders + permissions. The database already has document tables (unused); the team will likely ask for this first.
2. **Audit Log viewer screen** — an admin page over existing data (low effort, high trust win: "who changed what").
3. **Reports access nuance** — the whole Reports page is director-only because two of its four tabs contain money. Splitting Attendance + HR tabs down to L2 would restore useful non-financial reporting without breaking the money rule.
4. **Client-facing artifacts** — quotation/invoice PDF branding toward clients (partially delivered: GST breakup + brand letterhead now exist); possibly a read-only client portal much later.
5. **Leave year configuration** — define whether balances reset per calendar/fiscal year and comp-off expiry rules (currently simple annual quotas).
6. **Orphaned-table cleanup migration** — drop the unused vendors/timesheets/documents tables left in the DB after the vendors module removal.

### Possibly trimming / deferring (remove or simplify?)
7. **Deals pipeline depth** — if the studio doesn't run structured sales stages, the CRM pipeline could be simplified to "client + projects".
8. **Meeting RSVP** — confirm it's actually used internally; if not, plain scheduling suffices.
9. **Org chart editing** — could be read-only if promotions stay rare/administrative.

### Polish before handover
11. Full test-suite verification run (currently frozen pending owner approval) + fix fallout.
12. README/onboarding docs refresh for the client's team (User-ID login explanation, admin handbook).
13. Hindi translation completeness pass.
14. Deployment rehearsal: backups, HTTPS certificate, domain, super-user password change from the dev default.
15. Seed/demo-data strategy for the client's first login (real employees vs demo data cleanup).

---

## 12. Quick Reference

| Thing | Where |
|---|---|
| Run locally | `docker compose up --build` → app at http://localhost:5173 |
| First login | User ID of seeded owner account (query `SELECT login_id, email FROM users;`) |
| Change own password | Settings → Security |
| Reset someone's password | Settings → Users → key icon (directors only) |
| Switch language | Profile menu (EN/हिंदी, auto-detected from browser) |
| Back up data | Settings → Backup (L0/L1) — Google Drive or direct download |
| API docs (dev only) | http://localhost:8000/docs |
| Deeper technical docs | `_ai_context/` folder (SECURITY.md, MODULES.md, API_ENDPOINTS.md…) |

---

_This document describes the product as implemented on 2026-08-23. If code changes materially, update this file alongside `_ai_context/CHANGE_LOG.md`._
