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
curl localhost:8003/healthz
make down
```

## Deploy (build amd64 here, run on the amd64 host)

Migrations run on container start with either method.

### Tagged release (current)

```bash
scripts/deploy-macrolog-from-arm64.sh v1.2.0
```

This runs four steps:

1. Creates an annotated git tag and pushes it to `origin`.
2. Builds a `linux/amd64` image `docker.io/xadamz23/macro-log:<tag>`.
3. Pushes that image to Docker Hub.
4. SSHes to `root@docker-public.stizzle.org` and runs `/home/dockerapps/macrolog/update-app.sh <tag>`.

`update-app.sh` exits early if `macrolog-app` is already running that tag. Otherwise it stops the stack,
rewrites `docker-compose.yaml` to pin the new tag, and starts the stack again.

One-time setup:

- Here:
  - Run `docker login` for Docker Hub.
  - Make sure buildx can build `linux/amd64` (`docker run --privileged --rm tonistiigi/binfmt --install amd64`).
  - Set up key-based SSH as `root` to the host. The script uses `BatchMode`, so it can't prompt for a password.
- On the host:
  - Copy `scripts/update-app.sh` to `/home/dockerapps/macrolog/` and `chmod +x` it.
  - Put a filled-in `.env` next to it (see `.env.example`).
  - Create the `proxied_to_localhost` Docker network.

Edit `update-app.sh` in the repo, then copy it to the host again: the host runs its own copy. It generates the compose
file itself, so `compose.yaml` in the repo isn't used on the host.

### Registry `latest` (alternative)

1. `docker login <registry>` once.
2. `make deploy` builds `linux/amd64` and pushes `$REGISTRY/macro-log:<git-sha>` and `:latest`.
3. On the prod host, with `compose.yaml` and a filled-in `.env` next to it, run
   `docker compose pull && docker compose up -d`.

## Cloudflare

Put the hostname behind a Cloudflare Access application. Set `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` so the app
rejects any request that didn't pass through Access. `/healthz` stays open for health checks.

How much those variables matter depends on the deploy method:

- **Tagged release:** the generated compose file publishes `8003:8003` on all interfaces, so the variables are
  required.
- **Registry `latest`:** `compose.yaml` publishes the port on `127.0.0.1` only (`APP_BIND`), with `cloudflared` on the
  same host. The variables are recommended, and become required if you publish the port beyond localhost.
