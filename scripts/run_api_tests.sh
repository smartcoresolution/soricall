#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../services/api"
../../.venv/bin/pytest app/tests

