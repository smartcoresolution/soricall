# SoriCall - 안심소리 가족콜

AI 가족 사칭 보이스피싱 차단 및 가족 안심 통화 앱 MVP입니다.

## Environments

SoriCall separates development and production configuration.

| Environment | Env file | Compose file | Purpose |
|---|---|---|---|
| Development | `.env.development` | `infra/docker/docker-compose.development.yml` | Local MVP development |
| Production | `.env.production` | `infra/docker/docker-compose.production.yml` | Deployment template with required secrets |

`.env.example` mirrors the development defaults for compatibility.

## Development Setup

```bash
cp .env.development.example .env.development
scripts/dev_up.sh
```

If Docker is not installed on Ubuntu:

```bash
sudo scripts/install_docker_ubuntu.sh
```

When Docker is unavailable, run the Python services directly:

```bash
python3 -m venv .venv
.venv/bin/pip install -e "services/api[dev]"

cd services/api
../../.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../ai
PYTHONPATH=/home/soricall/services/ai ../../.venv/bin/uvicorn app.main:app --reload --port 8100
```

Direct Python mode uses the API service's default SQLite database. Docker development mode uses Postgres through `.env.development`.

## Production Template

Production is intentionally not the default path right now. To prepare it:

```bash
cp .env.production.example .env.production
# Edit every replace-* secret before use.
scripts/prod_up.sh
```

The API refuses to start in `APP_ENV=production` if `JWT_SECRET` is still the default development placeholder.

## Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -e "services/api[dev]"

scripts/run_api_tests.sh
scripts/run_ai_tests.sh
```

## Demo Data

For the local development API database:

```bash
PYTHONPATH=/home/soricall/services/api .venv/bin/python scripts/seed_demo_data.py
```

Demo guardian login:

```text
guardian.demo@example.com / password123
```

API:

- http://localhost:8000/docs
- http://localhost:8000/health

AI:

- http://localhost:8100/docs
- http://localhost:8100/health

## Services

- `apps/android`: Android app scaffold
- `apps/web`: Web development console
- `services/api`: FastAPI backend
- `services/ai`: AI analysis service with mock adapters
- `infra/docker`: local Docker Compose
- `infra/db`: database initialization and migrations
- `docs`: implementation and design docs

## MVP Policy

This MVP does not implement hidden call recording.
Do not use Android Accessibility API for call audio recording.

## Current Backend Scope

- Email/password registration and login with signed bearer token
- Family and family member registration
- Senior profile creation and guardian linking
- Safe word hash storage and verification
- Number-based call risk evaluation with unknown number, risk number, repeated call, and late-night call signals
- Risk event creation and lookup
- Guardian emergency notification placeholder flow
- Voice profile enrollment with mock AI embedding storage

## Current AI Scope

- Rule-based Korean phishing text risk analysis
- Mock speaker embedding enrollment
- Mock speaker similarity comparison
- Mock synthetic voice suspicion scoring
- Mock STT based on `audio_ref` hints
- Final voice-analysis risk scoring

## Current Android Scope

- Kotlin + Jetpack Compose project skeleton
- MVP screen placeholders for onboarding, family, safe word, emergency, voice profile, history, and settings
- Local demo repositories for UI data
- `CallScreeningService` skeleton for number-based screening
- Guardian emergency response placeholder screen
- API DTOs and mock API contract boundary

## Current Web Scope

- React/Vite development console
- API health check
- Demo family/senior/guardian setup flow
- Call risk evaluation
- Risk event and emergency notification lists
- Voice profile list

## Environment Notes

This workspace currently has Python but does not have Docker, Java, or Gradle installed. API and AI tests are verified locally; Android and Docker builds should be verified in Android Studio or a CI runner with those tools installed.
