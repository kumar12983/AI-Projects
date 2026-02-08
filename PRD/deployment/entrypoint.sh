#!/bin/sh
set -e

# Simple entrypoint that waits until Postgres is ready, then runs the CMD
HOST="${DB_HOST:-db}"
PORT="${DB_PORT:-5432}"
USER="${DB_USER:-postgres}"

echo "Waiting for database ${HOST}:${PORT}..."
until pg_isready -h "$HOST" -p "$PORT" -U "$USER" >/dev/null 2>&1; do
  sleep 1
done

echo "Database is available - starting command: $@"
exec "$@"
