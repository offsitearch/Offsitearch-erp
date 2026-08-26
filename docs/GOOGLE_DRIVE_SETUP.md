# Google Drive Backup — Setup Guide

One-time setup that enables **Settings → Backup → Connect Google Drive**.
Backups upload to a private "StudioERP Backups" folder in the connected
account's Drive. The app only ever sees files it created itself
(`drive.file` scope).

---

## 1. Create the Google Cloud project

1. Go to <https://console.cloud.google.com/> and sign in with the account
   that should own the backups (usually the studio's admin Gmail).
2. Top bar → project dropdown → **New project** → name it e.g. `StudioERP`
   → **Create** → select it.

## 2. Enable the Google Drive API

1. Menu → **APIs & Services → Library**.
2. Search **Google Drive API** → open it → **Enable**.

## 3. Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. User type: **External** (personal Gmail) or **Internal** (Google
   Workspace org) → **Create**.
3. Fill in:
   - App name: `StudioERP`
   - User support email: your email
   - Developer contact email: your email
4. Scopes step → nothing needed manually; scopes are requested at runtime:
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/userinfo.email`
5. **Test users** step → add every Gmail address that will click
   *Connect Google Drive* (required while the app is in *Testing* mode).
6. Save. You may leave the app in *Testing* — refresh tokens still work;
   only re-consent is needed after 7 days *only if* using a sensitive
   scope (`drive.file` is not, so tokens persist).

## 4. Create the OAuth client

1. **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Web application**.
3. Name: `StudioERP Backend`.
4. **Authorized redirect URIs** → add one per environment, exactly:

   | Environment | Redirect URI |
   |---|---|
   | Local dev | `http://localhost:8000/api/v1/backup/google/callback` |
   | Production | `https://<your-backend-host>/api/v1/backup/google/callback` |

5. **Create** → copy the **Client ID** and **Client Secret**.

## 5. Set environment variables

Local dev — `.env` in the repo root:

```env
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/backup/google/callback
BACKUP_UI_REDIRECT=http://localhost:5173/settings?tab=backup
```

Production (Render dashboard → `studio-erp-api` → Environment):

```env
GOOGLE_CLIENT_ID=<same client id>
GOOGLE_CLIENT_SECRET=<same secret>
GOOGLE_REDIRECT_URI=https://<backend-host>/api/v1/backup/google/callback
BACKUP_UI_REDIRECT=https://<frontend-host>/settings?tab=backup
```

> `GOOGLE_REDIRECT_URI` and `BACKUP_UI_REDIRECT` must match the deployed
> URLs exactly (scheme + host, no trailing slash). The redirect URI must
> also be registered verbatim on the OAuth client from step 4.

Restart/redeploy the backend after changing these.

## 6. Connect

Log in as an executive (L0/L1) → **Settings → Backup tab → Connect Google
Drive** → approve the consent screen. The button turns green showing the
connected account, and a **StudioERP Backups** folder appears in that
Drive. Manual and scheduled backups now upload there automatically
(older files are pruned past the newest 30).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Toast: *"Backend Google credentials are not set up yet"* | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` missing or backend not restarted |
| Google error `redirect_uri_mismatch` | URI in Console ≠ `GOOGLE_REDIRECT_URI`; compare character-for-character |
| Google error `access_blocked` | Account not added as a **Test user** while the consent app is in Testing |
| `drive=error` after consent | Check backend logs for `Google Drive token exchange failed`; verify system clock is accurate |
| Connection lost later | `SECRET_KEY` changed — tokens are encrypted with it and can no longer be decrypted; reconnect once |
