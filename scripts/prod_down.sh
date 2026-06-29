#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../infra/docker"
docker compose --env-file ../../.env.production -f docker-compose.production.yml down

