#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../services/ai"
env PYTHONPATH=/home/soricall/services/ai ../../.venv/bin/pytest app/tests

