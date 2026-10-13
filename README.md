# Macro Log

Personal macro tracker (calories, protein, fat, carbs). FastAPI + HTMX + Alpine, SQLite in dev, Postgres in prod.

## Dev

```bash
uv sync
make migrate      # alembic upgrade head (SQLite at ./data/dev.db)
make dev          # http://localhost:8000
make test
```

New migration after changing `app/models.py`: `make revision m="describe change"`, then review the file in `alembic/versions/`.

## Local prod-like smoke test (native arm64 + Postgres)

```bash
cp .env.example .env   # edit values
make up                # builds macro-log:local, starts app + postgres
curl localhost:8000/healthz
make down
```

## Deploy (build amd64 here, run on the amd64 host)

1. `docker login <registry>` once.
2. `make deploy` — builds `linux/amd64` and pushes `$REGISTRY/macro-log:<git-sha>` and `:latest`.
3. On the prod host (with `compose.yaml` and a filled-in `.env` next to it):
   `docker compose pull && docker compose up -d`. Migrations run on container start.

## Cloudflare

Put the hostname behind a Cloudflare Access application. Optionally set `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD`
so the app rejects any request that didn't pass through Access (`/healthz` stays open for health checks).
