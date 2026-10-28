#!/bin/sh
set -e
alembic upgrade head
# The app applies forwarded headers itself (app/main.py), after recording the real peer for the access check.
exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000 --no-proxy-headers
