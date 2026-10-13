#!/usr/bin/env bash
# Build the linux/amd64 image on this (arm64) machine and push it to $REGISTRY.
set -euo pipefail

if [[ -z "${REGISTRY:-}" && -f .env ]]; then
  REGISTRY=$(grep -E '^REGISTRY=' .env | cut -d= -f2-)
fi
: "${REGISTRY:?Set REGISTRY (e.g. ghcr.io/your-user) in the environment or .env}"

TAG=$(git rev-parse --short HEAD)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "warning: working tree has uncommitted changes; image tag $TAG won't match them" >&2
fi

if ! docker buildx inspect --bootstrap | grep -q 'linux/amd64'; then
  echo "buildx can't target linux/amd64. One-time setup:" >&2
  echo "  docker run --privileged --rm tonistiigi/binfmt --install amd64" >&2
  exit 1
fi

docker buildx build --platform linux/amd64 \
  -t "$REGISTRY/macro-log:$TAG" -t "$REGISTRY/macro-log:latest" \
  --push .

echo
echo "Pushed $REGISTRY/macro-log:$TAG (and :latest). On the prod host:"
echo "  docker compose pull && docker compose up -d"
