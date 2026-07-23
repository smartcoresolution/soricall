#!/usr/bin/env bash
set -euo pipefail

# Fresh installations use the current SQLAlchemy schema as their baseline,
# then stamp Alembic at head. Existing databases must use normal migrations.
if [[ "${ALLOW_SCHEMA_BOOTSTRAP:-}" != "true" ]]; then
  echo "Set ALLOW_SCHEMA_BOOTSTRAP=true only for an empty database." >&2
  exit 2
fi

python -c 'from app.core.database import init_db; init_db()'
alembic stamp head
alembic current
