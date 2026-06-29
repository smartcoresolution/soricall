# SoriCall AI

FastAPI AI mock analysis service for SoriCall.

## Run Locally

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

## Tests

```bash
env PYTHONPATH=/home/soricall/services/ai ../../.venv/bin/pytest app/tests
```

## Endpoints

- `GET /health`
- `POST /v1/text/analyze`
- `POST /v1/voice/enroll`
- `POST /v1/voice/analyze`

## Mock Hints

The mock voice pipeline uses `audio_ref` text hints:

- `clean`, `real`: low spoof probability
- `spoof`, `synthetic`, `deepfake`: high spoof probability
- `match`, `family`: speaker match
- `mismatch`, `fake`, `unknown`: speaker mismatch
- `money`, `scam`: STT text with money-transfer pressure
- `app`: STT text with app-install pressure
