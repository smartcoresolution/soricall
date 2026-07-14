# SoriCall Production Runbook

## Prerequisites

- Docker with Compose v2
- nginx serving `/soricall/` and proxying `/soricall-api/` to `127.0.0.1:8000`
- A production environment file at `/home/soricall/.env.production`

## First deployment

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

Replace `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, and optional FCM values. The password embedded in `DATABASE_URL` must match `POSTGRES_PASSWORD` and must be URL-encoded when it contains reserved URL characters.

Start the backend and wait for all health checks:

```bash
scripts/prod_up.sh
```

Build and publish the web app:

```bash
cd apps/web
npm ci
npm run build
sudo install -d -o root -g www-data -m 0755 /var/www/soricall
sudo rsync -a --delete dist/ /var/www/soricall/
```

Use the locations in `infra/nginx/soricall.locations.conf` in each applicable nginx HTTP/HTTPS server block, then validate and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Verify the deployment:

```bash
scripts/check_production.sh http://127.0.0.1
scripts/check_production.sh https://your-production-host
```

## Routine deployment

1. Pull or deploy reviewed source changes.
2. Run API, AI, and web build tests.
3. Run `scripts/prod_up.sh`.
4. Publish `apps/web/dist/` atomically or with `rsync --delete`.
5. Run `scripts/check_production.sh` against the public HTTPS origin.

## Rollback

- Keep the previous static web directory or release artifact before publishing.
- Roll back the application image/source revision and run `scripts/prod_up.sh` again.
- Do not remove the `soricall_pg_data_prod` volume during rollback.
