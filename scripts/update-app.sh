#!/bin/bash

tag=$1

cd "/home/dockerapps/macrolog"

docker ps | grep macrolog-app | grep -q "$tag"
if [[ $? -eq 0 ]]; then
    echo "[INFO] app is already running the latest version ($tag)"
    exit 0
fi

echo "[INFO] stopping the container"
docker compose down

echo "[INFO] updating tag in compose file to $tag"

cat <<EOF > docker-compose.yaml
services:
  app:
    container_name: macrolog-app
    image: docker.io/xadamz23/macro-log:$tag
    env_file: .env
    environment:
      DATABASE_URL: postgresql+psycopg://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@db:5432/\${POSTGRES_DB}
    ports:
      - "8003:8003"
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \$\${POSTGRES_USER} -d \$\${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  pgdata:

networks:
  default:
    external: true
    name: proxied_to_localhost
EOF

echo "[INFO] starting the container back up"
docker compose up -d