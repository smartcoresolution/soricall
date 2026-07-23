#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$project_root/.env.production"
compose_file="$project_root/infra/docker/docker-compose.production.yml"

if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file." >&2
  exit 1
fi

docker compose --env-file "$env_file" -f "$compose_file" down
