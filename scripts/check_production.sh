#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-http://127.0.0.1}"

check() {
  local name="$1"
  local url="$2"
  local expected="$3"
  local status
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 10 "$url")"
  if [[ "$status" != "$expected" ]]; then
    echo "FAIL  $name ($url returned $status; expected $expected)" >&2
    return 1
  fi
  echo "PASS  $name ($status)"
}

check "web redirect" "$base_url/soricall" "301"
check "web app" "$base_url/soricall/" "200"
check "API health" "$base_url/soricall-api/health" "200"
