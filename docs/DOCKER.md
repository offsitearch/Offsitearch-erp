# 🐳 StudioERP Docker Setup

Dev and production stacks, plus Dockerfiles and troubleshooting.

---

## 1. Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Compose v2 (Linux)
- At least 4 GB free RAM for the stack

---

## 2. Quick Start (Development)

```bash
copy .env.example .env      # Windows PowerShell
# or: cp .env.example .env  # Linux/macOS

docker compose up --build
```

What comes up:

| Service  | Image / Build          | URL |
|----------|------------------------|-----|
| `db`     | `postgres:16-alpine`   | localhost:5432 |
| `backend`| `./backend/Dockerfile` | localhost:8000 (+ /docs) |
| `frontend`| `./frontend/Dockerfile`| localhost:5173 |

The backend container:
1. waits for `db` to be healthy,
2. runs `alembic upgrade head`,
3. starts `uvicorn --reload`.

Frontend runs Vite dev server with HMR. Source directories are bind-mounted for live reload in both containers.

```bash
# Useful commands
docker compose logs -f backend     # watch backend logs
docker compose exec backend alembic revision --autogenerate -m "message"
docker compose exec backend alembic upgrade head
docker compose exec db psql -U studio -d studio_erp   # psql shell
docker compose down                # stop (keeps data)
docker compose down -v             # stop + wipe db volume (fresh start)
```

---

## 3. Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

| Service  | Behavior |
|----------|----------|
| `db`     | Postgres with a named volume (persistent) |
| `backend`| `alembic upgrade head` then uvicorn (no reload) |
| `frontend`| Builds the React app, serves it from **Nginx**, which also reverse-proxies `/api` → backend |

Production URLs: `http://localhost` (Nginx) → static React + `/api/*` proxied to FastAPI.

**Before deploying anywhere real:**
- Change `SECRET_KEY` and `POSTGRES_PASSWORD` to strong random values
- Set `ENVIRONMENT=production`, `DEBUG=false`
- Put a reverse proxy (Caddy/Traefik/cloud LB) in front for TLS

---

## 4. Dockerfiles

### backend/Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first (layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# App source
COPY . .

# Run migrations, then serve
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### frontend/Dockerfile (multi-stage)

```dockerfile
# ---- build stage ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- serve stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### frontend/nginx.conf (prod)

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 200M;
    }

    # Uploaded files served by backend itself
    location /uploads/ {
        proxy_pass http://backend:8000;
    }
}
```

---

## 5. docker-compose.yml (dev)

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: ./backend
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - ./backend/app:/app/app          # live reload
      - uploads:/app/uploads            # uploaded files
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    restart: unless-stopped
    environment:
      VITE_API_BASE_URL: /api/v1
    ports:
      - "${FRONTEND_PORT:-5173}:5173"
    volumes:
      - ./frontend/src:/app/src         # HMR
    depends_on:
      - backend
    # dev override (see comment below): command: ["npm", "run", "dev", "--", "--host"]
```

> For dev hot-reload, the frontend command is `npm run dev -- --host`. Production builds with `npm run build`. If your Dockerfile's default CMD is the production serve, override in a `docker-compose.dev.yml` or set the CMD directly in the image for dev.

---

## 6. docker-compose.prod.yml (production)

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: ./backend
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      ENVIRONMENT: production
    volumes:
      - uploads:/app/uploads
    expose:
      - "8000"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  pgdata:
  uploads:
```

---

## 7. .env.example

See [TECH_STACK.md → §5](./TECH_STACK.md) for the full variable list. **Never commit real secrets.**

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Backend won't start, `connection refused` on db | DB not healthy yet — wait; check `docker compose logs db` |
| Alembic fails on fresh clone | Delete the volume: `docker compose down -v`, then `up` |
| Frontend can't reach API | Vite proxy target must be `http://backend:8000` inside Docker; `http://localhost:8000` when run locally without Docker |
| Uploads disappear after `down` | Uploads live in the `uploads` volume — do not use `-v` if you want them kept |
| Port 80 in use (prod) | Change `"80:80"` to `"8080:80"` and visit localhost:8080 |
| `docker compose` not found | Use `docker-compose` (v1) or install Compose v2 plugin |
| Windows: bind-mount watch errors | Add `"watch": true` on volumes, or use WSL2 backend in Docker Desktop |
| Build fails on npm ci | Delete `frontend/package-lock.json` mismatch → run `npm install` locally to regenerate, commit it |

---

## 9. Backups

### 9.1 Built-in app backups (recommended)

The app ships a **Google Drive backup module** (Settings → Backup, L0/L1 users only):

- One-click OAuth connect (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` env vars required — see `.env.example`)
- Manual "Back up now" or auto daily/weekly schedule; full-DB JSON dump gzipped to a "StudioERP Backups" Drive folder
- 30-file retention pruned automatically; history visible in-app
- Zero-setup fallback: "Download backup file (.json.gz)" from the same tab

Tokens are encrypted at rest with a key derived from `SECRET_KEY` — rotating the secret requires reconnecting Drive.

### 9.2 Classic pg_dump (belt-and-braces)

```bash
# Dump database to a file
docker compose exec db pg_dump -U studio studio_erp > backup_$(date +%F).sql

# Restore
docker compose exec -T db psql -U studio studio_erp < backup_2026-08-14.sql
```

Schedule with a cron/Task Scheduler job for off-box copies. The `uploads/` volume should be backed up separately (or moved to object storage).
