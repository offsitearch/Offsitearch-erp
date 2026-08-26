#!/bin/sh

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"

echo "Running database migrations..."
if alembic upgrade head; then
    echo "Migrations complete."
else
    echo "WARNING: migrations failed — app will start anyway. Check logs."
fi

echo "Starting application server on port ${PORT}..."
exec gunicorn app.main:app \
  -w "$WORKERS" \
  -k uvicorn.workers.UvicornWorker \
  -b "0.0.0.0:${PORT}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
