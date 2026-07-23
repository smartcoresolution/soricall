#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$project_root/.env.production"
compose_file="$project_root/infra/docker/docker-compose.production.yml"

if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file. Copy .env.production.example and replace all production secrets." >&2
  exit 1
fi

if grep -Eq '^(POSTGRES_PASSWORD|JWT_SECRET)=replace-with-' "$env_file"; then
  echo "Refusing to start with placeholder production secrets." >&2
  exit 1
fi

docker compose --env-file "$env_file" -f "$compose_file" config --quiet
docker compose --env-file "$env_file" -f "$compose_file" up --build -d --wait
