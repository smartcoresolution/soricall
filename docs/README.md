# SoriCall Docs

This directory contains product and engineering documentation for SoriCall.

- `technical_spec_current.docx`: current implementation technical specification and target-gap analysis
- `implementation_spec.md`: source implementation specification
- `api_contract.md`: MVP API contract
- `privacy_security.md`: privacy and security design
- `android_design.md`: Android MVP design
- `ai_design.md`: AI mock service design
- `environments.md`: development and production configuration
- `ui_detailed_design.md`: mobile Web/PWA and Android UI detailed design
- `soricall_ui_design_revised.md`: revised SoriCall UI design specification
- `soricall_simple_ui_wireframe_design.md`: simplified 7-screen UI wireframe design
- `worklog.md`: consolidated current worklog
- `worklog-2026-07-06-soricall-ui-sync.md`: historical UI/API sync worklog

## MVP Integration Status

The current repository includes:

- FastAPI backend with auth, family, safe word, call risk, emergency notifications, and voice profile enrollment.
- FastAPI AI mock service with text and voice analysis adapters.
- Android Kotlin/Compose app with phone signup, family setup, device enrollment, and `CallScreeningService`.
- Web family enrollment, biometric invitation, device connection, and call-protection flows.
- Docker Compose development and production templates for Postgres, API, and AI.

For the implemented as-is system, known limitations, and current verification status, use
`technical_spec_current.docx` as the primary engineering reference.
