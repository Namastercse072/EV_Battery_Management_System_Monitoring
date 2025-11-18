#!/bin/bash
set -e

echo "Upgrading Superset database..."
superset db upgrade

echo "Creating admin user..."
superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@superset.local \
  --password admin 2>/dev/null || true

echo "Initializing Superset..."
superset init

# echo "Starting Superset server..."
gunicorn \
  -w 2 \
  -b 0.0.0.0:8088 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  superset.app:create_app()

