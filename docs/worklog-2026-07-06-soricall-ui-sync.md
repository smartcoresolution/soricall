# SoriCall Worklog - 2026-07-06 UI Sync

작성 시각: 2026-07-06 12:38 KST

## Summary

SoriCall UI was reworked around the simplified 7-screen senior-friendly service flow:

```text
가족 등록 -> 어르신 홈 -> 전화 수신 -> 의심 경고 -> 추가 확인 -> 결과 안내 -> 보호자 알림
```

The work also fixed remote VS Code/browser API routing and a Docker/Postgres UUID insert error that blocked signup.

## UI Design Inputs

Added and referenced:

- `docs/soricall_ui_design_revised.md`
- `docs/soricall_simple_ui_wireframe_design.md`
- `docs/ui_detailed_design.md`
- `docs/ui_detailed_design.pdf`

## Frontend Changes

- Reworked service start into a simple registration hub:
  - 가족 연락처 등록
  - 얼굴 프로필 등록
  - 음성 프로필 등록
- Added sub screens for:
  - `contactSetup`
  - `faceSetup`
  - `voiceSetup`
- Reworked main tab labels toward the 7-screen MVP flow:
  - 홈
  - 가족등록
  - 전화수신
  - 추가확인
  - 결과
- Simplified the senior home:
  - 안심 보호 중입니다
  - registered family cards
  - phone action
  - guardian help request
  - compact service flow strip
- Reworked suspicious call flow:
  - phone receiving state
  - unregistered-number warning
  - do-not-send-money/account/app-install warnings
  - hang up and guardian confirmation actions
- Reworked additional confirmation and result screens:
  - voice check
  - face check
  - guardian check
  - family confirmed / hard to verify / possible impersonation result states
- Updated consent copy from the old dementia-oriented language to SoriCall voice/face/family-impersonation wording.

## Remote Dev / API Routing Fix

The browser is local while code and servers run on the remote machine through VS Code Remote. Therefore browser `localhost` points to the local PC unless VS Code forwards the port.

Frontend API discovery was changed to use same-origin `/soricall-api` by default. Direct browser candidates such as `localhost:8000`, `127.0.0.1:8000`, and `${hostname}:8000` were removed from default discovery.

Vite dev proxy now maps:

```text
/soricall-api -> http://127.0.0.1:8000
/api          -> http://127.0.0.1:8000
/health       -> http://127.0.0.1:8000
```

## Backend Fix

Signup was failing against Docker/Postgres with:

```text
column "id" is of type uuid but expression is of type character varying
```

Root cause:

- SQLAlchemy models used `String(36)` for UUID primary/foreign keys.
- Postgres schema uses native `UUID`.
- SQLite tests did not expose the mismatch.

Fix:

- Added a cross-dialect `GUID` SQLAlchemy `TypeDecorator`.
- It binds UUID values as native Postgres UUID and stores strings in SQLite.
- Replaced model UUID PK/FK/resource ID columns with `GUID()`.

## Verification

Passed:

```text
npm run build
scripts/run_api_tests.sh
```

Also verified after Docker rebuild:

```text
GET  /soricall-api/health              -> 200 OK
POST /soricall-api/api/v1/auth/register -> 201 Created
```

Docker API container was rebuilt/restarted with:

```bash
docker compose -f infra/docker/docker-compose.development.yml up -d --build api
```

## Current Dev Run Notes

Recommended remote-server commands:

```bash
cd /home/soricall
docker compose -f infra/docker/docker-compose.development.yml up -d --build

cd /home/soricall/apps/web
npm run dev
```

In local Chrome, use the VS Code forwarded port:

```text
http://localhost:5173/
```

Important: this `localhost` is local PC localhost, forwarded by VS Code to the remote server.

## Remaining Notes

- Production nginx `/soricall-api/` was observed pointing to `127.0.0.1:8001`, while SoriCall API is on `8000`. This requires sudo to change:

```nginx
location ^~ /soricall-api/ {
    proxy_pass http://127.0.0.1:8000/;
}
```

- Static deployment to `/var/www/soricall/` may require sandbox/permission escalation.
- Continue UI refinement from `docs/soricall_simple_ui_wireframe_design.md`.
