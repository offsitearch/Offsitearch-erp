# Offsite ERP — REST API Reference

Human-facing reference for the backend HTTP API. Every router below is mounted under the `/api/v1` prefix (see `backend/app/api/__init__.py`). Interactive OpenAPI/Swagger UI is available at `/docs` **in development only** — it is disabled when the app runs with `ENVIRONMENT=production`.

---

## 1. Conventions

### 1.1 Requests & responses

- All URLs in this document are relative to the base URL `/api/v1`.
- Request and response bodies are JSON (`Content-Type: application/json`) except where an endpoint explicitly takes multipart form data (file uploads) or streams a binary export.
- List responses are paginated envelopes: `{ "items": [...], "total": int, "page": int, "page_size": int }`.

### 1.2 Authentication

- Bearer JWT access tokens: `Authorization: Bearer <access_token>`. Login issues an **access + refresh** pair.
- Access-token claims: `sub` (user id), `type` (`access`), `tvp` (token-version pointer into `users.token_version`). A token whose `tvp` no longer matches the user's current `token_version` is rejected with **401** ("Session invalidated by a password change") — any password event kills every outstanding session.
- 401 responses include `WWW-Authenticate: Bearer`.
- While `user.must_change_password` is `true`, every path outside `/api/v1/auth/*` returns **403** until the password is changed.
- `POST /auth/login` is rate-limited per client IP: **5 failed attempts / 300 s**, then **429** with a `Retry-After` header.

### 1.3 Errors

FastAPI default error shape: `{ "detail": "message" }`.

| Code | Meaning |
|------|---------|
| 400 | Bad request (domain rule violated) |
| 401 | Missing/invalid/stale token (includes `WWW-Authenticate: Bearer`) |
| 403 | Insufficient level, financial-field violation, or pending password change |
| 404 | Not found (also used to hide resources the caller may not see) |
| 409 | Conflict (duplicate, non-empty department, etc.) |
| 422 | Validation error (FastAPI/pydantic shape) |
| 429 | Login rate limit exceeded (`Retry-After` header) |

### 1.4 Org levels & access shorthand

Users carry an organizational level `L0`–`L6`. Levels describe seniority; authorization is enforced by dependency gates. In the tables below:

| Shorthand | Enforced by | Meaning |
|-----------|-------------|---------|
| `public` | — | No authentication required |
| `auth` | `get_current_user` | Any authenticated user |
| `L3+`, `L2+`, `L1+` | `require_min_level("Ln")` | Caller's level must be `Ln` or more senior (e.g. `L2+` admits L0, L1, L2) |
| `L0/L1 (financial)` | `require_financial_access()` | Executive band only — see §1.5 |

`L0` (CEO) is the most senior level; `L6` is the most junior. Users without an assigned level are always rejected by level gates. The self-service "staff band" (roughly L4–L6) additionally gets record-level scoping on projects/tasks/site-visits: they see only what they lead, are assigned to, or are a team member of.

### 1.5 Financial isolation policy

Any figure denominated in rupees is executive-only (**L0/L1**):

- Whole endpoints that expose money (finance overview, invoices, expenses admin, payroll, salary, financial reports and their exports, backups) sit behind `require_financial_access()`.
- Mixed endpoints **redact** money fields below L1 instead of failing: project `budget`/`studio_fee`/`fee_type`/`fee_percent`, client `budget_range` and profile `financial_summary` rupee keys, dashboard `revenue_this_month` are omitted/nulled in responses.
- **Writing** a money field without financial access returns **403** ("Financial fields require executive access").
- Department/designation/any other attribute never grants financial access.

### 1.6 Exports

Endpoints accepting `?format=json|csv|xlsx` stream the payload with the correct MIME type: `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; PDF downloads use `application/pdf`; binary attachments use `application/octet-stream` / `application/gzip` with `Content-Disposition: attachment`.

---

## 2. System

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/system/health` | public | DB round-trip check. Extra build/disk details dev-only (omitted in production) |
| GET | `/system/ready` | public | Liveness/readiness probe |
| GET | `/rate-limit/stats` | L2+ | Login rate-limit usage counters |

---

## 3. Auth

Login is by **6-digit user ID** (`login_id`, format `YY####`) — email is not a login key.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| POST | `/auth/login` | public | Body `{"user_id": "<6-digit>", "password": "..."}` → `{access_token, refresh_token, token_type, user}`. Rate-limited (§1.2). Example below |
| POST | `/auth/refresh` | public | Body `{"refresh_token": "..."}` → rotated token pair + user. Rejects refresh tokens invalidated by a password change |
| POST | `/auth/logout` | auth* | Body `{"refresh_token": "..."}` → revokes that refresh token |
| GET | `/auth/me` | auth | Current user profile (includes `login_id`, `must_change_password`) |
| POST | `/auth/change-password` | auth | Body `{"current_password", "new_password"}`. Verifies current password, clears `must_change_password`, bumps `token_version` (old access tokens die) and revokes refresh tokens → returns a **fresh token pair** |

\* Logout accepts any valid request; it is reachable even during a forced password change because it lives under `/auth/*`.

```jsonc
// POST /api/v1/auth/login — request
{ "user_id": "260001", "password": "482913" }
```

```jsonc
// 200 OK — response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "login_id": "260001",
    "name": "Aarav Mehta",
    "email": "aarav.mehta.26@offsitearch.in",
    "org_level_code": "L1",
    "must_change_password": false
  }
}
```

---

## 4. Users (account administration)

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/users` | L3+ | Query: `department_id`, `active_only` (default true). Brief directory rows |
| POST | `/users` | L1+ | Creates an account; system email + numeric password auto-generated, `generated_password` returned **once**; `must_change_password` starts true |
| PATCH | `/users/{id}` | L1+ | Partial update. Sending `password` resets it: sets `must_change_password`, bumps `token_version`, revokes refresh tokens |
| POST | `/users/{id}/regenerate-password` | L1+ | One-time password recovery. Not allowed on yourself or equal-or-senior users (403). Returns `{login_id, name, generated_password}` exactly once (example below) |

> `GET /users/{id}/credentials` was **removed** — generated passwords are shown once at creation/reset and never stored or re-displayed.

Profile-level edits with seniority guardrails live under `/employees` (§8): creators can only assign org levels strictly below their own and cannot edit equal-or-senior colleagues; activation/deactivation is executive-only.

```jsonc
// POST /api/v1/users/42/regenerate-password — 200 OK
{
  "login_id": "260042",
  "name": "Diya Kapoor",
  "generated_password": "483920"
}
```

---

## 5. Dashboard

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/dashboard/summary` | auth | KPI counts. Level-aware: staff band scoped to own projects/tasks; `revenue_this_month` is `null` below L1 |

---

## 6. Attendance

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| POST | `/attendance/check-in` | auth | Clock in (own record) |
| POST | `/attendance/check-out` | auth | Clock out |
| GET | `/attendance/me` | auth | Own monthly summary; `month`/`year` optional |
| GET | `/attendance/today` | L3+ | Roster rows for today; `department_id`, `status` filters |
| GET | `/attendance/date/{date}` | L3+ | Same roster for an arbitrary date |
| GET | `/attendance/employee/{user_id}` | L3+ | Monthly summary for one employee |
| GET | `/attendance/holidays` | auth | Convenience holiday list for a year (see also §16) |
| POST | `/attendance/bulk` | L2+ | Bulk mark entries for a date |
| PATCH | `/attendance/{record_id}` | L2+ | Correct a single record |
| GET | `/attendance/report?from_date=&to_date=` | L3+ | Optional `department_id`, `format=json|csv|xlsx` (CSV/XLSX streamed with proper MIME) |

---

## 7. Leaves

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/leaves/balance` | auth | Own yearly balances |
| GET | `/leaves/mine` | auth | Own requests (paginated) |
| POST | `/leaves` | auth | Apply |
| PATCH | `/leaves/{leave_id}` | auth | Cancel own pending request |
| GET | `/leaves/pending` | L3+ | Approval queue |
| POST | `/leaves/{leave_id}/approve` | L3+ | Approve; notifies + emails requester |
| POST | `/leaves/{leave_id}/reject` | L3+ | Body `{"reason": "..."}`; notifies + emails requester |
| GET | `/leaves/team-availability?from_date=&to_date=` | L3+ | Who is off in a window |

---

## 8. Employees

Directory page is management-band; individual profile reads/writes fall back to strict self-service below L3. Salary is financial-only.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/employees` | L3+ | Search/filter by `search`, `department_id`, `org_level_id`, `skill`, active flags |
| GET | `/employees/skills` | L3+ | Distinct skill tags |
| GET | `/employees/designations` | L3+ | Catalog `{org_level_code: [titles]}` |
| GET | `/employees/department-designations` | L3+ | Catalog `{department: [titles]}` |
| GET | `/employees/org-chart` | auth | Reporting tree |
| POST | `/employees` | L2+ | Onboard employee (creates account); can only assign org levels **strictly below own**; `generated_password` returned once |
| GET | `/employees/{user_id}` | auth | Profile — self, or L3+ (403 otherwise) |
| PATCH | `/employees/{user_id}` | auth | Self-service basics, full edit for L3+; cannot edit seniors; `is_active` changes and assigning `L1` require L1+ |
| DELETE | `/employees/{user_id}` | L1+ | Deactivate/remove |
| GET | `/employees/{user_id}/attendance-summary` | L2+ | Aggregated attendance |
| GET | `/employees/{user_id}/salary` | L0/L1 (financial) | Salary detail |
| PUT | `/employees/{user_id}/salary` | L0/L1 (financial) | Update salary |
| GET | `/employees/{user_id}/documents` | auth | Own documents, or L3+ for others |
| POST | `/employees/{user_id}/documents` | L2+ | Multipart `file` (+ `doc_type` query) |
| GET | `/employees/{user_id}/documents/{doc_id}/download` | auth | Self, or L3+ for others |
| DELETE | `/employees/{user_id}/documents/{doc_id}` | L2+ | Remove document |
| GET | `/employees/{user_id}/leaves` | L3+ | Leave history of one employee |

---

## 9. Org structure

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/departments` | auth | Tree/list of departments |
| POST | `/departments` | L1+ | Create (unique name, optional parent) |
| PATCH | `/departments/{id}` | L1+ | Rename/re-parent |
| DELETE | `/departments/{id}` | L1+ | 409 if employees or sub-departments still attached |
| GET | `/org-levels` | auth | Level catalog |
| POST | `/org-levels` | L1+ | Add a level (unique code) |
| PATCH | `/org-levels/{level_id}` | L1+ | Edit name/rank/description. The `L0` CEO row is managed by seed data |

---

## 10. Projects

Money fields (`budget`, `studio_fee`, `fee_type`, `fee_percent` on phases) are omitted below L1; writing them without financial access → 403 (§1.5).

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/projects/templates` | auth | Phase templates |
| GET | `/projects` | auth | Filters: `search`, `project_type`, `status`, `client_id`, `lead_id`. Staff band scoped to own projects |
| POST | `/projects` | L3+ | Server forces `status=draft`; sub-L2 creators become the project lead automatically |
| GET | `/projects/{id}` | auth | Staff band only sees projects they belong to |
| PATCH | `/projects/{id}` | manage\* | \*L1/L2 manage any project; otherwise only its assigned lead. Reassigning the lead requires L2+ |
| DELETE | `/projects/{id}` | L1+ | Soft delete |
| POST | `/projects/{id}/team` | manage\* | Body `{"user_id", "role"}` |
| DELETE | `/projects/{id}/team/{user_id}` | manage\* | Remove member |
| GET | `/projects/{id}/timeline` | auth | Milestones/phases timeline (staff scoped) |
| POST | `/projects/{id}/phases` | manage\* | Phase create; `studio_fee` is a financial field |
| PATCH | `/projects/{id}/phases/{phase_id}` | manage\* | Phase update |
| DELETE | `/projects/{id}/phases/{phase_id}` | manage\* | Phase delete |

> The old kanban view `GET /projects/{id}/board` was **removed** — the task board lives at `GET /tasks/board` (§12).

---

## 11. Clients

List/detail/create/edit are gated at L3+. `budget_range` is a deal value: omitted below L1, writes by non-executives → 403. `deal_stage` and GST fields stay visible to operations.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/clients` | L3+ | `search`, `client_type`, paginated |
| POST | `/clients` | L3+ | Create; `budget_range` accepted only from L0/L1 |
| GET | `/clients/{id}` | L3+ | Profile incl. communications summary; `financial_summary` rupee keys nulled below L1 |
| PATCH | `/clients/{id}` | L3+ | Update; same budget guard |
| DELETE | `/clients/{id}` | L1+ | Soft delete |
| GET | `/clients/{id}/communications` | L3+ | Contact history |
| POST | `/clients/{id}/communications` | L3+ | Log a communication |

---

## 12. Tasks

Board CRUD is open to authenticated users with record-level scoping; assignment fires a notification to the assignee.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/tasks/board` | auth | Kanban board; optional `project_id` filter (staff band must be a member) |
| GET | `/tasks` | auth | Filters: `search`, `project_id`, `assignee`, `status` |
| POST | `/tasks` | auth | Below L2 only within projects you lead |
| GET | `/tasks/{id}` | auth | Visible to L3+, assignee, or same-project members |
| PATCH | `/tasks/{id}` | auth | Assignee, creator, L2+, or project lead; reassignment needs L3+/lead |
| DELETE | `/tasks/{id}` | auth | L2+ or project lead |
| POST | `/tasks/{task_id}/checklist` | auth | Add checklist item (visible tasks only) |
| PATCH | `/tasks/{task_id}/checklist/{item_id}` | auth | Toggle checklist item |

---

## 13. Finance overview

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/finance/overview` | L0/L1 (financial) | Summary; `period=month|quarter|year|all`, `compare=bool` |
| GET | `/finance/my-expenses` | auth | Own expense claims (matched by name) |
| POST | `/finance/my-expenses` | auth | Submit own claim (JSON; `paid_by` forced to caller) |

---

## 14. Invoices

Entire module is **L0/L1 (financial)**. Line-item `amount` is always recomputed server-side as `quantity × rate` — client-supplied amounts are ignored. `hsn_sac` is optional per line item (≤ 20 chars). Sending blocks line descriptions shorter than 3 characters (client-facing safeguard) and emails the client when mail is enabled. Payment recording drives status `draft → sent → partial/paid`. The PDF renders CGST/SGST lines when the studio and client GSTIN share a state code (first two digits), otherwise a single IGST line; company identity/GSTIN/bank/UPI come from the seeded company profile.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/invoices` | L0/L1 (financial) | `status`, `client_id`, `search`, paginated |
| POST | `/invoices` | L0/L1 (financial) | Create (example below) |
| GET | `/invoices/{invoice_id}` | L0/L1 (financial) | Detail with items |
| PATCH | `/invoices/{invoice_id}` | L0/L1 (financial) | Update header/items |
| POST | `/invoices/{invoice_id}/send` | L0/L1 (financial) | Mark sent (+ email) |
| POST | `/invoices/{invoice_id}/payment` | L0/L1 (financial) | Body `{"amount": >0, "method": "bank_transfer", "payment_date"?}` |
| GET | `/invoices/{invoice_id}/pdf` | L0/L1 (financial) | Tax invoice PDF with GST breakup |

```jsonc
// POST /api/v1/invoices — request
{
  "client_id": 7,
  "project_id": 3,
  "invoice_date": "2026-08-24",
  "due_date": "2026-09-23",
  "tax_percent": 18,
  "items": [
    { "description": "Schematic design phase", "hsn_sac": "993321", "quantity": 1, "rate": 450000 },
    { "description": "Site supervision visit", "quantity": 4, "rate": 12500 }
  ],
  "notes": "Payable within 30 days"
}
```

```jsonc
// 201 Created — response (abridged)
{
  "id": 58,
  "invoice_number": "OFF/2026/0058",
  "subtotal": 500000,
  "tax_percent": 18,
  "tax_amount": 90000,
  "total": 590000,
  "status": "draft",
  "items": [
    { "description": "Schematic design phase", "hsn_sac": "993321", "quantity": 1, "rate": 450000, "amount": 450000 },
    { "description": "Site supervision visit", "hsn_sac": null, "quantity": 4, "rate": 12500, "amount": 50000 }
  ]
}
```

---

## 15. Expenses

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/expenses` | L0/L1 (financial) | Filters: `category`, `project_id`, `status`, `month`, `year` |
| POST | `/expenses` | L0/L1 (financial) | Multipart form: `category`, `amount`, optional `description`, `expense_date`, `project_id`, `paid_by`, receipt `file` |
| PATCH | `/expenses/{expense_id}/approve` | L0/L1 (financial) | Body `{"approve": true|false}` — approve/reject decision |
| GET | `/expenses/{expense_id}/receipt` | L0/L1 (financial) | Download stored receipt |

(Individual users submit their own claims via `/finance/my-expenses`, §13.)

---

## 16. Payroll

All endpoints **L0/L1 (financial)**.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/payroll?month=&year=` | L0/L1 (financial) | Run state for a period (defaults to current month) |
| POST | `/payroll/process` | L0/L1 (financial) | Body `{"month": 8, "year": 2026}` — compute/process the run |
| GET | `/payroll/{month}/{year}/payslips/{user_id}` | L0/L1 (financial) | Payslip PDF download |

---

## 17. Settings

Flat key-value store (`group`/`key`/`value` rows). The company profile (Offsitearch legal name, address, GSTIN, bank account, UPI) is seeded at boot and is what invoice PDFs print.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/settings` | L2+ | Optional `?group=` filter |
| PUT | `/settings` | L2+ | Upsert a **list** of `{"group", "key", "value"}` rows |
| DELETE | `/settings/{group}/{key}` | L2+ | Delete one setting |

---

## 18. Holidays

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/holidays` | L2+ | `?year=` (defaults to current year) |
| POST | `/holidays` | L2+ | Create |
| PATCH | `/holidays/{holiday_id}` | L2+ | Update |
| DELETE | `/holidays/{holiday_id}` | L2+ | Delete |

(Everyone else reads the year's holidays through `GET /attendance/holidays`, §6.)

---

## 19. Notices

Importance is `low|medium|high`; notices support pinning and publish/expiry windows. Below L2 only currently-published notices are visible.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/notices` | auth | Paginated; L2+ may pass `include_inactive=true` |
| POST | `/notices` | L2+ | Create (`importance`, `is_pinned`, publish/expiry fields) |
| PATCH | `/notices/{notice_id}` | L2+ | Update/edit |
| DELETE | `/notices/{notice_id}` | L2+ | Soft delete |

---

## 20. Meetings

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/meetings` | auth | L3+ see all; others see meetings they organize/attend |
| POST | `/meetings` | L3+ | Create with attendees |
| PATCH | `/meetings/{meeting_id}` | organizer-or-L2+ | Update (route gate L3+) |
| DELETE | `/meetings/{meeting_id}` | organizer-or-L2+ | Delete (route gate L3+) |
| POST | `/meetings/{meeting_id}/rsvp?rsvp_status=accepted|declined` | auth attendee | Record your RSVP |

---

## 21. Notifications

Own inbox only; other users' rows 404.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/notifications` | auth | Paginated inbox |
| GET | `/notifications/unread-count` | auth | `{"count": int}` |
| PATCH | `/notifications/{notification_id}/read` | auth | Mark one read |
| POST | `/notifications/read-all` | auth | Mark all read |
| DELETE | `/notifications/{notification_id}` | auth | Delete one |

---

## 22. Site visits

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/site-visits` | auth | L2+ see all; leads/members see led or joined projects' visits |
| POST | `/site-visits` | lead+ | L2+ anywhere; below that only the project lead of an active project |
| GET | `/site-visits/{visit_id}` | auth | Viewer-guarded |
| PATCH | `/site-visits/{visit_id}` | organizer-or-L2+ | Update |
| DELETE | `/site-visits/{visit_id}` | organizer-or-L2+ | Delete |
| POST | `/site-visits/{visit_id}/photos` | organizer-or-L2+ | Multipart `file` + optional `caption` (images only) |
| GET | `/site-visits/{visit_id}/photos/{photo_id}` | auth | Photo download |
| GET | `/site-visits/{visit_id}/report` | auth | Visit report PDF |

---

## 23. Audit logs

Written automatically by every module; read-only API. All endpoints L2+.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/audit-logs` | L2+ | Filters: `user_id`, `entity_type`, `action`, `from_date`, `to_date` |
| GET | `/audit-logs/count` | L2+ | Optional `entity_type` filter |
| GET | `/audit-logs/export` | L2+ | CSV stream (last 5 000 rows), same filters |

---

## 24. Reports

All report endpoints accept `format=json|csv|xlsx` (exports stream with correct MIME). The projects and finance reports are entirely financial — including their exports — hence executive-only.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/reports/projects?status=&project_type=&format=` | L0/L1 (financial) | Per-project budget/fee/expenses/hours |
| GET | `/reports/finance?period=month|quarter|year|all&format=` | L0/L1 (financial) | Invoiced/paid/outstanding |
| GET | `/reports/hr?month=&year=&format=` | L2+ | Headcount/attendance/leave (no money columns) |

Attendance reporting lives separately at `GET /attendance/report` (§6, L3+).

---

## 25. Backup

Whole router is **L1+** (`require_min_level("L1")`) — dumps contain every table, salaries included. Backups go to Google Drive (OAuth) and/or direct download.

| Method | Path | Access | Notes |
|--------|------|--------|-------|
| GET | `/backup/status` | L1+ | Config + connection + last-run snapshot |
| GET | `/backup/history?limit=` | L1+ | Recent runs (limit 1–100, default 20) |
| POST | `/backup/run` | L1+ | Trigger a manual backup; 502 with error detail on failure |
| PUT | `/backup/schedule` | L1+ | Body `{"auto_enabled": bool, "frequency": "daily"\|"weekly"}` |
| GET | `/backup/google/connect` | L1+ | Redirects the **browser** to Google consent (call with credentials, follow redirect) |
| GET | `/backup/google/callback` | public | Google redirects here; HMAC-signed `state` is mandatory, exchanges the code, then bounces to the settings page with `&drive=connected|error|not_configured` |
| POST | `/backup/google/disconnect` | L1+ | Drop stored Drive tokens |
| GET | `/backup/download` | L1+ | Fresh dump streamed as `application/gzip` (`studioerp-backup-<stamp>.json.gz`); works without Drive configured |

---

## 26. Removed & never-existing modules

Do not build against these — they will 404:

- **Vendors (`/vendors`)** — module deleted **2026-08-24** (tables remain orphaned in the database). Procurement records now live under expenses.
- **Documents / DMS** — never existed as an HTTP API (schema-only historically). Employee documents are served by `/employees/{user_id}/documents` (§8).
- **`GET /users/{id}/credentials`** — removed; use `POST /users/{id}/regenerate-password` (one-time response).
- **`GET /projects/{id}/board`** — removed; the kanban board is `GET /tasks/board`.
- **`/auth/forgot-password`, `/auth/reset-password`** — no email-reset flow exists; executives issue one-time passwords instead.

---

_Last Updated: 2026-08-24_
