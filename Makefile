.PHONY: dev test migrate revision

dev:
	uv run uvicorn --factory app.main:create_app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest -q

migrate:
	uv run alembic upgrade head

revision:
	uv run alembic revision --autogenerate -m "$(m)"

.PHONY: build up down deploy

build:
	docker build -t macro-log:local .

up:
	docker compose -f compose.yaml -f compose.build.yaml up --build -d

down:
	docker compose -f compose.yaml -f compose.build.yaml down

deploy:
	./scripts/deploy.sh
