> **STATUS (2026-08-24): AS-BUILT GRAPH OF THE OLD LAYERED TREE.** Import edges, fan-in table and
> cycles C1/C2 describe the pre-modularization codebase (C1 seeds↔project_service was resolved by
> the wave extractions; vendors edges are gone — module deleted). For the current enforced
> boundaries see `backend/.importlinter` and `_ai_context/MODULE_BOUNDARIES.md`.

# OFFSITE ERP — Dependency Graph (as-built)

> Derived from actual imports, SQLAlchemy relationships and service calls.
> Every edge cites evidence. Companion: `architecture_inventory.md`.

Legend:
`→` imports/calls · `⇢` DB relationship (FK) · `⇉` cross-domain **write** ·
`(p)` private-symbol import · `(s)` route-layer raw query bypassing services

---

## 1. Module-level import graph (backend)

```text
                        ┌──────────────────────────────────────────────┐
                        │                CORE / INFRA                  │
                        │  config · db · security · storage · middleware│
                        │  enums · errors · state_machines · shared     │
                        │  email_service · audit_service · notification │
                        └──────────────────────────────────────────────┘
                                            ↑ (all modules)

 identity(auth,users) ──→ audit, email
 employees ──→ Attendance(model) · Department · OrgLevel · SalaryComponent · User
              ──→ email(welcome) · audit · leave_service (route /employees/{id}/leaves)
 attendance ──→ Setting · Department(join) · User · seeds.data ATTENDANCE_SETTINGS
 attendance.route ──(p)→ reports_service._attendance_sheets
 leave ──⇉→ Attendance (INSERT on approve) · Holiday(read) · Setting · Department(join)
        ──→ seeds.data LEAVE_SETTINGS · email(leave status) · notify
 holidays ──→ audit          [no service; raw queries in route]
 projects ──→ Client(validate) · Task(board read) · User · seeds.data PROJECT_TYPE_TEMPLATES
 tasks ──→ Project(validate/board) · User · notify · audit
 clients ──→ Project(profile aggregate) · Invoice(profile aggregate) · User
 site_visits ──→ project_service(validate) · Project · User · storage · pdf
 finance ──→ Client(validate/join) · Project(validate/join) · User · email(invoice)
 reports ──→ Attendance · Client · Department · Expense · Invoice · Leave · Project · User
         ──(p)→ finance_service._period_bounds / _status_for
 dashboard(s) ──→ Attendance · Invoice · Project · Task · User   (+project_service.scope_condition)
 payroll ──→ Attendance(read) · Holiday(read) · SalaryComponent · Department(join) · User
 vendors ──→ Project(link validation)
 meetings ──→ User · notify
 notices ──→ User
 notifications ──→ User
 settings ──→ Setting only
 system/audit_logs/rate_limit(s) ──→ AuditLog · User
```

## 2. Reverse-dependency (fan-in) view — "who breaks if X changes"

```text
User / identity        ← EVERY module (FK + get_current_user + role enums)
Department             ← employees, users route, attendance, leave, payroll, reports (name joins)
Setting                ← settings, attendance, leave (+ frontend SettingsPage)
Holiday                ← holidays, leave, payroll, attendance UI
Attendance             ← attendance, leave(WRITE), employees(summary), payroll, reports, dashboard
Project                ← projects, tasks, clients, site_visits, finance, vendors, dashboard, reports
Client                 ← clients, projects(FK), finance(joins), reports
Invoice/Expense        ← finance, client profile, reports, dashboard(revenue sum)
notify()               ← tasks, leaves, meetings
log_audit()            ← ~15 route modules
finance_service privates ← reports_service
reports_service privates ← attendance route
seeds.data constants   ← attendance, leave, projects services  ⟲ circular with project_service
```

## 3. Database ownership & FK map

```text
users ──⇢ departments.id, org_levels.id, users.id (reporting_to)
refresh_tokens ──⇢ users
employee_documents ──⇢ users            salary_components ──⇢ users
attendance ──⇢ users                    leaves ──⇢ users (user_id, approved_by)
leave_balances ──⇢ users
projects ──⇢ clients.id, users.id (lead)
project_team ──⇢ projects, users        project_phases ──⇢ projects
tasks ──⇢ projects, project_phases, users
task_checklist ──⇢ tasks
client_communications ──⇢ clients, users
site_visits ──⇢ projects, users         site_visit_photos ──⇢ site_visits, users
invoices ──⇢ clients, users(created_by) invoice_items ──⇢ invoices
expenses ──⇢ projects, users(approved_by)
payroll_runs ──⇢ users(processed_by)    payroll_entries ──⇢ payroll_runs, users
vendors ⇄ vendor_projects ⇄ projects
meetings ──⇢ users(organizer)           meeting_attendees ──⇢ meetings, users
notices ──⇢ users    notifications ──⇢ users    audit_logs ──⇢ users(actor, nullable)
```

No cross-schema tricks exist today: **all tables live in one flat schema**, so table
ownership is purely a code-organization concern (good — extraction needs no data migration).

## 4. Circular dependencies

| Cycle | Path | How it is currently masked |
|---|---|---|
| C1 | `app.seeds.data` → `app.services.project_service` (`_compute_progress`, `next_project_code`) **and** `project_service` → `app.seeds.data` (`PROJECT_TYPE_TEMPLATES`) | function-local import at seeds/data.py:369 |
| C2 (latent) | `attendance_service` / `leave_service` → `seeds.data` defaults; any future seed code importing those services would close the loop | one-directional today |

Related structural cycle (module level, not import level):
`Leave ⇒ writes ⇒ Attendance` while `Employees reads Attendance` and
`Payroll reads Attendance+Salary(HR-owned)` — a write-cycle across HR/Attendance/Leave/Payroll
that must be broken with contracts (see `module_boundaries.md` §4).

## 5. Hidden dependencies (not visible from folder names)

1. **Settings is runtime infra for 3 modules** — attendance/leave merge DB rows over seed defaults; changing `settings` storage format silently alters attendance policy behavior.
2. **Seeds are runtime config** — `ATTENDANCE_SETTINGS`, `LEAVE_SETTINGS`, `PROJECT_TYPE_TEMPLATES` are used by production services, not just seeding.
3. **Dashboard revenue field** is part of the auth API client contract on the frontend (`api/auth.ts` calls `/dashboard/summary`).
4. **`/attendance/holidays` endpoint proxies the Holiday table** — attendance frontend depends on holidays domain without knowing it.
5. **`/employees/{id}/leaves`** — Employees route calls leave_service directly (employees.py:29).
6. **`scope_condition` / `user_in_project` / `user_project_ids`** from project_service are public-by-accident APIs consumed by dashboard/tasks/site_visits.
7. **Frontend `employees.ts` api client bundles departments CRUD + employee leaves** — mirrors backend's blurred HR boundary.

## 6. Frontend dependency summary

Already feature-oriented (`src/features/<domain>/` + `src/api/<domain>.ts`). Cross-domain usage found:

| Consumer | Reaches into |
|---|---|
| DashboardPageNew | 8 api modules (attendance, auth, clients, finance, leave, notices, projects, tasks) |
| AttendanceCalendarPage | employees api (departments list) |
| SettingsPage | settings + users + holidays + auth(change-password, regenerate-password) |
| api/auth.ts | `/dashboard/summary` |
| api/employees.ts | departments CRUD, `/employees/{id}/leaves` (the `/users/{id}/credentials` view was removed in the auth rewrite) |
| lib/constants.ts | central role/status metadata (mirrors backend enums) |

These are aggregation-page concerns (dashboards/settings legitimately span domains);
they map cleanly onto the proposed backend contracts rather than requiring a rewrite.

## 7. Allowed vs forbidden dependencies (target state, per module)

Example (full matrix in `module_boundaries.md`):

```text
attendance  ✓ may call EmployeeDirectory.read (contract), SettingsPort.get(group)
            ✗ must not import app.models.user / app.models.department directly
            ✗ must not be imported by leave for writes — leave calls AttendanceWriter(contract)
leave       ✓ AttendanceWriter.mark_on_leave(...) contract
            ✗ no direct Attendance model import
reports     ✓ read-model contracts per domain (or owned read replicas of queries)
            ✗ no private _helpers from other services
dashboard   ✓ per-module summary providers (contract)
            ✗ no raw multi-model queries in route layer
```
