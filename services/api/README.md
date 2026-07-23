# SoriCall API

FastAPI backend for SoriCall.

## Run Locally

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
../../.venv/bin/pytest app/tests
```

## Database migrations

```bash
../../.venv/bin/alembic upgrade head
```

## Seed Demo Data

```bash
cd /home/soricall
PYTHONPATH=/home/soricall/services/api .venv/bin/python scripts/seed_demo_data.py
```

## Health

```bash
curl http://localhost:8000/health
```
