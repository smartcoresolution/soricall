# API Contract

## Call-protection family registration v2

User-facing terminology is intentionally limited to two roles.

- `PROTECTED_CALL_USER`: parent or grandparent whose incoming calls are protected from voice phishing
- `FAMILY_CONFIRMATION_CONTACT`: family member who confirms whether a suspicious call was genuine

### Register a family member whose calls will be protected

`POST /api/v1/families/{family_id}/protected-call-users`

```json
{
  "name": "김영희",
  "relation_code": "MOTHER",
  "phone_number": "010-1111-2222"
}
```

Allowed relations: `FATHER`, `MOTHER`, `GRANDFATHER`, `GRANDMOTHER`, `OTHER`.

### Register a family confirmation contact

`POST /api/v1/families/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts`

```json
{
  "name": "김민지",
  "relation_code": "DAUGHTER",
  "phone_number": "010-3333-4444",
  "is_primary_contact": true,
  "notification_priority": 1,
  "notify_enabled": true
}
```

Allowed relations: `SON`, `DAUGHTER`, `GRANDSON`, `GRANDDAUGHTER`, `SPOUSE`, `OTHER`.

The relation is always expressed from the protected family member's point of view.

The MVP API starts with health checks and expands by phase.

## Health

### `GET /health`

Returns service health.

```json
{
  "status": "ok",
  "service": "soricall-api"
}
```

## Planned MVP Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/families`
- `GET /api/v1/families/{family_id}`
- `POST /api/v1/families/{family_id}/members`
- `GET /api/v1/families/{family_id}/members`
- `POST /api/v1/families/{family_id}/safe-word`
- `PUT /api/v1/families/{family_id}/safe-word`
- `POST /api/v1/families/{family_id}/safe-word/verify`
- `POST /api/v1/seniors`
- `GET /api/v1/seniors/{senior_id}`
- `POST /api/v1/seniors/{senior_id}/guardians`
- `GET /api/v1/seniors/{senior_id}/guardians`
- `POST /api/v1/calls/evaluate`
- `POST /api/v1/risk-events`
- `GET /api/v1/risk-events`
- `GET /api/v1/risk-events/{event_id}`
- `POST /api/v1/admin/risk-numbers`
- `GET /api/v1/admin/risk-numbers`
- `POST /api/v1/emergency/confirm-family-call`
- `POST /api/v1/emergency/notify`
- `POST /api/v1/emergency/respond`
- `GET /api/v1/emergency/notifications`
- `POST /api/v1/voice-profiles`
- `GET /api/v1/voice-profiles`
- `GET /api/v1/voice-profiles/{profile_id}`
- `POST /api/v1/voice-profiles/{profile_id}/samples`
- `POST /api/v1/voice-profiles/{profile_id}/enroll`
- `DELETE /api/v1/voice-profiles/{profile_id}`
- `POST /api/v1/voice/analyze`

## AI Service Endpoints

- `GET /health`
- `POST /v1/text/analyze`
- `POST /v1/voice/enroll`
- `POST /v1/voice/analyze`

## Demo Flow

1. Register/login guardian.
2. Create family.
3. Add family member and senior.
4. Link guardian to senior.
5. Set safe word.
6. Register risk number.
7. Evaluate incoming call.
8. Review risk event and emergency notification.
9. Create voice profile.
10. Add voice sample metadata and enroll mock embedding.
