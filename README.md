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

## Logging with Claude

Set `ANTHROPIC_API_KEY` in `.env` to show "Log with Claude" in the log sheet, including on the production host. Its
Photo mode sends a photo (and an optional description) to the Claude API; Describe mode sends just a description, such
as "large coke from mcdonalds". Claude's estimate is shown to check, then logged, or copied into the manual form to
edit. The app doesn't store the photo.
Without a key the option is hidden. `ANTHROPIC_MODEL` overrides the default model.

## Local prod-like smoke test (native arm64 + Postgres)

```bash
cp .env.example .env   # edit values
make up                # builds macro-log:local, starts app + postgres
curl localhost:8000/healthz
make down
```

## Deploy (build amd64 here, run on the amd64 host)

Migrations run on container start.

```bash
./deploy.sh              # patch bump of the newest remote tag, e.g. 1.1.25 -> 1.1.26
./deploy.sh --minor      # 1.2.0  (--major: 2.0.0)
./deploy.sh 1.3.0        # explicit tag
```

It reads the newest `X.Y.Z` tag from `origin` with `git ls-remote` (so local tags don't need fetching), shows the
new tag and asks for confirmation. It refuses a tag that already exists or is older than the latest. Then it runs four
steps:

1. Creates an annotated git tag and pushes it to `origin`.
2. Builds a `linux/amd64` image `docker.io/xadamz23/macro-log:<tag>`.
3. Pushes that image to Docker Hub.
4. SSHes to `root@docker-public.stizzle.org` and runs `/home/dockerapps/macrolog/update-app.sh <tag>`.

`update-app.sh` exits early if `macrolog-app` is already running exactly that image tag. Otherwise it stops the stack,
rewrites `docker-compose.yaml` to pin the new tag, and starts the stack again.

One-time setup:

- Here:
  - Run `docker login` for Docker Hub.
  - Make sure buildx can build `linux/amd64` (`docker run --privileged --rm tonistiigi/binfmt --install amd64`).
  - Set up key-based SSH as `root` to the host. The script uses `BatchMode`, so it can't prompt for a password.
- On the host:
  - Copy `scripts/update-app.sh` to `/home/dockerapps/macrolog/` and `chmod +x` it.
  - Put a filled-in `.env` next to it (see `.env.example`).
  - Create the shared tunnel network (`docker network create cf-tunnel`) and attach the `cloudflared` container to it.

The generated stack publishes no host ports. `macrolog-app` joins `cf-tunnel`, and `macrolog-db` sits only on the
internal `macrolog-internal` network. Point the tunnel's public hostname at `http://macrolog-app:8000`.

Edit `update-app.sh` in the repo, then copy it to the host again: the host runs its own copy. It generates the compose
file itself, so `compose.yaml` in the repo isn't used on the host.

## Cloudflare

Put the hostname behind a Cloudflare Access application. Set `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` so the app
rejects any request that didn't pass through Access. `/healthz` stays open for health checks.

The generated compose file publishes no ports, so only `cloudflared` on the `cf-tunnel` network can reach the app.
The variables are recommended as defence in depth.

## Tailscale

A Tailscale sidecar container running `tailscale serve` (proxying to `http://macrolog-app:8000`) can serve the app on
the tailnet. Those requests carry no Access token, so set `TAILNET_PROXY_HOST` to the sidecar's container name (e.g.
`macrolog-ts`). A request then also passes the access check when its TCP peer is that container and it has the
`Tailscale-User-Login` header that `tailscale serve` adds for tailnet users. The header alone isn't trusted, because
other containers on the network could send it.
