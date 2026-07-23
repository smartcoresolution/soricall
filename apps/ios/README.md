# SoriCall iOS implementation contract

The iOS client must reuse the backend `/api/v1` contract and must not claim
system-wide call blocking. Apple CallKit/Call Directory capabilities and App
Review constraints must be validated before product wording is finalized.

Initial implementation order:

1. Keychain-backed access/refresh token storage and phone OTP sign-in.
2. Family, protected user, invitation resolve/OTP/complete, and approval APIs.
3. `UNUserNotificationCenter` + APNs token registration through
   `POST /api/v1/device-push-tokens` using platform `IOS`.
4. Share Extension using an App Group temporary directory; create
   `POST /api/v1/media-assets/import-sessions`, then validate the copied asset.
5. `AVAudioRecorder` enrollment (15–60 seconds) and optional photo capture.
6. Accessibility verification with VoiceOver and 200% Dynamic Type.

Security requirements:

- Never place biometric payloads or invitation tokens in logs.
- Delete App Group temporary files after upload success, rejection, or expiry.
- Treat imported files as trust level D until OTP and protected-user approval.
- Preserve `X-Request-ID` from API failures in diagnostic reports.
