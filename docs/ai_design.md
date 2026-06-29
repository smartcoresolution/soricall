# AI Design

The MVP AI service uses deterministic mock adapters behind stable interfaces.

## Adapters

- Speaker verification
- Anti-spoofing
- STT
- NLP risk analysis

## MVP Behavior

The mock service returns reproducible results based on input text or filename-like hints. This allows the API and Android flows to be built before real model integration.

## Implemented Endpoints

- `POST /v1/text/analyze`
- `POST /v1/voice/enroll`
- `POST /v1/voice/analyze`

`audio_ref` is a mock reference string in Phase 3. Later phases can replace it with uploaded object keys or local temp file paths without changing adapter boundaries.

## Backend Enrollment Flow

The API service creates a voice profile, records an enrollment sample metadata row, calls the AI enroll adapter, and stores the returned mock embedding metadata. Raw sample references are not retained by default.
