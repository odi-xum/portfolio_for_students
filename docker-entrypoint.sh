#!/bin/bash
set -e

echo "=== diplom docker-entrypoint ==="

# Ждём PostgreSQL (только если DATABASE_URL указывает на PostgreSQL)
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "^postgresql"; then
  echo "Waiting for PostgreSQL..."
  DB_HOST=$(echo "$DATABASE_URL" | sed -E 's|^postgresql://[^:]+:[^@]+@([^:/]+).*$|\1|')
  DB_PORT=$(echo "$DATABASE_URL" | sed -E 's|^postgresql://[^:]+:[^@]+@[^:]+:([0-9]+).*$|\1|')
  DB_PORT=${DB_PORT:-5432}

  for i in $(seq 1 30); do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
      echo "PostgreSQL ready."
      break
    fi
    echo "  waiting... ($i/30)"
    sleep 1
  done
fi

# Создаём таблицы
echo "Creating tables..."
python -c "
from app import create_app
from models import db
app = create_app()
with app.app_context():
    db.create_all()
print('Tables ready.')
"

# Seed-данные (опционально)
if [ "$RUN_SEED" = "true" ]; then
  echo "Loading seed data..."
  python sql/load.py
  echo "Seed data loaded."
fi

echo "Starting gunicorn..."
exec "$@"
