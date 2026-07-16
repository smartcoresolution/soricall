# SoriCall Worklog

# 2026-07-16 — 부모님 Android 앱 연결·배포 흐름 개선

## Android 앱 연결 흐름

- 일반 홈페이지 설치 시 레거시 `설치 완료` 화면 대신 SoriCall 서비스 시작 화면을 표시하도록 초기 진입 상태를 변경했다.
- 부모님 초대 링크의 `device_token`을 Android 딥링크로 전달하고 암호화 저장하도록 구현했다.
- 앱 내부에서 초대 조회, 부모님 휴대전화 인증, Android 전화·마이크·알림 권한, 통화 선별 앱 역할 설정, 통화 보호 활성화를 진행하도록 연결했다.
- 이미 연결된 휴대전화는 홈으로, 위험 알림으로 실행된 경우에는 위험 분석·차단 화면으로 분기한다.

## 휴대전화 가입·로그인

- Android의 기존 이메일 가입·로그인을 웹과 동일한 휴대전화 번호 기반 방식으로 교체했다.
- 회원가입에 인증번호 발송·확인, 이름·비밀번호 입력, 약관 동의 흐름을 연결했다.
- 로그인 요청을 휴대전화 번호와 비밀번호 방식으로 변경했다.

## API 및 DB 수정

- Android 네트워크 계층에 기기 연결 초대 조회, 인증번호 발송·확인, 보호 활성화 API를 추가했다.
- `DEVICE_CONNECT:<UUID>`가 DB의 30자 제한을 초과해 발생하던 인증번호 API 500 오류를 확인했다.
- `phone_verifications.purpose`를 80자로 확장하는 모델 변경과 `20260716_03` Alembic 마이그레이션을 추가했다.
- 실행 중인 개발 PostgreSQL에도 컬럼 변경을 적용했으며 인증번호 요청의 `201 Created`를 확인했다.

## Android 운영 서명 및 배포

- 기존 서명 비밀번호를 복구할 수 없어 새로운 운영 키스토어 v2를 생성했다.
- 키스토어와 비밀번호는 Git 외부 `/home/soricall/.android`에 권한 `600`으로 저장했다.
- 앱 버전을 `0.3.3`, versionCode `6`으로 올렸다.
- Gradle DEX 메모리 부족을 해결하기 위해 JVM heap을 4GB로 설정했다.
- 새 키로 Release APK를 빌드하고 APK Signature Scheme v2 서명을 검증했다.
- 기존 운영 APK를 백업하고 `/var/www/soricall/downloads/soricall.apk`를 새 Release APK로 교체했다.
- 공개 다운로드 파일과 빌드 산출물의 SHA-256 일치 및 공개 APK 버전 `0.3.3`을 확인했다.

## 검증

- Web production build 성공
- Android Debug APK build 성공
- Android Release APK build 성공
- Release APK 서명 검증 성공
- 공개 APK 다운로드·해시·버전 검증 성공

## 운영 주의사항

- v2 키 도입 이전 서명으로 설치된 앱은 한 번 삭제한 뒤 새 APK를 설치해야 한다.
- 이후 업데이트는 반드시 `/home/soricall/.android/soricall-release-v2.jks`와 대응 비밀번호를 사용해야 한다.
- 키스토어와 비밀번호 파일은 별도 보안 저장소에 반드시 백업한다.

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
# 2026-07-14 — 개발 웹앱 6·7·8번 가족 등록 흐름 및 백업

## 완료 내용

- 확인 가족을 여러 명 등록하고, 등록 요청을 발송하는 화면(6번)을 구현했다.
- 초대받은 가족 본인이 직접 동의한 뒤 음성을 필수로 등록하고 얼굴 사진은 선택 등록하는 화면(7번)을 구현했다.
- 초대별 응답 대기/등록 완료 상태, 개발용 등록 화면 열기, 링크 재전송과 홈 요약 화면(8번)을 구현했다.
- 음성 등록 완료 시 해당 초대 상태를 `COMPLETED`로 갱신하도록 연결했다.
- 기존 enrollment invitation API와 Alembic migration을 개발환경에서 사용하도록 정리했다.

## 검증

- `npm run build` 성공
- Playwright 화면 6 테스트 통과
- Playwright 화면 7 초대 발송 테스트 통과
- Playwright 화면 8 등록현황/재전송 테스트 통과

## 백업

- `backups/soricall-work-20260714-2037.tgz`
- `.git`, `node_modules`, Playwright 결과물은 제외했다.

## 다음 작업

- GitHub 인증 갱신 후 현재 브랜치 변경사항을 commit/push하고 PR을 생성한다.
- 운영 전환 전 실제 SMS/카카오 알림 연동과 초대 토큰 기반 공개 등록 엔드포인트를 검토한다.

# 2026-07-15 — SoriMemo 정합 모바일 UI 개편 및 동의 화면 개선

## 디자인 개편

- `/home/scs_dev/velora/velora-frontend`의 SoriMemo 화면을 참고해 SoriCall을 동일 계열의 모바일 앱 디자인으로 개편했다.
- 데스크톱에서도 폭 430px, 높이 최대 824px의 앱 프레임으로 표시하고 실제 스마트폰에서는 기기 화면 높이를 사용하도록 구성했다.
- 크림색 배경, 청록색 주요 버튼, 코랄색 전화 아이콘, 굵은 한글 제목, 둥근 카드와 입력창을 공통 디자인 언어로 적용했다.
- 내용이 긴 화면은 브라우저 전체가 아니라 앱 프레임 내부에서 스크롤되도록 수정했다.
- 하단 내비게이션을 브라우저 하단이 아닌 앱 프레임 내부 하단에 배치했다.

## 시작·회원가입 흐름

- 첫 화면 우측 상단에 `회원가입` 버튼을 배치했다.
- `회원가입 → 가입 정보 입력 → 동의 절차 → 가입 완료` 순서로 연결했다.
- `서비스 시작`은 기존 가입자의 로그인 화면으로 연결했다.
- 첫 화면의 `앱으로 설치하기` 버튼과 설치 프롬프트 UI를 제거했다.
- 모든 비초기 화면 상단에 최초 화면으로 이동하는 `홈` 버튼을 추가했다.
- 임시 알림 종과 하드코딩 사용자 아바타를 제거했다.
- `1 / 3`, `2 / 3` 형태의 단계 숫자 표시는 전체 등록 화면에서 제거했다.

## 동의 화면

- 전체 동의 아래 필수 4개와 선택 1개 항목을 항상 표시하도록 레이아웃을 정리했다.
- 각 항목의 체크 동작과 세부내용 열기 동작을 분리했다.
- 오른쪽 화살표로 약관 세부내용을 펼치고 접는 아코디언 기능을 추가했다.
- 중복 이메일 오류를 화면 밖 토스트 대신 현재 동의 카드 내부의 오류 안내 박스로 표시한다.

## 검증

- `npm run build` 성공
- 시작 화면과 회원가입·동의 화면 이동 Playwright 테스트 통과
- 홈 버튼의 최초 화면 이동 Playwright 테스트 통과
- 필수·선택 동의 항목 표시 및 선택 테스트 통과
- 동의 세부내용 열기·닫기 테스트 통과
- 중복 이메일 오류의 동의 화면 내부 표시 테스트 통과

## 백업

- `backups/soricall-ui-work-20260715.tgz`
- `.git`, 의존성, 빌드 결과물, 테스트 결과물, 기존 백업은 제외한다.

# 2026-07-16 — 양방향 가족 통화 보호 가입 흐름

## 가입 경로 분리

- 회원가입과 동의를 먼저 완료한 뒤 `서비스 시작 → 가족 등록 → 보호 방법 선택` 순서로 흐름을 재구성했다.
- 회원가입 정보에 본인 휴대전화 번호를 추가했다.
- 가족의 관계·이름·전화번호를 먼저 등록한 뒤 `내 전화를 보호받고 싶어요`와 `부모님의 전화를 보호하고 싶어요` 중 하나를 선택한다.
- 직접 보호 경로는 가입자를 `SELF` 보호 대상으로 연결하고 앞서 등록한 자녀·손주에게 생체정보 등록 링크를 준비한다.
- 가족 도움 경로는 앞서 등록한 부모·조부모를 보호 대상으로 연결하고 부모님 휴대전화용 앱 설치·연결 링크를 준비한다.
- 두 경로 모두 확인 가족은 각자의 휴대전화에서 본인 동의 후 음성과 선택 얼굴정보를 등록하도록 안내한다.
- 보호받을 휴대전화에서는 최초 한 번 본인 확인과 통화 보호 활성화가 필요하다는 문구로 정리했다.

## 화면 및 API

- 시작 방법 선택 화면과 두 개의 큰 선택 카드를 모바일 디자인으로 추가했다.
- 직접 설정 경로에서는 가족관계 선택 대신 가입자 이름을 자동 입력하고 본인 휴대전화 번호만 연결한다.
- `ProtectedCallUserCreate.relation_code`에 `SELF`를 허용했다.
- 동의 완료 중 전역 팝업을 제거하고 버튼 내부 진행 상태와 가입 완료 카드의 고정 안내만 표시한다.
- 이메일 중심 가입·로그인을 휴대전화 번호와 6자리 인증번호 기반 흐름으로 전환했다.
- 휴대전화 인증번호의 만료, 시도 횟수, 검증·사용 완료 상태를 저장하는 모델과 마이그레이션을 추가했다.
- 보호 대상 가족 목록 조회와 삭제 기능을 추가하고 조부모 관계를 친가·외가로 세분화했다.
- 부모님 휴대전화 연결 초대, 번호 확인, 권한 확인, 보호 활성화를 처리하는 기기 등록 API와 공개 연결 화면을 추가했다.
- Android 앱의 운영 API 주소, 릴리스 서명, 설치 완료 안내 화면을 구성했다.
- Nginx에 APK 다운로드 MIME 타입과 브라우저 마이크 권한 정책을 추가했다.

## 검증

- Web production build 성공
- 기존 시작·가입·동의·보호 가족·확인 가족 화면 테스트 8개 통과
- 부모·조부모 직접 보호 경로 Playwright 테스트 통과
- API 전체 테스트 `48 passed`

## 추가 테스트

- 휴대전화 인증 가입·로그인과 미인증 가입 거부 API 테스트를 추가했다.
- 부모님 기기 초대부터 본인 확인, 권한 설정, 보호 활성화까지의 API 테스트를 추가했다.
- 본인 전화 직접 보호 및 기존 계정의 휴대전화 번호 보완 Playwright 테스트를 추가했다.
- 최종 Web production build는 성공했다.
- 최종 API 전체 테스트는 신규 휴대전화 가입 스키마와 기존 이메일 기반 테스트의 불일치로 `41 passed, 10 failed`였다.
- 최종 Playwright 실행은 설정된 개발 서버가 시작되지 않아 테스트 실행 전에 중단됐다.

## 백업

- `backups/soricall-work-20260716-1430.tgz`
- `.git`, 의존성, 빌드·테스트 결과물, 기존 백업과 Android 힙 덤프는 제외했다.
