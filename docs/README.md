# SoriCall Docs

This directory contains product and engineering documentation for SoriCall.

- `implementation_spec.md`: source implementation specification
- `api_contract.md`: MVP API contract
- `privacy_security.md`: privacy and security design
- `android_design.md`: Android MVP design
- `ai_design.md`: AI mock service design
- `environments.md`: development and production configuration

## MVP Integration Status

The current repository includes:

- FastAPI backend with auth, family, safe word, call risk, emergency notifications, and voice profile enrollment.
- FastAPI AI mock service with text and voice analysis adapters.
- Android Kotlin/Compose scaffold with local demo data and API DTO boundaries.
- Docker Compose configuration for Postgres, API, and AI.
