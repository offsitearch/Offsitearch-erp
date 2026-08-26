# Offsite ERP — Database Schema

PostgreSQL 16, accessed through SQLAlchemy 2.0 **async** (`asyncpg`) and
migrated with Alembic (`backend/alembic/versions/`, revisions `0001`–`0026`).

Conventions:

- Timestamps are stored in **UTC** (`DateTime(timezone=True)`); the business
  timezone is Asia/Kolkata and is applied only at the display layer.
- Primary keys are autoincrement integers; most tables use a
  `TimestampMixin` (`created_at` / `updated_at`).
- Soft deletes where present are `is_active = false` (never row deletion).
- Enum-like columns store the **lowercase string value** of Python enums from
  `app/utils/enums.py` via `SAEnum(native_enum=False)` — no PG enum types for
  domain statuses.

---

## 1. Migration timeline

`alembic upgrade head` runs automatically on backend boot (entrypoint/compose).

| Revision | Name | What it does |
|---|---|---|
| 0001 | initial | `users`, `departments`, `refresh_tokens`, `settings` |
| 0002 | attendance | `attendance`, `holidays` |
| 0003 | leave_hr | `leave_balance`, `leaves`, `employee_documents`, `salary_components` |
| 0004 | projects_clients | `clients`, `projects`, `project_team`, `project_phases`, `client_communications` |
| 0005 | tasks_timesheets_documents | `tasks`, `task_checklist`; timesheet & document tables (**now orphaned**, see §5) |
| 0006 | finance_vendors_payroll | `invoices`, `invoice_items`, `expenses`, `payroll_runs`, `payroll_entries`; `vendors`, `vendor_projects` (**orphaned**) |
| 0007 | reports_settings_comm | `notices`, `meetings`, `meeting_attendees`, `notifications`, `site_visits`, `site_visit_photos`, `audit_logs` |
| 0008 | crm_pipeline_fees | CRM pipeline on clients: `deal_stage` + follow-up fields; per-phase studio fees |
| 0009 | contact_email_and_password_change | `users.contact_email` + password-change flow columns |
| 0010 | fix_enum_case | normalize enum values to lowercase strings |
| 0011 | add_indexes_fix_cascade | secondary indexes + FK cascade fixes |
| 0012 | add_performance_indexes | performance indexes on hot filter/join paths |
| 0013 | fix_constraint_names | canonical constraint naming |
| 0014 | fix_deal_stage | deal_stage value/type repair |
| 0015 | enable_rls | Row Level Security policies on all public tables (defense-in-depth) |
| 0016 | audit_ip_user_agent | `audit_logs.ip_address`, `user_agent` |
| 0017 | add_password_plain | added `users.password_plain` — **superseded, column dropped by 0024**; never reintroduce |
| 0018 | add_audit_request_id | `audit_logs.request_id` (correlates with `X-Request-ID`) |
| 0019 | org_structure_refactor | create `org_levels`; rewire authorization to levels |
| 0020 | backfill_org_levels | backfill `users.org_level_id` from legacy roles |
| 0021 | drop_user_role | drop `users.role` + `user_role` enum — RBAC by org level only |
| 0022 | rename_org_levels | rename level rows to L-codes taxonomy (L1 Director … L6 Intern) |
| 0023 | add_l0_ceo | insert `L0 CEO` level row |
| 0024 | userid_auth | `users.login_id` (`YY####`, unique+indexed, backfilled per joining-year cohort), `must_change_password`, `token_version`; drops `password_plain`; BEFORE-INSERT trigger fallback assigns login ids to ORM rows that omit it |
| 0025 | backup_google_drive | `backup_configs` (singleton) + `backup_history` |
| 0026 | invoice_hsn_sac | `invoice_items.hsn_sac String(20)` |

---

## 2. The `users` table today

Defined in `app/modules/identity/models.py`. Key columns:

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `login_id` | String(6), UNIQUE + indexed | immutable login handle `YY####`; trigger backstop on INSERT |
| `email` | String(255), unique + indexed | contact only — **not** a login credential |
| `contact_email`, `phone` | nullable | HR contact metadata |
| `password_hash` | String(255) | bcrypt only; no plaintext column exists |
| `must_change_password` | bool | gates all non-auth endpoints until rotation |
| `token_version` | int | bumped on password events; compared against JWT `tvp` claim |
| `org_level_id` | FK → `org_levels.id` | drives all authorization |
| `department_id` | FK → `departments.id` | |
| `reporting_to_id` | FK → `users.id` | self-reference |
| `date_of_joining` | date | used for login-id year prefix |
| `employment_type` | enum-as-string | full_time/part_time/contract/internship |
| `is_active` | bool | soft delete |

There is **no role column and no role enum** (dropped in `0021`) and **no
plaintext password column** (dropped in `0024`). `refresh_tokens` stores
refresh-token JTIs (`user_id`, `jti` UUID unique, `expires_at`, `revoked`).

---

## 3. Tables by module

Live tables (each owned by exactly one module under `app/modules/`):

| Module | Table(s) | Key contents |
|---|---|---|
| identity | `users`, `refresh_tokens` | accounts & auth sessions |
| orgstructure | `departments` (self-referencing tree, `head_id`), `org_levels` (`code` L0–L6, `rank`, `is_active`) | org hierarchy |
| employees | `employee_documents` | files linked to users |
| attendance | `attendance` | daily status/method records |
| leave | `leave_balance` (unique user+type+year), `leaves` | requests, approvals |
| projects | `projects` (budget/fees — financial fields), `project_team`, `project_phases` | delivery |
| clients | `clients` (CRM: `deal_stage`, follow-up, budget_range), `client_communications` | CRM |
| tasks | `tasks` (project/phase/assignee FKs, parent task), `task_checklist` | work management |
| finance | `invoices` (`tax_percent`, `tax_amount`, `paid_amount`, payment fields inline), `invoice_items` (`hsn_sac`, quantity, rate, amount), `expenses` (`category` free-text, receipt path, approver) | billing & spend |
| payroll | `payroll_runs` (unique month/year, `PayrollStatus draft→processed`), `payroll_entries` (gross/deductions/net, payslip path), `salary_components` (per-user CTC split, bank details) | payroll |
| backup | `backup_configs` (singleton id=1, Google Drive OAuth tokens, schedule), `backup_history` (status/trigger/file metadata) | ops |
| settings | `settings` (`group`,`key`,`value JSONB`, unique per group+key) | company profile, app config |
| holidays | `holidays` (with recurring flag) | calendar |
| notices | `notices` (`NoticeImportance`) | comms |
| meetings | `meetings`, `meeting_attendees` (RSVP status) | comms |
| notifications | `notifications` | per-user feed |
| site_visits | `site_visits`, `site_visit_photos` | field ops |
| audit | `audit_logs` (actor/action/entity/details JSON/ip/user_agent/request_id) | security trail |

Notes:

- There is **no separate `payments` table** — payments are recorded inline on
  `invoices` (`paid_amount`, `payment_date`, `payment_method`).
- Org levels are **rows in `org_levels`**, not a PostgreSQL enum.
- `expenses.category` is currently a free-text `String(80)` even though an
  `ExpenseCategory` enum exists [TODO: verify whether the enum should be enforced].

---

## 4. Enums (`app/utils/enums.py`)

Stored as lowercase strings (`native_enum=False`). Workflow transitions are
guarded separately in `app/utils/state_machines.py`.

| Enum | Values |
|---|---|
| ProjectStatus | `draft → concept → design → under_review → in_construction → completed` (+ `on_hold`, `cancelled`) |
| PhaseStatus | `not_started / in_progress / completed / delayed` |
| ProjectType | `residential, commercial, interior, institutional, landscape, urban_planning, renovation, mixed_use` |
| TaskStatus | `todo / in_progress / review / done / blocked` |
| TaskPriority | `low → medium → high → urgent` |
| InvoiceStatus | `draft / sent / partial / paid / overdue / cancelled` |
| PaymentMethod | `bank_transfer / upi / cash / cheque / card` |
| ExpenseStatus | `pending / approved / rejected` |
| ExpenseCategory | `travel, material, software, printing, subcontract, office, utilities, salary, other` |
| PayrollStatus | `draft / processed` |
| LeaveType | `casual, sick, earned, compensatory, maternity, paternity, work_from_home, unpaid` |
| LeaveStatus | `pending / approved / rejected / cancelled` |
| AttendanceStatus | `present / absent / late / half_day / work_from_home / on_leave` |
| AttendanceMethod | `web / manual / qr / gps / ip` |
| EmploymentType | `full_time / part_time / contract / internship` |
| DealStage | `lead → proposal → negotiation → won / lost` |
| ClientType | `individual / company / developer / government` |
| CommunicationType | `call / email / meeting / site_visit` |
| NoticeImportance | `low / medium / high` |
| MeetingType | `internal / client / site / video` |
| MeetingStatus | `scheduled / completed / cancelled` |
| RsvpStatus | `pending / accepted / declined` |
| SiteVisitStatus | `scheduled / completed / cancelled` |

Removed/obsolete: `UserRole` (enum + column dropped in `0021`),
`vendor_category` (code enum removed with the vendors module). Authorization
levels are data rows (`org_levels`), not enums.

---

## 5. Orphaned tables — do not use

The vendors and documents modules were deleted from the codebase, but their
tables have **no drop migration yet**. They still exist in deployed databases
and are covered by RLS, but nothing reads or writes them:

| Table(s) | Origin | Status |
|---|---|---|
| `vendors`, `vendor_projects` | migration `0006` | **Orphaned** — module removed 2026-08-24; cleanup candidate |
| `timesheets`, `timesheet_entries` | migration `0005` | **Orphaned** — no model/route; replaced by task hours; cleanup candidate |
| `document_folders`, `documents`, `document_versions` | migration `0005` | **Orphaned** — DMS module dropped (live file storage uses `employee_documents` + uploads); cleanup candidate |

Do not build new features on these tables; a future migration should drop them
after a verified backup.

---

## 6. Relationship map (ERD summary)

```
org_levels 1───* users *───1 departments        users *───1 users (reporting_to)
users 1───* refresh_tokens · leave_balance · leaves · attendance · notifications
users 1───* employee_documents · salary_components(1:1) · site_visit photos(authors)

clients 1───* projects · client_communications          clients 1───* invoices
projects 1───* project_team *───1 users
projects 1───* project_phases 1───* tasks
projects 1───* tasks (also phase-scoped, self-parenting checklist)
projects 1───* expenses · site_visits · invoices (optional project link)
invoices 1───* invoice_items
payroll_runs 1───* payroll_entries *───1 users
meetings 1───* meeting_attendees *───1 users
site_visits 1───* site_visit_photos
```

Tabular highlights:

| Parent | Child (FK) | Cardinality |
|---|---|---|
| `org_levels` / `departments` | `users.org_level_id` / `users.department_id` | 1 → many |
| `clients` | `projects.client_id`, `client_communications.client_id`, `invoices.client_id` | 1 → many |
| `projects` | `project_team`, `project_phases`, `tasks.project_id`, `expenses.project_id`, `site_visits.project_id`, `invoices.project_id` (nullable) | 1 → many |
| `project_phases` | `tasks.phase_id` | 1 → many |
| `users` | `tasks.assigned_to`/`assigned_by`, `leaves.user_id`/`approved_by`, `attendance.user_id`, `payroll_entries.user_id`, `meeting_attendees.user_id`, `notifications.user_id`, `audit_logs.user_id`, `expenses.approved_by` | 1 → many |
| `users` (self) | `users.reporting_to_id`, `tasks.parent_task_id` | tree/self-ref |
| `invoices` | `invoice_items.invoice_id` | 1 → many (cascade delete) |
| `payroll_runs` | `payroll_entries.payroll_run_id` | 1 → many (cascade delete) |

---

## 7. Indexes & integrity

- `ix_users_login_id` **unique** index (plus unique constraint) from `0024`;
  `email`, `department_id`, `org_level_id`, `reporting_to_id`, `is_active`
  also indexed.
- Migration `0012` added performance indexes on hot lookup paths (foreign
  keys, dates, statuses such as `invoices.invoice_date`,
  `tasks.status`); `0011` added secondary indexes and fixed cascades.
- Notable uniqueness: `projects.project_code`, `invoices.invoice_number`,
  `payroll_runs (month, year)`, `payroll_entries (run, user)`,
  `leave_balance (user, type, year)`, `project_team (project, user)`,
  `settings (group, key)`.
- Row Level Security is enabled on all public application tables (`0015`)
  with permissive policies for the backend role.

---

## 8. Data-access rules

- All access goes through async `AsyncSession` provided by
  `app.db.session.get_db` (pool: pre-ping, size 5 / overflow 10; NullPool in tests).
- Cross-module data reads must go through the owning module's service or the
  `app.models` registry — module models may not import each other
  (import-linter contract `model-boundaries`).
- Soft deletes: master-data tables expose `is_active`; services filter and
  callers check `get_or_404(...)` + `is_active`.
- Datetimes: persist UTC; convert to Asia/Kolkata only at the edges
  (`app.utils.shared.utc_now` / `to_local`).
- Financial columns (budget, fees, amounts, salaries) are readable only via
  endpoints guarded for L0/L1 — see ARCHITECTURE.md §3.

---

## 9. Alembic golden rules

1. **Never edit an applied migration.** Generate a new revision instead.
   Precedent: `0021_drop_user_role` originally failed everywhere because it
   explicitly dropped `ix_users_role` after `drop_column` (Postgres already
   removes the index with the column). Since the revision had never applied in
   any environment, it was safe to fix in place — that exception is rare and
   requires verifying the revision has applied nowhere first.
2. Keep the chain linear (`down_revision` points at the previous head);
   current head is `0026_invoice_hsn_sac`.
3. Every schema change ships with working `upgrade()` **and** `downgrade()`.
4. Data backfills belong in migrations when later code depends on them
   (see `0020_backfill_org_levels`, `0024` login-id cohort backfill).
5. Migrations run unattended on container start — they must be idempotent-safe
   and fast; never rely on interactive input.

---

## 10. Seeding

Idempotent seeding runs at startup (`app.db.init_db`) after migrations:

| Seeder | Seeds |
|---|---|
| `seed_org_levels` | L0–L6 rows |
| `seed_departments` | the seven studio departments |
| `seed_settings` | company profile ("Offsitearch") incl. bank name/account, UPI id and default invoice terms rendered onto PDF invoices |
| `seed_holidays` | holiday calendar |
| `seed_superuser` | first superuser from env (`FIRST_SUPERUSER_*`); receives a **cohort `login_id`** allocated via `format_login_id(year, next_sequence)` |
| `seed_leave_balances` | yearly allocations |
| `seed_clients`, `seed_projects` | minimal starter records |

`SEED_DEMO=true` additionally loads the demo dataset (`app/seeds/demo.py`) —
demo staff with generated `YY####` login ids, sample clients/projects/tasks —
intended for staging only.

---

_Last Updated: 2026-08-24_
