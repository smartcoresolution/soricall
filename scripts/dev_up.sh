#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../infra/docker"
docker compose --env-file ../../.env.development -f docker-compose.development.yml up --build
