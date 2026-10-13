# Macro Log — Design Spec (2026-10-13)

## Context
Fresh, empty repo (`macro-log`, no commits). Build a single-user web app for logging macros (calories, protein, fat, carbs) through the day, mobile-first, behind Cloudflare. Success = logging a meal takes a couple of taps on a phone, Today shows at a glance consumed vs remaining per macro, changing targets never rewrites how past days are judged, and prod deploy is "build amd64 image here → push → compose pull on prod".

**Decisions made:** FastAPI + Jinja + HTMX (+ Alpine for small UI state) · Cloudflare Access for auth (app optionally verifies the Access JWT) · entries = optional name + macros, quick foods log one serving with ×multiplier · calories auto-filled from 4P+4C+9F but overridable · History = day list + charts · fixed timezone setting, midnight boundary · quick foods managed in Settings + "save as quick food" toggle when logging + auto "recent foods" · PWA + dark mode · images pushed to a registry · Log opens as a bottom sheet over Today.

**Out of scope:** barcode scanning / external food DB lookup (explicitly skipped for now — no design accommodations either); multi-user; CSV export; DB backup sidecar.

## Stack
- Python ≥3.14 managed by **uv** (`.venv` in project, `pyproject.toml` + `uv.lock`).
- FastAPI, Uvicorn, Jinja2, SQLAlchemy 2.x, Alembic, pydantic-settings, psycopg[binary] v3 (prod), PyJWT[crypto] (CF Access check).
- Frontend: HTMX 2, Alpine.js 3, Chart.js 4 — **vendored** into `app/static/vendor/` (no CDN, no Node build). Hand-written CSS with custom properties; dark mode via `prefers-color-scheme`.
- Dev DB: SQLite (`./data/dev.db`). Prod DB: Postgres 17. Same code via `DATABASE_URL`.
- Tests: pytest + FastAPI TestClient.

## Data model
- **settings** (single row): `timezone` (IANA, default from env `APP_TZ`).
- **targets**: `id, effective_date (date, unique), calories, protein, fat, carbs, created_at`. Targets for day D = row with greatest `effective_date <= D` (fallback: earliest row). Saving targets in Settings **upserts the row for today** — earlier days keep resolving to older rows, so history is untouched. Settings shows the target change history.
- **quick_foods**: `id, name, serving_label, calories, protein, fat, carbs, sort_order`.
- **entries**: `id, day (local date), logged_at (UTC timestamp), name (nullable), calories, protein, fat, carbs, servings (default 1), quick_food_id (nullable, ON DELETE SET NULL)`. Macros are **snapshotted** (already multiplied by servings), so editing/deleting a quick food never changes past entries.
- Numbers: calories stored as integer; P/F/C as float rounded to 0.1 on input.
- **Recent foods** (derived, no table): named entries from last 30 days, grouped by name+macros, ranked by frequency/recency, excluding names already in quick foods, top 8.

## App structure
```
app/
  main.py          # app factory, static mount, routers, /healthz
  config.py        # pydantic-settings: DATABASE_URL, APP_TZ, CF_ACCESS_TEAM_DOMAIN, CF_ACCESS_AUD
  db.py            # engine/session dependency
  models.py        # SQLAlchemy models
  auth.py          # middleware: verify Cf-Access-Jwt-Assertion via team JWKS when configured; no-op in dev
  services/        # pure-ish logic, unit-tested
    clock.py       # today() in configured TZ
    targets.py     # resolve_targets(day), set_targets_today()
    entries.py     # CRUD, day totals, calorie autofill helper
    foods.py       # quick food CRUD/reorder, recent_foods()
    history.py     # per-day totals+targets, 7/30-day averages, chart series
  routes/
    pages.py       # GET / (today), /day/{date}, /history, /settings, /settings/foods
    entries.py     # POST /entries, POST /quick-foods/{id}/log, GET/PUT/DELETE /entries/{id}
    foods.py       # quick food CRUD + reorder (HTMX partials)
    settings.py    # targets + timezone forms
    history.py     # GET /history/data?days=N (JSON for Chart.js), paged day list partial
  templates/
    base.html, today.html (also used for /day/{date}), history.html, settings.html, foods.html
    partials/      # macro_bars, entry_list, entry_row, entry_form, log_sheet, quick_food_grid, food_row, day_row
  static/
    css/app.css, js/app.js, vendor/{htmx,alpine,chart}.min.js
    manifest.webmanifest, sw.js (minimal, caches static shell only), icons/
alembic/           # migrations (env.py reads DATABASE_URL)
tests/
Dockerfile, compose.yaml (prod), .env.example, .dockerignore, Makefile, scripts/deploy.sh
```

## UI & interaction
- **Layout:** single centered column (max ~640px) on desktop, full width on mobile. Fixed bottom nav: Today · History · **＋ Log** (prominent center button) · Settings. Safe-area insets for iOS PWA.
- **Today / Day view:** date header (day view has ‹ › arrows to step days), four horizontal bars: label, `consumed / target`, fill proportional, "X left" or "X over" (over-target uses a warning color and the bar caps full with an overflow marker). Below: entry list (time, name, macros) with tap-to-edit inline and delete.
- **Log bottom sheet** (Alpine-controlled, opened from nav; on a day view it logs to that day):
  1. Quick-food grid — pinned quick foods, then "Recent". Tap = log 1 serving immediately; a small ×½ / ×1 / ×2 stepper behind a small "⋯" button on each tile.
  2. Manual form — name (optional), P / F / C, calories (auto-fills from 4P+4C+9F until user edits it), modern **toggle switch** "Save as quick food" (reveals serving label field).
  - Submit → server returns updated `macro_bars` + `entry_list` via `hx-swap-oob`, plus `HX-Trigger: entry-logged` → sheet closes, brief toast with **Undo** (DELETE).
- **History:** 7-day and 30-day averages vs targets at top; Chart.js charts (daily calories vs target line; protein/fat/carbs as three lines, each with its target as a dashed line) with 14/30/90-day range toggle; below, reverse-chronological day list with mini bars against *that day's* targets, infinite-scroll via `hx-trigger="revealed"`. Tap a day → `/day/{date}` (editable, supports backfill).
- **Settings:** targets form (calories auto-suggest from macros, overridable) with note "applies from today onward" + list of past target changes; timezone select; link to Quick Foods page (add/edit/delete inline rows, ↑/↓ buttons to reorder).
- All mutations are HTMX partial swaps; full page loads only on nav between top-level pages (use `hx-boost` on nav so even those are swap-based).
- Dark mode + light mode via CSS variables; PWA manifest + icons so it installs full-screen.

## Auth / Cloudflare
- Primary protection is Cloudflare Access in front of the hostname.
- If `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` are set, middleware validates `Cf-Access-Jwt-Assertion` (RS256, JWKS from `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`, cached) and 403s otherwise; `/healthz` exempt. Unset in dev → disabled.
- Uvicorn runs with `--proxy-headers --forwarded-allow-ips='*'`.

## Dev workflow
- `uv sync` → `uv run alembic upgrade head` → `uv run uvicorn app.main:app --reload`. Makefile targets: `dev`, `test`, `migrate`, `revision`, `build`, `deploy`.

## Docker / prod
- **Dockerfile:** multi-stage, `python:3.14-slim` (matches local Python 3.14), uv installs locked deps into `/app/.venv`; non-root user; entrypoint runs `alembic upgrade head` then uvicorn; `HEALTHCHECK` on `/healthz`.
- **compose.yaml (prod):** `app` (image `${REGISTRY}/macro-log:${TAG:-latest}`, env from `.env`, port bound to `${APP_PORT:-8000}`, `depends_on: db: condition: service_healthy`, `restart: unless-stopped`) + `db` (`postgres:17`, named volume, `pg_isready` healthcheck). `.env.example` documents POSTGRES_*, DATABASE_URL, APP_TZ, CF_* vars.
- **scripts/deploy.sh / `make deploy`:** `docker buildx build --platform linux/amd64 -t $REGISTRY/macro-log:$(git rev-parse --short HEAD) -t $REGISTRY/macro-log:latest --push .` (notes the one-time `tonistiigi/binfmt --install amd64` QEMU setup if buildx lacks amd64). Prod: `docker compose pull && docker compose up -d`.

## Error handling
- Form validation via Pydantic/FastAPI: non-negative numbers, sane caps; on error return the form partial with inline messages (HTTP 422 + `HX-Retarget`/`HX-Reswap` so errors render in place).
- Global HTMX `htmx:responseError` handler shows a toast.
- Days with no targets defined → bars show consumed only with "set targets" prompt.

## Testing
- **Unit:** target resolution across effective dates (past days keep old targets after a change), TZ day boundary (`clock.today()` near midnight), calorie autofill, servings multiplication/snapshotting, recent-foods ranking/exclusion, history averages.
- **Route:** TestClient against temp SQLite: log manual entry, log quick food, edit/delete, OOB partials present, settings change doesn't alter a past day's rendered targets, CF Access middleware accept/reject with a locally generated RSA key + JWKS stub.
- **E2E check:** run dev server and exercise via Playwright MCP at 390px and desktop widths (log via sheet, bars update without reload, dark mode).
- **Prod smoke:** build native arm64 image locally and `docker compose up` with Postgres to confirm migrations + app boot; then buildx amd64 push.

