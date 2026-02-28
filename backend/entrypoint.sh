#!/bin/sh

# Останавливать выполнение при ошибке
set -e

echo "Running migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"