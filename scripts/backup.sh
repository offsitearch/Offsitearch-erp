#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAILY=7
RETENTION_WEEKLY=4

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DOW=$(date +%u)  # 1=Monday .. 7=Sunday
FILENAME="backup_${TIMESTAMP}.sql.gz"
WEEKLY_FLAG=""

# Mark weekly backups (Sunday)
if [ "$DOW" -eq 7 ]; then
    WEEKLY_FLAG=".weekly"
    FILENAME="backup_weekly_${TIMESTAMP}.sql.gz"
fi

FILEPATH="${BACKUP_DIR}/${FILENAME}"

# ── Dump ─────────────────────────────────────────────────────────────────
echo "Starting backup: ${FILENAME}"
pg_dump "$DATABASE_URL" \
    --no-owner \
    --no-privileges \
    --format=plain \
    | gzip > "$FILEPATH"

SIZE=$(du -h "$FILEPATH" | cut -f1)
echo "Backup complete: ${FILENAME} (${SIZE})"

# ── Retention: daily ─────────────────────────────────────────────────────
echo "Pruning daily backups (keeping last ${RETENTION_DAILY})..."
find "$BACKUP_DIR" -name "backup_*.sql.gz" ! -name "*.weekly.*" -type f -printf '%T@ %p\n' \
    | sort -rn \
    | tail -n +$((RETENTION_DAILY + 1)) \
    | awk '{print $2}' \
    | xargs -r rm -f

# ── Retention: weekly ────────────────────────────────────────────────────
echo "Pruning weekly backups (keeping last ${RETENTION_WEEKLY})..."
find "$BACKUP_DIR" -name "*.weekly.sql.gz" -type f -printf '%T@ %p\n' \
    | sort -rn \
    | tail -n +$((RETENTION_WEEKLY + 1)) \
    | awk '{print $2}' \
    | xargs -r rm -f

echo "Backup process finished."
