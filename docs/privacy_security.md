# Privacy and Security Design

SoriCall is privacy-first by default.

## Principles

- Do not implement hidden call recording.
- Do not use Android Accessibility API for call audio recording.
- Store safe words as hashes only.
- Store phone numbers as hash plus last four digits where possible.
- Do not retain raw voice samples by default in production.
- Voice enrollment stores mock embeddings by default. Raw sample references are dropped unless `RETAIN_VOICE_SAMPLES=true`.
- Require explicit consent before collecting family voice samples.
- Keep mock AI outputs advisory. Do not present AI results as certainty.
