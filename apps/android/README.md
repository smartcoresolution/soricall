# SoriCall Android

Android app scaffold for the SoriCall MVP.

This phase includes a Kotlin + Jetpack Compose project skeleton, MVP screens, local demo repositories, and a `CallScreeningService` skeleton.

Policy constraints:

- No hidden call recording.
- No Accessibility API use for call audio recording.
- Microphone access only after explicit user action.

## Screens

- Onboarding
- Family list
- Safe word
- Emergency confirmation
- Voice profile
- Risk history
- Settings
- Guardian response placeholder

## Build

Open this directory in Android Studio, then run the `app` configuration.

The current Codex environment does not include Java or Gradle, so local CLI build verification was not available here.

## API Integration Boundary

`core/network` contains DTOs and a small API contract matching the current FastAPI MVP endpoints. It uses a mock implementation for now; Retrofit wiring can replace it without changing the screen-level placeholders.
