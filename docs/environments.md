# Environments

SoriCall uses separate configuration files for development and production.

## Development

Development is the default active workflow.

Files:

- `.env.development.example`
- `.env.development`
- `infra/docker/docker-compose.development.yml`

Setup:

```bash
cp .env.development.example .env.development
scripts/dev_up.sh
```

Direct Python services:

```bash
../../.venv/bin/uvicorn app.main:app --reload --port 8000
```

Direct Python mode uses SQLite defaults unless `ENV_FILE` is explicitly set. Docker development mode uses Postgres.

Development defaults are intentionally convenient:

- Local Postgres credentials
- Local storage
- Mock FCM key
- `RETAIN_VOICE_SAMPLES=false`
- Dev-only JWT secret

## Production

Production files are templates and must be edited before use.

Files:

- `.env.production.example`
- `.env.production`
- `infra/docker/docker-compose.production.yml`

Setup:

```bash
cp .env.production.example .env.production
# Replace all secrets before running.
scripts/prod_up.sh
```

Production safety:

- `APP_ENV=production`
- `JWT_SECRET` must not be the default placeholder.
- Raw voice samples remain disabled by default.
- FCM and storage settings must be replaced with real production values.
