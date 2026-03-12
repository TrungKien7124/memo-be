#!/bin/bash
set -e

echo "Waiting for PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."
while ! pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -q 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready."

echo "Waiting for Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
while ! redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
    sleep 1
done
echo "Redis is ready."

cd /app/be

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput 2>/dev/null || true
fi

exec "$@"
