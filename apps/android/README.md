# SoriCall Android

## Device connection

The app starts on the device connection screen until a `senior_id` and access token are
validated. The emulator uses `http://10.0.2.2:8000` by default. Change
`SORICALL_API_BASE_URL` in `app/build.gradle.kts` for a physical device or production build.

To receive incoming-call screening, grant SoriCall the call-screening role in Android system
settings. Warning notifications also require notification and full-screen notification
permission on Android versions that expose those controls.

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
