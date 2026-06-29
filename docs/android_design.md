# Android Design

The Android MVP uses Kotlin and Jetpack Compose.

## MVP Scope

- Onboarding
- Role selection
- Family registration
- Safe word setup
- Suspicious call warning
- Emergency family confirmation
- Voice profile upload screen
- Risk history
- `CallScreeningService` skeleton

## Policy Notes

The app must not record calls secretly. Microphone access is only for explicit user actions such as family voice sample enrollment.

## Current Implementation

- Kotlin + Jetpack Compose project skeleton lives in `apps/android`.
- Navigation is state-based for MVP scaffolding.
- `SoriCallScreeningService` performs local number-risk evaluation only.
- API, Room, Hilt, Retrofit, and FCM production wiring are reserved for later phases.
