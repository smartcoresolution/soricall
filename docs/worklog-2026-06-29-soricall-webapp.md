# SoriCall Web/App Worklog - 2026-06-29

## Summary

SoriCall frontend was rebuilt as a mobile-first senior-friendly web app and connected to the FastAPI backend through nginx. The flow now starts with signup, consent, login, role selection, family connection, and service screens for family, risk call evaluation, video verification, history, and settings.

## Frontend

- Reworked the web app into a smartphone-oriented PWA layout.
- Added onboarding screens:
  - Welcome
  - Signup
  - Consent procedure
  - Login
  - Service start and role selection
- Added senior-friendly navigation:
  - Back button on upper left
  - Home shortcut on upper right
  - Bottom tabs for main service screens
- Added consent procedure before account registration:
  - Required data collection and analysis consent
  - Required privacy policy consent
  - Required non-medical service acknowledgement
  - Required third-party/synthetic voice possibility acknowledgement
  - Optional AI model improvement and research consent
  - Optional service notification consent
- Added PWA files:
  - `manifest.webmanifest`
  - `sw.js`
  - `icon.svg`
- Updated API base URL discovery so deployed browser clients use `/soricall-api` before direct backend ports.
- Registered the service worker under the `/soricall/` base path.

## Backend

- Added face profile and video verification backend support.
- Added API routes for:
  - Face profile create/list/update/delete
  - Video verification request/list
  - Video verification accept
- Updated models, schemas, and DB init script for face/video records.
- Adjusted development CORS handling so the web app can call the API during local and nginx-proxied testing.

## Deployment

- Production frontend build command:

```bash
npm run build -- --base=/soricall/
```

- Static frontend deployment path:

```text
/var/www/soricall/
```

- Public frontend URL:

```text
http://175.118.124.67/soricall/
```

- Public API proxy URL:

```text
http://175.118.124.67/soricall-api/
```

## Verification

- Frontend production build passed.
- API health check passed:

```json
{"status":"ok","service":"soricall-api"}
```

- API test suite passed:

```text
12 passed
```

## Notes

- Browser cache or an older service worker can keep the old UI bundle. If the old screen appears, perform a hard refresh or unregister the SoriCall service worker and clear site data.
- Local environment files and shell/user configuration files must not be committed to GitHub.
