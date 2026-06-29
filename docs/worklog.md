# SoriCall Worklog

작성 시각: 2026-06-26 12:18 KST

## 개요

`soricall_implementation_spec.md`를 기준으로 SoriCall MVP 모노레포를 단계별로 구현했다. 현재 저장소는 FastAPI 백엔드, FastAPI AI mock 서비스, Android scaffold, Web 개발 콘솔, Docker 개발/운영 환경 템플릿을 포함한다.

## Phase 0: Monorepo Scaffold

- 루트 README, `.env.example`, `.gitignore` 작성
- `services/api` FastAPI skeleton 생성
- `services/ai` FastAPI skeleton 생성
- `infra/docker` Dockerfile 및 Compose 초기 구성
- `infra/db/init.sql` 초기 DB schema 추가
- `docs` 하위 설계 문서 초안 작성
- `apps/android` placeholder 생성

검증:

- API health test 통과
- AI health/text analysis test 통과
- Ruff lint 통과

## Phase 1: Backend MVP API

- SQLAlchemy DB 설정 추가
- 모델 추가:
  - `User`
  - `Family`
  - `FamilyMember`
  - `Senior`
  - `Guardian`
  - `SafeWord`
  - `CallEvent`
  - `RiskEvent`
  - `ConsentLog`
  - `AuditLog`
- 인증 API 추가:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
- 가족/구성원 API 추가
- 어르신/보호자 연결 API 추가
- 안심 단어 hash 저장 및 검증 API 추가
- 기본 call risk evaluation API 추가

보안 처리:

- 비밀번호 hash 저장
- 안심 단어 원문 미저장
- 전화번호 hash + last4 중심 처리

## Phase 2: Risk Scoring Engine

- `RiskNumber` 모델 추가
- 관리자 위험번호 API 추가:
  - `POST /api/v1/admin/risk-numbers`
  - `GET /api/v1/admin/risk-numbers`
- 위험 평가 신호 추가:
  - 가족 번호
  - 모르는 번호
  - 위험번호 매칭
  - 1시간 내 반복 전화
  - 심야 전화
- `HIGH` 이상 위험 평가 시 `risk_events` 자동 생성

## Phase 3: AI Mock Service

- Speaker verification adapter/interface 추가
- Mock speaker embedding 생성
- Mock speaker similarity 비교
- Anti-spoofing adapter/interface 추가
- Mock 합성음성 의심도 계산
- Mock STT adapter 추가
- Rule-based Korean phishing text risk 분석
- 최종 voice risk scoring pipeline 추가
- AI endpoints 추가:
  - `POST /v1/text/analyze`
  - `POST /v1/voice/enroll`
  - `POST /v1/voice/analyze`

## Phase 4: Android Scaffold

- Kotlin + Jetpack Compose Android project skeleton 추가
- `MainActivity`와 state-based navigation scaffold 추가
- MVP 화면 placeholder 추가:
  - Onboarding
  - Family list
  - Safe word
  - Emergency confirmation
  - Guardian response
  - Voice profile
  - Risk history
  - Settings
- `CallScreeningService` skeleton 추가
- Local demo repository 추가
- API DTO/contract/mock boundary 추가

제약:

- 현재 작업 환경에 Java/Gradle이 없어 Android CLI build는 수행하지 못했다.

## Phase 5: Guardian Emergency Notification

- `EmergencyNotification` 모델 추가
- FCM placeholder service 추가
- 긴급 알림 API 추가:
  - `POST /api/v1/emergency/confirm-family-call`
  - `POST /api/v1/emergency/notify`
  - `POST /api/v1/emergency/respond`
  - `GET /api/v1/emergency/notifications`
- 고위험 통화 평가 시 보호자 알림 row 자동 생성
- Android 보호자 응답 placeholder 화면 추가

## Phase 6: Voice Profile Enrollment

- `VoiceProfile`, `VoiceSample` 모델 추가
- Voice profile API 추가:
  - `POST /api/v1/voice-profiles`
  - `GET /api/v1/voice-profiles`
  - `GET /api/v1/voice-profiles/{profile_id}`
  - `POST /api/v1/voice-profiles/{profile_id}/samples`
  - `POST /api/v1/voice-profiles/{profile_id}/enroll`
  - `DELETE /api/v1/voice-profiles/{profile_id}`
- API service용 AI enroll client mock 추가
- Mock embedding metadata 저장
- `RETAIN_VOICE_SAMPLES=false` 기본 정책 추가
- 기본값에서는 raw sample reference 미보관

## Integration Cleanup

- `scripts/seed_demo_data.py` 추가
- 테스트 실행 스크립트 추가:
  - `scripts/run_api_tests.sh`
  - `scripts/run_ai_tests.sh`
- 개발/운영 환경 분리:
  - `.env.development.example`
  - `.env.production.example`
  - `infra/docker/docker-compose.development.yml`
  - `infra/docker/docker-compose.production.yml`
  - `scripts/dev_up.sh`
  - `scripts/dev_down.sh`
  - `scripts/prod_up.sh`
  - `scripts/prod_down.sh`
- API/AI settings에서 `ENV_FILE` 지원
- production 환경에서 기본 JWT secret 사용 시 API startup 거부
- Docker 설치 스크립트 추가:
  - `scripts/install_docker_ubuntu.sh`

## Docker Development

- Docker 설치 완료 후 개발환경 실행 확인
- Postgres host port 충돌로 개발 compose의 Postgres host port를 `5433:5432`로 변경
- Postgres healthcheck 추가
- API는 Postgres healthy 이후 시작하도록 compose depends_on 보강
- `infra/db/init.sql` 오류 수정:
  - `consent_logs`를 `voice_profiles`보다 먼저 생성
  - `risk_events.reason_codes`를 코드와 맞게 `TEXT`로 변경
  - `audit_logs.metadata_json` 컬럼명 정렬

현재 Docker 개발환경 상태:

- `soricall-postgres-dev`: healthy 확인
- `soricall-api-dev`: startup complete 확인
- `localhost:8000/docs`: API Swagger
- `localhost:8100/docs`: AI Swagger

## Web App

- Android보다 Web을 먼저 만들기로 방향 전환
- `apps/web` 생성
- React + Vite + TypeScript 기반 개발 콘솔 구현
- 기능:
  - API health check
  - 데모 가족/어르신/보호자/위험번호/음성프로필 생성
  - 전화 위험도 평가
  - 위험 이벤트 조회
  - 보호자 알림 생성/조회
  - 음성 프로필 조회
- FastAPI CORS 설정 추가:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`

검증:

- `npm run build` 성공
- Codex 실행 환경에서는 포트 바인딩 제한으로 `npm run dev`를 직접 유지하지 못함

## Current Verification

마지막 기준 검증:

- API tests: `10 passed`
- AI tests: `6 passed`
- Ruff lint: `All checks passed`
- Web build: 성공
- Docker 개발환경: Postgres/API/AI 기동 확인

## Important Policy Decisions

- 숨겨진 통화 녹음 구현 없음
- Accessibility API를 통한 통화 오디오 수집 없음
- Android는 `CallScreeningService` 기반 번호 선별 skeleton만 구현
- 음성 원본은 기본 미보관
- AI 판단은 확정 표현이 아닌 위험 가능성 안내 중심

## Next Recommended Work

1. Web console에서 실제 API flow를 브라우저로 점검
2. Web UI의 state/error handling 정리
3. Backend Alembic migration 도입
4. Web app Docker service 추가 여부 결정
5. Android는 이후 Retrofit/Hilt/Room 연동

