#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <tag>"
    exit 1
fi

tag=$1
image="docker.io/xadamz23/macro-log:$tag"

cd "/home/dockerapps/macrolog"

running=$(docker ps --filter 'name=^macrolog-app$' --format '{{.Image}}')
if [[ "$running" == "$image" ]]; then
    echo "[INFO] app is already running the latest version ($tag)"
    exit 0
fi

if ! docker network inspect cf-tunnel >/dev/null 2>&1; then
    echo "[ERROR] docker network cf-tunnel does not exist; run: docker network create cf-tunnel"
    exit 1
fi

echo "[INFO] stopping the container"
docker compose down

echo "[INFO] updating tag in compose file to $tag"

cat <<EOF > docker-compose.yaml
name: macrolog

services:
  app:
    container_name: macrolog-app
    image: $image
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@db:5432/\${POSTGRES_DB}
    networks:
      - cf-tunnel
      - internal
    security_opt:
      - no-new-privileges:true
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    container_name: macrolog-db
    image: postgres:17
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - internal
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \$\${POSTGRES_USER} -d \$\${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  pgdata:

networks:
  cf-tunnel:
    external: true
  internal:
    name: macrolog-internal
    internal: true
EOF

echo "[INFO] starting the container back up"
docker compose up -d
