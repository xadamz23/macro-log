#!/bin/sh
set -e
alembic upgrade head
exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8003 --proxy-headers --forwarded-allow-ips='*'
