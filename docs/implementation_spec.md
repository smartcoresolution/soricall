# 안심소리 가족콜 — SoriCall 구현 상세기술서

> **서비스명:** 안심소리 가족콜  
> **앱 이름:** SoriCall  
> **문서 목적:** OpenAI Codex 또는 개발자가 바로 구현을 시작할 수 있도록 만든 MVP/확장형 구현 상세기술서  
> **작성일:** 2026-06-26  
> **대상:** Android 앱, 보호자 앱, FastAPI 백엔드, AI 음성 분석 모듈, 관리자 기능

---

## 0. Codex 실행용 핵심 지시문

아래 문장을 Codex 첫 작업 프롬프트로 사용할 수 있다.

```text
You are implementing the MVP for "안심소리 가족콜 / SoriCall", an AI family-call safety app for seniors.

Build a monorepo with:
1. Android app in Kotlin + Jetpack Compose under apps/android
2. FastAPI backend under services/api
3. AI analysis service under services/ai
4. PostgreSQL schema and migrations under infra/db
5. Docker Compose for local development under infra/docker
6. Markdown docs under docs

Important constraints:
- Do NOT implement hidden call recording.
- Do NOT use Accessibility API for call audio recording.
- Implement Android CallScreeningService for number-based call screening.
- MVP should support family member registration, guardian registration, safe word, suspicious-call alert, risk scoring, push notification placeholder, voice sample upload, speaker verification adapter interface, anti-spoofing adapter interface, and risk event history.
- For AI models, start with mock adapters and clean interfaces. Do not block MVP on model training.
- Use privacy-first design: consent logs, encrypted storage notes, no raw voice retention by default, store voice embeddings only in production mode.

Deliver working scaffolding, API contracts, DB migrations, unit tests, and README instructions.
```

---

# 1. 프로젝트 개요

## 1.1 서비스 정의

**안심소리 가족콜(SoriCall)**은 어르신이 가족을 사칭한 보이스피싱 전화를 받을 때, 가족 목소리·가족 연락처·안심 단어·보호자 알림·위험 대화 패턴을 종합하여 위험을 알려주는 **AI 가족 사칭 보이스피싱 차단 및 가족 안심 통화 앱**이다.

## 1.2 핵심 문제

최근 보이스피싱은 다음 형태로 진화한다.

- 가족 목소리를 흉내 내거나 AI로 합성한 음성 사용
- “엄마 나 사고 났어”, “납치됐어”, “급히 돈 보내줘”와 같은 감정적 압박
- 전화를 끊지 못하게 유도
- 가족·경찰·검찰·금융기관 사칭
- 악성 앱 설치, 원격제어 앱 설치, 계좌 이체 유도

## 1.3 MVP 목표

MVP에서는 **실시간 통화 음성 녹음/분석**을 무리하게 구현하지 않는다.  
대신 Android 정책상 구현 가능한 범위에서 다음 기능을 우선 구현한다.

```text
가족 등록
+ 보호자 등록
+ 안심 단어 등록
+ 수신 전화 위험번호 판단
+ CallScreeningService 기반 전화 선별
+ 의심 전화 보호자 알림
+ 통화 후 음성 샘플 분석
+ 가족 음성 프로필 등록
+ 위험 이벤트 기록
+ 관리자용 위험 로그 조회
```

## 1.4 MVP에서 제외할 항목

다음은 MVP에서 제외한다.

- 일반 앱의 숨겨진 통화 녹음
- Accessibility API를 이용한 통화 음성 수집
- 통화 중 상대방 음성의 상시 실시간 분석
- 금융기관 계좌이체 차단 직접 제어
- 통신사망 수준의 발신번호 변작 검증
- 완전 자동 보이스피싱 판단

---

# 2. 공식 제약 및 설계 전제

## 2.1 Android Call Screening

Android에서는 `CallScreeningService`를 사용하여 수신·발신 전화에 대한 차단, 허용, 무음 처리, 위험 표시 등의 기능을 구현할 수 있다.

공식 문서:

- Android Screen calls: https://developer.android.com/develop/connectivity/telecom/dialer-app/screen-calls
- CallScreeningService API: https://developer.android.com/reference/android/telecom/CallScreeningService

## 2.2 Google Play 민감 권한 정책

민감 데이터 접근 권한은 앱의 핵심 기능에 필요한 범위에서만 요청해야 한다. 특히 Accessibility API를 통화 녹음 우회 수단으로 사용하면 안 된다.

공식 문서:

- Google Play Sensitive Information Policy: https://support.google.com/googleplay/android-developer/answer/16558241

## 2.3 Codex 작업 방식 전제

Codex는 저장소를 읽고, 파일을 수정하고, 테스트·린트·타입체크를 실행하면서 기능 구현을 진행하는 코딩 에이전트로 활용한다.

공식 문서:

- OpenAI Codex Developers: https://developers.openai.com/codex
- Using Codex with ChatGPT plan: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan

---

# 3. 전체 시스템 아키텍처

## 3.1 구성요소

```text
[어르신 Android 앱: SoriCall]
    │
    ├─ 가족/보호자 등록
    ├─ 안심 단어 확인
    ├─ 수신 전화 위험 표시
    ├─ CallScreeningService
    ├─ 의심 전화 버튼
    ├─ 통화 후 음성 샘플 업로드
    └─ 위험 이벤트 조회

          │ REST API / HTTPS / JWT
          ▼

[API 서버: FastAPI]
    │
    ├─ 사용자/기기 인증
    ├─ 가족 그룹 관리
    ├─ 음성 프로필 관리
    ├─ 위험번호/위험 이벤트 관리
    ├─ 보호자 알림 요청
    ├─ AI 분석 요청 라우팅
    └─ 관리자 API

          │ internal HTTP / queue
          ▼

[AI 분석 서비스]
    │
    ├─ 화자 인증 adapter
    ├─ 합성음성 탐지 adapter
    ├─ STT adapter
    ├─ 보이스피싱 문장 탐지
    └─ 최종 위험 점수 산출

          │
          ▼

[PostgreSQL + Object Storage]
    │
    ├─ 사용자/가족/보호자
    ├─ 동의 이력
    ├─ 음성 embedding
    ├─ 통화 이벤트
    ├─ 위험 이벤트
    └─ 감사 로그
```

## 3.2 권장 Monorepo 구조

```text
soricall/
├─ README.md
├─ .env.example
├─ .gitignore
├─ apps/
│  └─ android/
│     ├─ README.md
│     ├─ app/
│     ├─ build.gradle.kts
│     ├─ settings.gradle.kts
│     └─ gradle/
├─ services/
│  ├─ api/
│  │  ├─ README.md
│  │  ├─ pyproject.toml
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ core/
│  │  │  ├─ api/
│  │  │  ├─ models/
│  │  │  ├─ schemas/
│  │  │  ├─ services/
│  │  │  └─ tests/
│  │  └─ alembic/
│  └─ ai/
│     ├─ README.md
│     ├─ pyproject.toml
│     ├─ app/
│     │  ├─ main.py
│     │  ├─ adapters/
│     │  ├─ pipelines/
│     │  ├─ scoring/
│     │  └─ tests/
├─ infra/
│  ├─ docker/
│  │  ├─ docker-compose.yml
│  │  ├─ api.Dockerfile
│  │  └─ ai.Dockerfile
│  └─ db/
│     ├─ init.sql
│     └─ migrations/
├─ docs/
│  ├─ implementation_spec.md
│  ├─ api_contract.md
│  ├─ privacy_security.md
│  ├─ android_design.md
│  └─ ai_design.md
└─ scripts/
   ├─ dev_up.sh
   ├─ dev_down.sh
   └─ seed_demo_data.py
```

---

# 4. 사용자 역할

## 4.1 역할 정의

| 역할 | 설명 |
|---|---|
| Senior | 어르신 사용자 |
| Guardian | 자녀·보호자 |
| FamilyMember | 가족 목소리 등록 대상 |
| Admin | 서비스 관리자 |
| AIService | 내부 AI 분석 서비스 |

## 4.2 주요 사용자 시나리오

### 시나리오 A: 보호자가 부모님을 등록

```text
1. 보호자 앱 또는 웹에서 회원가입
2. 부모님 프로필 생성
3. 부모님 스마트폰에 SoriCall 설치
4. QR 코드 또는 초대코드로 연결
5. 가족 연락처 등록
6. 안심 단어 등록
7. 가족 음성 샘플 등록
```

### 시나리오 B: 모르는 번호에서 전화 수신

```text
1. 전화 수신
2. CallScreeningService 실행
3. 번호가 가족 연락처인지 확인
4. 위험번호 DB 조회
5. 위험 점수 계산
6. 어르신에게 경고 표시 또는 무음/차단
7. 위험 이벤트 저장
8. 필요 시 보호자에게 알림
```

### 시나리오 C: 가족 사칭 의심 상황

```text
1. 어르신이 통화 중 "가족 확인" 버튼 누름
2. 보호자에게 긴급 알림 전송
3. 보호자가 "내가 전화한 것 아님" 선택
4. 어르신 앱에 강한 경고 표시
5. "전화를 끊고 저장된 가족 번호로 다시 전화하세요" 안내
```

### 시나리오 D: 통화 후 음성 분석

```text
1. 사용자가 음성 파일 또는 샘플 녹음 업로드
2. AI 분석 서비스 호출
3. 가족 음성 유사도 계산
4. 합성음성 가능성 계산
5. 위험 문장 탐지
6. 최종 위험 점수 저장
7. 분석 결과 표시
```

---

# 5. Android 앱 상세 설계

## 5.1 기술 스택

| 항목 | 선택 |
|---|---|
| 언어 | Kotlin |
| UI | Jetpack Compose |
| 아키텍처 | MVVM + Repository |
| 네트워크 | Retrofit + OkHttp |
| 로컬 DB | Room |
| 암호화 | Android Keystore + EncryptedSharedPreferences |
| 비동기 | Kotlin Coroutines + Flow |
| DI | Hilt |
| 알림 | Firebase Cloud Messaging |
| 최소 SDK | Android 10, API 29 권장 |
| 타깃 SDK | 최신 안정 버전 |

## 5.2 Android 패키지 구조

```text
com.ansimsori.soricall/
├─ MainActivity.kt
├─ SoriCallApplication.kt
├─ core/
│  ├─ network/
│  ├─ security/
│  ├─ database/
│  ├─ permissions/
│  └─ util/
├─ feature/
│  ├─ onboarding/
│  ├─ family/
│  ├─ safeword/
│  ├─ callguard/
│  ├─ voiceprofile/
│  ├─ emergency/
│  ├─ history/
│  └─ settings/
├─ service/
│  ├─ SoriCallScreeningService.kt
│  ├─ SoriFirebaseMessagingService.kt
│  └─ EmergencyOverlayService.kt
└─ domain/
   ├─ model/
   ├─ repository/
   └─ usecase/
```

## 5.3 주요 화면

| 화면 | 기능 |
|---|---|
| OnboardingScreen | 서비스 설명, 권한 안내 |
| RoleSelectScreen | 어르신/보호자 선택 |
| SeniorLinkScreen | QR/초대코드 연결 |
| FamilyListScreen | 가족 연락처 목록 |
| FamilyRegisterScreen | 가족 등록 |
| SafeWordScreen | 안심 단어 등록·수정 |
| CallGuardSettingsScreen | 위험 알림 설정 |
| SuspiciousCallScreen | 의심 전화 경고 |
| EmergencyButtonScreen | 가족 확인·보호자 호출 |
| VoiceProfileScreen | 가족 음성 등록 |
| VoiceAnalysisScreen | 음성 샘플 분석 |
| RiskHistoryScreen | 위험 이벤트 이력 |
| SettingsScreen | 개인정보, 동의, 삭제 |

## 5.4 권한 설계

### 필수 권한

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

### 조건부 권한

```xml
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.READ_CONTACTS" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

주의사항:

- `READ_CONTACTS`는 가족 등록 기능에 필요한 경우에만 요청한다.
- 가능한 경우 Android Contact Picker를 우선 사용한다.
- `RECORD_AUDIO`는 가족 음성 등록 또는 사용자가 명시적으로 누른 녹음 기능에서만 사용한다.
- 통화 녹음을 위해 `RECORD_AUDIO`를 우회 사용하면 안 된다.

## 5.5 CallScreeningService 구현 개요

### AndroidManifest 예시

```xml
<service
    android:name=".service.SoriCallScreeningService"
    android:permission="android.permission.BIND_SCREENING_SERVICE"
    android:exported="true">
    <intent-filter>
        <action android:name="android.telecom.CallScreeningService" />
    </intent-filter>
</service>
```

### Kotlin 예시

```kotlin
class SoriCallScreeningService : CallScreeningService() {

    override fun onScreenCall(callDetails: Call.Details) {
        val handle = callDetails.handle
        val phoneNumber = handle?.schemeSpecificPart ?: return

        val risk = runBlocking {
            callRiskRepository.evaluateIncomingNumber(phoneNumber)
        }

        val response = CallResponse.Builder()
            .setDisallowCall(risk.shouldBlock)
            .setRejectCall(risk.shouldReject)
            .setSkipCallLog(false)
            .setSkipNotification(false)
            .setSilenceCall(risk.shouldSilence)
            .build()

        respondToCall(callDetails, response)

        if (risk.score >= 60) {
            emergencyNotifier.notifyGuardians(phoneNumber, risk)
        }
    }
}
```

## 5.6 위험 전화 UI 정책

| 위험도 | UI |
|---:|---|
| 0~30 | 일반 표시 |
| 31~60 | 노란색 주의 |
| 61~80 | 빨간색 경고, 보호자 알림 |
| 81~100 | 강한 경고, 차단 또는 무음 권장 |

어르신 친화 UI 원칙:

- 글자 크게
- 버튼 2개 이하
- “위험”, “가족 확인”, “끊고 다시 전화”처럼 직접적인 문구 사용
- 작은 설명보다 음성 안내·진동·색상 경고 사용
- 복잡한 AI 점수는 숨기고 “주의/위험/매우 위험”으로 표시

---

# 6. 백엔드 API 상세 설계

## 6.1 기술 스택

| 항목 | 선택 |
|---|---|
| 언어 | Python 3.11+ |
| 프레임워크 | FastAPI |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| DB | PostgreSQL |
| 인증 | JWT Access/Refresh Token |
| 파일 | S3 호환 Object Storage 또는 로컬 개발 저장소 |
| 테스트 | pytest |
| 포맷 | ruff, black |
| API 문서 | OpenAPI 자동 문서 |

## 6.2 FastAPI 구조

```text
services/api/app/
├─ main.py
├─ core/
│  ├─ config.py
│  ├─ security.py
│  ├─ database.py
│  └─ exceptions.py
├─ api/
│  ├─ deps.py
│  └─ v1/
│     ├─ auth.py
│     ├─ users.py
│     ├─ families.py
│     ├─ devices.py
│     ├─ voice_profiles.py
│     ├─ call_events.py
│     ├─ risk_events.py
│     ├─ emergency.py
│     └─ admin.py
├─ models/
├─ schemas/
├─ services/
│  ├─ auth_service.py
│  ├─ family_service.py
│  ├─ risk_service.py
│  ├─ notification_service.py
│  ├─ voice_profile_service.py
│  └─ ai_client.py
└─ tests/
```

## 6.3 주요 API 목록

### 인증

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/auth/register` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 |
| POST | `/api/v1/auth/logout` | 로그아웃 |

### 가족 그룹

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/families` | 가족 그룹 생성 |
| GET | `/api/v1/families/{family_id}` | 가족 그룹 조회 |
| POST | `/api/v1/families/{family_id}/members` | 가족 구성원 추가 |
| POST | `/api/v1/families/{family_id}/invite` | 초대코드 생성 |
| POST | `/api/v1/families/join` | 초대코드로 참여 |

### 어르신·보호자

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/seniors` | 어르신 프로필 생성 |
| GET | `/api/v1/seniors/{senior_id}` | 어르신 프로필 조회 |
| POST | `/api/v1/seniors/{senior_id}/guardians` | 보호자 연결 |
| GET | `/api/v1/seniors/{senior_id}/guardians` | 보호자 목록 |

### 안심 단어

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/families/{family_id}/safe-word` | 안심 단어 등록 |
| PUT | `/api/v1/families/{family_id}/safe-word` | 안심 단어 수정 |
| POST | `/api/v1/families/{family_id}/safe-word/verify` | 안심 단어 확인 |

### 전화 위험 평가

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/calls/evaluate` | 전화번호 위험 평가 |
| POST | `/api/v1/calls/events` | 통화 이벤트 저장 |
| GET | `/api/v1/calls/events` | 통화 이벤트 목록 |

### 위험 이벤트

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/risk-events` | 위험 이벤트 생성 |
| GET | `/api/v1/risk-events` | 위험 이벤트 목록 |
| GET | `/api/v1/risk-events/{event_id}` | 위험 이벤트 상세 |

### 긴급 알림

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/emergency/confirm-family-call` | 가족 확인 요청 |
| POST | `/api/v1/emergency/respond` | 보호자 응답 |
| POST | `/api/v1/emergency/notify` | 보호자 알림 발송 |

### 음성 프로필

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/voice-profiles` | 가족 음성 프로필 생성 |
| POST | `/api/v1/voice-profiles/{id}/samples` | 음성 샘플 업로드 |
| POST | `/api/v1/voice-profiles/{id}/enroll` | 음성 embedding 등록 |
| DELETE | `/api/v1/voice-profiles/{id}` | 음성 프로필 삭제 |

### 음성 분석

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/voice/analyze` | 음성 파일 분석 |
| GET | `/api/v1/voice/analysis/{analysis_id}` | 분석 결과 조회 |

---

# 7. 데이터베이스 설계

## 7.1 ERD 개요

```text
users
 ├─ devices
 ├─ family_members
 ├─ consent_logs
 └─ audit_logs

families
 ├─ family_members
 ├─ safe_words
 ├─ seniors
 └─ guardians

seniors
 ├─ guardians
 ├─ call_events
 ├─ risk_events
 └─ devices

voice_profiles
 ├─ voice_samples
 └─ voice_embeddings

risk_events
 ├─ call_events
 └─ emergency_notifications
```

## 7.2 PostgreSQL DDL 초안

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(50),
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('SENIOR', 'GUARDIAN', 'FAMILY_MEMBER', 'ADMIN')),
    password_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE families (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE family_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    relation VARCHAR(50),
    phone_number VARCHAR(50),
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE seniors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(50),
    birth_year INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE guardians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_id UUID NOT NULL REFERENCES seniors(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    relation VARCHAR(50),
    priority INT NOT NULL DEFAULT 1,
    notify_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('ANDROID', 'IOS', 'WEB')),
    device_name VARCHAR(100),
    push_token TEXT,
    app_version VARCHAR(50),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE safe_words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    word_hash TEXT NOT NULL,
    hint VARCHAR(255),
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_member_id UUID NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'ENROLLED', 'FAILED', 'DELETED')),
    consent_id UUID,
    embedding_vector BYTEA,
    embedding_model VARCHAR(100),
    embedding_version VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    enrolled_at TIMESTAMPTZ
);

CREATE TABLE voice_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_profile_id UUID NOT NULL REFERENCES voice_profiles(id) ON DELETE CASCADE,
    object_key TEXT,
    duration_ms INT,
    sample_rate INT,
    mime_type VARCHAR(100),
    purpose VARCHAR(30) NOT NULL CHECK (purpose IN ('ENROLLMENT', 'ANALYSIS')),
    retain_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE call_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_id UUID NOT NULL REFERENCES seniors(id) ON DELETE CASCADE,
    phone_number_hash TEXT NOT NULL,
    phone_number_last4 VARCHAR(4),
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('INCOMING', 'OUTGOING')),
    caller_type VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (caller_type IN ('FAMILY', 'UNKNOWN', 'RISK_NUMBER', 'BLOCKED')),
    risk_score INT NOT NULL DEFAULT 0,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW'
        CHECK (risk_level IN ('LOW', 'CAUTION', 'HIGH', 'CRITICAL')),
    action_taken VARCHAR(50),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    senior_id UUID NOT NULL REFERENCES seniors(id) ON DELETE CASCADE,
    call_event_id UUID REFERENCES call_events(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    risk_score INT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    reason_codes TEXT[] NOT NULL DEFAULT '{}',
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE emergency_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_event_id UUID REFERENCES risk_events(id) ON DELETE CASCADE,
    guardian_id UUID REFERENCES guardians(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'RESPONDED')),
    response VARCHAR(30)
        CHECK (response IN ('REAL_CALL', 'NOT_ME', 'UNKNOWN')),
    sent_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ
);

CREATE TABLE consent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL,
    version VARCHAR(30) NOT NULL,
    accepted BOOLEAN NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address VARCHAR(100),
    user_agent TEXT
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 7.3 개인정보 최소화 원칙

- 전화번호는 원문 저장을 피하고 hash + last4만 저장한다.
- 원본 음성은 등록 완료 후 삭제하는 것이 기본값이다.
- 실제 운영에서는 embedding vector도 암호화 저장한다.
- 안심 단어는 원문 저장 금지, hash 저장.
- 보호자 알림 로그는 필요한 기간만 보관한다.

---

# 8. AI 분석 서비스 상세 설계

## 8.1 AI 서비스 역할

AI 서비스는 MVP에서 다음 4가지 기능을 제공한다.

```text
1. 가족 음성 embedding 생성
2. 가족 음성 유사도 비교
3. 합성음성/딥페이크 의심도 계산
4. 보이스피싱 문장 위험도 분석
```

## 8.2 AI 서비스 기술 스택

| 항목 | 선택 |
|---|---|
| 언어 | Python 3.11+ |
| 프레임워크 | FastAPI |
| 음성 처리 | torchaudio, librosa |
| 모델 | PyTorch |
| 화자 인증 | ECAPA-TDNN 계열 adapter |
| 합성음성 탐지 | AASIST/RawNet/LCNN 계열 adapter |
| STT | Whisper adapter 또는 외부 STT adapter |
| NLP | rule-based MVP + KoELECTRA/KLUE adapter 확장 |
| 배포 | Docker |
| 테스트 | pytest |

## 8.3 AI 서비스 폴더 구조

```text
services/ai/app/
├─ main.py
├─ core/
│  ├─ config.py
│  └─ logging.py
├─ schemas/
│  ├─ voice.py
│  ├─ risk.py
│  └─ common.py
├─ adapters/
│  ├─ speaker_verification.py
│  ├─ anti_spoofing.py
│  ├─ stt.py
│  └─ nlp_risk.py
├─ pipelines/
│  ├─ enrollment_pipeline.py
│  ├─ voice_analysis_pipeline.py
│  └─ text_risk_pipeline.py
├─ scoring/
│  ├─ risk_score.py
│  └─ reason_codes.py
└─ tests/
```

## 8.4 Adapter Interface

### Speaker Verification

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SpeakerEmbeddingResult:
    embedding: bytes
    model_name: str
    model_version: str
    quality_score: float

@dataclass
class SpeakerSimilarityResult:
    similarity: float
    matched: bool
    threshold: float

class SpeakerVerificationAdapter(ABC):
    @abstractmethod
    def create_embedding(self, audio_path: str) -> SpeakerEmbeddingResult:
        pass

    @abstractmethod
    def compare(self, audio_path: str, enrolled_embedding: bytes) -> SpeakerSimilarityResult:
        pass
```

### Anti-Spoofing

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AntiSpoofingResult:
    spoof_probability: float
    is_suspicious: bool
    model_name: str
    model_version: str

class AntiSpoofingAdapter(ABC):
    @abstractmethod
    def analyze(self, audio_path: str) -> AntiSpoofingResult:
        pass
```

### STT

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class STTResult:
    text: str
    language: str
    confidence: float

class STTAdapter(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> STTResult:
        pass
```

### NLP Risk

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TextRiskResult:
    risk_score: int
    reason_codes: list[str]
    detected_keywords: list[str]
    summary: str

class NLPRiskAdapter(ABC):
    @abstractmethod
    def analyze_text(self, text: str) -> TextRiskResult:
        pass
```

## 8.5 위험 문장 Rule-based MVP

### 위험 키워드

```python
RISK_PATTERNS = {
    "MONEY_TRANSFER": [
        "돈 보내", "송금", "계좌", "입금", "현금", "인출", "이체"
    ],
    "FAMILY_IMPERSONATION": [
        "엄마 나", "아빠 나", "사고 났어", "납치", "다쳤어", "휴대폰 고장"
    ],
    "KEEP_ON_CALL": [
        "전화 끊지 마", "끊으면 안 돼", "계속 통화", "아무에게도 말하지 마"
    ],
    "APP_INSTALL": [
        "앱 설치", "원격제어", "링크 눌러", "문자 보낸 주소", "보안 앱"
    ],
    "AUTHORITY_IMPERSONATION": [
        "검찰", "경찰", "금감원", "금융감독원", "수사", "대포통장", "구속"
    ],
    "LOAN_SCAM": [
        "저금리", "대환대출", "신용등급", "보증료", "상환 계좌"
    ]
}
```

## 8.6 최종 위험 점수 계산

```python
def calculate_final_risk_score(
    number_risk: int,
    speaker_mismatch: bool,
    spoof_probability: float,
    text_risk_score: int,
    asks_money: bool,
    asks_app_install: bool,
    asks_keep_on_call: bool,
) -> dict:
    score = 0
    reasons = []

    score += number_risk

    if speaker_mismatch:
        score += 25
        reasons.append("SPEAKER_MISMATCH")

    if spoof_probability >= 0.70:
        score += 25
        reasons.append("SYNTHETIC_VOICE_SUSPECTED")
    elif spoof_probability >= 0.50:
        score += 15
        reasons.append("SYNTHETIC_VOICE_POSSIBLE")

    score += min(text_risk_score, 40)

    if asks_money:
        score += 30
        reasons.append("MONEY_TRANSFER_REQUEST")

    if asks_app_install:
        score += 40
        reasons.append("APP_INSTALL_REQUEST")

    if asks_keep_on_call:
        score += 25
        reasons.append("KEEP_ON_CALL_PRESSURE")

    score = min(score, 100)

    if score >= 81:
        level = "CRITICAL"
    elif score >= 61:
        level = "HIGH"
    elif score >= 31:
        level = "CAUTION"
    else:
        level = "LOW"

    return {
        "risk_score": score,
        "risk_level": level,
        "reason_codes": reasons,
    }
```

---

# 9. API Request/Response 예시

## 9.1 전화번호 위험 평가

### Request

```json
{
  "senior_id": "6eb7c9b5-d9ad-409f-b670-111111111111",
  "phone_number": "+821012345678",
  "direction": "INCOMING"
}
```

### Response

```json
{
  "risk_score": 72,
  "risk_level": "HIGH",
  "caller_type": "UNKNOWN",
  "action_recommended": "WARN_AND_NOTIFY_GUARDIAN",
  "reason_codes": [
    "UNKNOWN_NUMBER",
    "FAMILY_IMPERSONATION_RISK"
  ],
  "message_for_senior": "모르는 번호입니다. 가족이라고 해도 전화를 끊고 저장된 가족 번호로 다시 확인하세요."
}
```

## 9.2 가족 확인 요청

### Request

```json
{
  "senior_id": "6eb7c9b5-d9ad-409f-b670-111111111111",
  "call_event_id": "11111111-d9ad-409f-b670-111111111111",
  "message": "가족 사칭 의심 전화입니다. 실제 가족 통화인지 확인해 주세요."
}
```

### Response

```json
{
  "emergency_event_id": "22222222-d9ad-409f-b670-111111111111",
  "notified_guardians": 2,
  "status": "SENT"
}
```

## 9.3 음성 분석

### Request

```http
POST /api/v1/voice/analyze
Content-Type: multipart/form-data

senior_id=<uuid>
family_member_id=<uuid>
audio_file=<wav_file>
analysis_mode=POST_CALL_SAMPLE
```

### Response

```json
{
  "analysis_id": "33333333-d9ad-409f-b670-111111111111",
  "speaker_similarity": 0.42,
  "speaker_matched": false,
  "spoof_probability": 0.78,
  "text": "엄마 나 사고 났어 돈 좀 보내줘",
  "risk_score": 95,
  "risk_level": "CRITICAL",
  "reason_codes": [
    "SPEAKER_MISMATCH",
    "SYNTHETIC_VOICE_SUSPECTED",
    "MONEY_TRANSFER_REQUEST",
    "FAMILY_IMPERSONATION"
  ],
  "message_for_senior": "가족 목소리처럼 들려도 AI 조작 가능성이 있습니다. 전화를 끊고 저장된 가족 번호로 다시 확인하세요."
}
```

---

# 10. 보안 및 개인정보 설계

## 10.1 보안 원칙

| 항목 | 정책 |
|---|---|
| 동의 | 가족 음성 등록 전 명시적 동의 |
| 목적 제한 | 보이스피싱 탐지 목적 외 사용 금지 |
| 최소 수집 | 전화번호·음성 원본 최소화 |
| 암호화 | 전송 TLS, 저장 AES-256 권장 |
| 삭제권 | 가족 음성 프로필 삭제 기능 제공 |
| 접근통제 | 관리자 접근 최소화 |
| 감사로그 | 민감정보 접근 기록 |
| 원본 음성 | 운영 기본값은 저장하지 않음 |

## 10.2 금지 사항

```text
- 가족 음성을 TTS/Voice Cloning 학습용으로 사용 금지
- 광고/마케팅 목적으로 음성정보 활용 금지
- 보호자 동의 없이 어르신 통화 내용 저장 금지
- Accessibility API로 통화 녹음 금지
- 앱 설명에 없는 민감 권한 요청 금지
```

## 10.3 동의 항목

앱 최초 사용 시 최소 다음 동의를 받는다.

| 동의 | 필수 여부 |
|---|---|
| 서비스 이용약관 | 필수 |
| 개인정보 처리방침 | 필수 |
| 가족 음성정보 수집·이용 동의 | 음성 등록 시 필수 |
| 보호자 알림 수신 동의 | 보호자 필수 |
| 마케팅 수신 동의 | 선택 |

---

# 11. 관리자 기능

## 11.1 관리자 웹 MVP

MVP에서는 간단한 관리자 API 또는 FastAPI Admin 형태로 시작한다.

관리자 기능:

- 전체 사용자 수 조회
- 위험 이벤트 목록 조회
- 위험번호 등록/해제
- 위험 키워드 관리
- AI 분석 이력 조회
- 동의 로그 조회
- 음성 원본 보관 여부 점검
- 신고 건 상태 관리

## 11.2 관리자 화면 후보

| 화면 | 기능 |
|---|---|
| Dashboard | 일별 위험 이벤트 수 |
| Users | 사용자 조회 |
| Families | 가족 그룹 조회 |
| Risk Events | 위험 이벤트 상세 |
| Risk Numbers | 위험번호 DB 관리 |
| Voice Profiles | 음성 프로필 상태 |
| Audit Logs | 감사로그 |

---

# 12. 로컬 개발 환경

## 12.1 Docker Compose

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    container_name: soricall-postgres
    environment:
      POSTGRES_USER: soricall
      POSTGRES_PASSWORD: soricall_dev
      POSTGRES_DB: soricall
    ports:
      - "5432:5432"
    volumes:
      - soricall_pg_data:/var/lib/postgresql/data
      - ../db/init.sql:/docker-entrypoint-initdb.d/init.sql

  api:
    build:
      context: ../../services/api
      dockerfile: ../../infra/docker/api.Dockerfile
    container_name: soricall-api
    env_file:
      - ../../.env
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  ai:
    build:
      context: ../../services/ai
      dockerfile: ../../infra/docker/ai.Dockerfile
    container_name: soricall-ai
    env_file:
      - ../../.env
    ports:
      - "8100:8100"

volumes:
  soricall_pg_data:
```

## 12.2 `.env.example`

```env
APP_ENV=local
API_HOST=0.0.0.0
API_PORT=8000
AI_SERVICE_URL=http://ai:8100

DATABASE_URL=postgresql+psycopg://soricall:soricall_dev@postgres:5432/soricall

JWT_SECRET=change-me-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=14

STORAGE_BACKEND=local
LOCAL_STORAGE_DIR=/tmp/soricall_uploads

FCM_SERVER_KEY=replace-in-production
```

---

# 13. 테스트 계획

## 13.1 Backend Unit Tests

| 테스트 | 기준 |
|---|---|
| 회원가입 | 정상 가입, 중복 가입 차단 |
| 로그인 | JWT 발급 확인 |
| 가족 생성 | family row 생성 |
| 안심 단어 | 원문 저장 금지, hash 검증 |
| 전화 위험 평가 | 위험번호/가족번호/모르는 번호 점수 확인 |
| 위험 이벤트 | event 생성, 조회 |
| 음성 분석 요청 | AI client mock 응답 처리 |

## 13.2 AI Service Tests

| 테스트 | 기준 |
|---|---|
| Speaker adapter mock | embedding 생성 |
| Anti-spoofing mock | probability 반환 |
| STT mock | text 반환 |
| NLP rule | 위험 문장 reason code 추출 |
| Final scoring | score/level 정확성 |

## 13.3 Android Tests

| 테스트 | 기준 |
|---|---|
| Onboarding UI | 권한 설명 표시 |
| 가족 목록 | API 결과 렌더링 |
| 긴급 버튼 | 보호자 알림 API 호출 |
| CallScreeningService | 번호 위험도에 따른 response 생성 |
| 로컬 DB | call event cache 저장 |
| 접근성 | 큰 글자, 큰 버튼 확인 |

---

# 14. MVP 개발 단계

## Phase 0. 저장소 초기화

목표:

```text
monorepo 생성
기본 README 작성
Docker Compose 작성
FastAPI skeleton 작성
Android skeleton 작성
AI service skeleton 작성
```

Codex 지시문:

```text
Create the monorepo scaffold for SoriCall exactly according to docs/implementation_spec.md.
Set up:
- services/api FastAPI project with health check
- services/ai FastAPI project with health check
- infra/docker/docker-compose.yml with Postgres, API, AI
- apps/android empty Kotlin Jetpack Compose project placeholder README if Android Gradle generation is not possible in the current environment
- root README with local development instructions
Run formatters/tests where possible.
```

완료 기준:

- `docker compose up`으로 API/AI/Postgres 실행
- `/health` 응답
- README 존재

## Phase 1. DB 및 API 구현

목표:

```text
PostgreSQL schema
Alembic migrations
Auth
Family
Senior
Guardian
SafeWord
CallEvent
RiskEvent
```

Codex 지시문:

```text
Implement the FastAPI backend data model and API endpoints for SoriCall MVP.
Use SQLAlchemy 2.x, Pydantic schemas, Alembic migrations, and pytest.
Do not implement production-grade OAuth yet; use JWT email/password auth.
Implement:
- users
- families
- family_members
- seniors
- guardians
- devices
- safe_words
- call_events
- risk_events
- consent_logs
- audit_logs
Add tests for each service.
```

완료 기준:

- 마이그레이션 실행 가능
- API 테스트 통과
- OpenAPI 문서 자동 생성

## Phase 2. 위험 점수 엔진

목표:

```text
번호 기반 위험 평가
가족 연락처 여부 확인
위험번호 목록
위험 점수 산출
보호자 알림 트리거
```

Codex 지시문:

```text
Implement the risk scoring engine in services/api.
Create a RiskService that evaluates incoming phone numbers.
Inputs:
- senior_id
- phone_number
- direction
Signals:
- known family phone number
- unknown number
- risk number list
- repeated calls
- late-night call
Outputs:
- risk_score
- risk_level
- action_recommended
- reason_codes
- message_for_senior
Add unit tests for all risk levels.
```

완료 기준:

- 위험 점수 계산 테스트 통과
- 위험 이벤트 자동 생성 가능

## Phase 3. AI Service Mock 구현

목표:

```text
AI adapter 인터페이스 구현
mock 모델로 응답 반환
음성 분석 API 구현
```

Codex 지시문:

```text
Implement the AI service for SoriCall using adapter interfaces and mock model implementations.
Endpoints:
- POST /health
- POST /v1/voice/enroll
- POST /v1/voice/analyze
Adapters:
- SpeakerVerificationAdapter
- AntiSpoofingAdapter
- STTAdapter
- NLPRiskAdapter
For MVP, use deterministic mock outputs based on filename/text fixture.
Add tests for voice analysis pipeline and risk score output.
```

완료 기준:

- `/v1/voice/analyze` 응답 정상
- AI service tests 통과

## Phase 4. Android MVP

목표:

```text
SoriCall Android 앱 기본 화면 구현
가족 등록
안심 단어
긴급 알림
위험 이력
CallScreeningService skeleton
```

Codex 지시문:

```text
Implement the Android MVP screens for SoriCall using Kotlin and Jetpack Compose.
Screens:
- onboarding
- role select
- senior link
- family list
- family registration
- safe word
- suspicious call warning
- emergency confirm
- voice profile
- risk history
Use MVVM, Repository, Retrofit, Hilt, Room.
Implement SoriCallScreeningService skeleton and local risk evaluation repository.
Do not implement hidden call recording.
```

완료 기준:

- 앱 빌드 성공
- 주요 화면 이동 가능
- 위험 이력 표시 가능
- CallScreeningService 컴파일 가능

## Phase 5. 보호자 알림

목표:

```text
보호자 푸시 알림 구조
FCM placeholder
보호자 응답 API
어르신 앱 경고 업데이트
```

Codex 지시문:

```text
Implement guardian notification flow.
Backend:
- emergency notification create
- guardian response endpoint
- FCM placeholder service
Android:
- receive push placeholder
- show emergency confirmation screen
- allow guardian to respond: REAL_CALL, NOT_ME, UNKNOWN
Add tests and mock FCM service.
```

완료 기준:

- 위험 이벤트 → 보호자 알림 row 생성
- 보호자 응답 저장
- 어르신 앱에서 상태 조회 가능

## Phase 6. 음성 프로필 등록

목표:

```text
가족 음성 샘플 업로드
음성 프로필 생성
AI enroll 호출
embedding 저장
```

Codex 지시문:

```text
Implement voice profile enrollment flow.
Backend:
- upload sample
- create voice profile
- call AI /v1/voice/enroll
- store embedding bytes or mock embedding
Android:
- record short voice sample only after explicit user action
- upload sample
- show enrollment status
Security:
- make raw sample retention configurable
- default to delete raw samples after enrollment in production mode
```

완료 기준:

- 샘플 업로드 가능
- mock embedding 저장 가능
- 삭제 정책 구현

---

# 15. Definition of Done

## 15.1 기능 완료 기준

MVP 완료는 다음 조건을 만족해야 한다.

```text
[Backend]
- 회원가입/로그인 가능
- 가족 그룹 생성 가능
- 어르신/보호자 연결 가능
- 안심 단어 등록 가능
- 전화번호 위험 평가 가능
- 위험 이벤트 저장 가능
- 음성 분석 mock API 연동 가능

[Android]
- 앱 실행 가능
- 가족 등록 가능
- 안심 단어 화면 가능
- 의심 전화 버튼 가능
- 위험 이력 조회 가능
- CallScreeningService skeleton 동작 가능

[AI]
- 음성 등록 mock 가능
- 음성 분석 mock 가능
- 위험 점수 반환 가능

[Security]
- 동의 로그 저장
- 안심 단어 hash 저장
- 전화번호 hash 저장
- 통화녹음 우회 기능 없음

[Docs]
- README 실행 방법
- API 문서
- 개인정보 처리 설계 문서
```

## 15.2 품질 기준

| 항목 | 기준 |
|---|---|
| Backend test coverage | 핵심 서비스 70% 이상 |
| API validation | Pydantic schema 적용 |
| Error handling | 400/401/403/404/500 구분 |
| Logging | 민감정보 masking |
| Android UI | 어르신 친화 큰 글자 |
| Security | 원문 민감정보 저장 최소화 |
| Docs | 로컬 실행 방법 명확 |

---

# 16. 앱 문구

## 16.1 앱 소개

```text
SoriCall은 가족 목소리를 사칭한 보이스피싱을 예방하기 위한 AI 안심 통화 앱입니다.
모르는 번호, 가족 사칭 의심 전화, 돈 요구, 앱 설치 요구 등 위험 신호를 감지하고,
필요할 때 보호자에게 즉시 알림을 보냅니다.
```

## 16.2 어르신 경고 문구

```text
가족 목소리처럼 들려도 AI로 조작될 수 있습니다.
전화를 끊고 저장된 가족 번호로 다시 전화하세요.
```

```text
돈을 보내라고 하면 위험할 수 있습니다.
가족 확인 버튼을 눌러 보호자에게 확인하세요.
```

```text
앱을 설치하라고 하거나 링크를 누르라고 하면 전화를 끊으세요.
```

## 16.3 보호자 알림 문구

```text
부모님이 가족 사칭 의심 전화를 받고 있습니다.
실제로 가족이 전화한 것이 맞습니까?
```

버튼:

```text
[내가 전화함]
[내가 아님, 사칭 의심]
[확인 어려움]
```

---

# 17. 위험 Reason Code 정의

| Code | 의미 |
|---|---|
| UNKNOWN_NUMBER | 가족 연락처에 없는 번호 |
| RISK_NUMBER_MATCH | 위험번호 DB 매칭 |
| FAMILY_IMPERSONATION_RISK | 가족 사칭 가능성 |
| SPEAKER_MISMATCH | 등록 가족 음성과 불일치 |
| SYNTHETIC_VOICE_POSSIBLE | 합성음성 가능성 |
| SYNTHETIC_VOICE_SUSPECTED | 합성음성 강한 의심 |
| MONEY_TRANSFER_REQUEST | 송금 요구 |
| APP_INSTALL_REQUEST | 앱 설치 요구 |
| KEEP_ON_CALL_PRESSURE | 통화 유지 강요 |
| AUTHORITY_IMPERSONATION | 수사기관 사칭 |
| LOAN_SCAM_PATTERN | 대출 사기 패턴 |
| SAFE_WORD_FAILED | 안심 단어 불일치 |
| GUARDIAN_NOT_ME | 보호자가 본인 통화 아님 응답 |

---

# 18. 향후 확장 설계

## 18.1 통신사 제휴형

통신사와 제휴하면 다음 기능 가능성이 높아진다.

- 발신번호 변작 검증
- 통신망 위험번호 DB 연동
- 통화 전 사기 의심 안내
- 통신사 AI 콜스크리닝 연계

## 18.2 금융기관 제휴형

금융기관과 제휴하면 다음 기능 가능성이 있다.

- 어르신 계좌 송금 전 보이스피싱 위험 경고
- 고액 이체 시 보호자 확인
- 사기 의심 계좌 정보 연동

## 18.3 제조사/기본 전화앱 제휴형

스마트폰 제조사 또는 기본 전화앱 수준으로 들어가면 다음 기능을 검토할 수 있다.

- 통화 중 온디바이스 위험 탐지
- 실시간 통화 내용 요약
- 실시간 가족 사칭 음성 탐지
- 기본 전화 UI에 경고 표시

---

# 19. 개발 우선순위 요약

## 반드시 먼저 만들 것

```text
1. 가족/보호자 등록
2. 안심 단어
3. 수신번호 위험 평가
4. 의심 전화 버튼
5. 보호자 알림
6. 위험 이벤트 기록
7. 음성 프로필 등록 mock
8. AI 분석 mock
```

## 나중에 만들 것

```text
1. 고성능 음성 AI 모델
2. 실시간 통화 음성 분석
3. 금융기관 연동
4. 통신사 연동
5. 지자체 관리자 대시보드
6. 통계 리포트
```

---

# 20. 최종 Codex 작업 순서

Codex에는 아래 순서로 작업을 나누어 맡긴다.

```text
Task 1: Create monorepo scaffold and local dev environment.
Task 2: Implement FastAPI backend models, migrations, and auth.
Task 3: Implement family, senior, guardian, safe word APIs.
Task 4: Implement call risk evaluation and risk events.
Task 5: Implement AI service mock adapters and voice analysis pipeline.
Task 6: Implement Android Jetpack Compose MVP screens.
Task 7: Implement Android CallScreeningService skeleton.
Task 8: Implement guardian emergency notification mock.
Task 9: Implement voice profile enrollment flow.
Task 10: Add tests, docs, and demo seed data.
```

---

# 21. README 초안

````markdown
# SoriCall — 안심소리 가족콜

AI 가족 사칭 보이스피싱 차단 및 가족 안심 통화 앱.

## Local Development

```bash
cp .env.example .env
cd infra/docker
docker compose up --build
```

API:

- http://localhost:8000/docs

AI:

- http://localhost:8100/docs

## Services

- apps/android: Android app
- services/api: FastAPI backend
- services/ai: AI analysis service
- infra/docker: local Docker Compose
- infra/db: database init and migrations

## MVP Features

- Family registration
- Senior/guardian linking
- Safe word
- Call risk evaluation
- Suspicious call event
- Guardian notification placeholder
- Voice profile enrollment mock
- Voice analysis mock

## Important Policy

This MVP does not implement hidden call recording.  
Do not use Accessibility API for call audio recording.
````

---

# 22. 개발자 주의사항

```text
1. 통화 녹음 우회 기능을 넣지 말 것.
2. AI 판단을 “확정”처럼 표현하지 말 것.
3. 앱 문구는 “위험 가능성”, “한 번 더 확인” 중심으로 작성할 것.
4. 음성정보는 생체성 정보이므로 동의·삭제·암호화를 기본으로 할 것.
5. MVP에서는 모델 정확도보다 사용자 흐름과 안전장치를 우선 구현할 것.
6. 앱 이름은 SoriCall, 서비스명은 안심소리 가족콜로 통일할 것.
```

---

# 23. 납품 산출물 체크리스트

| 산출물 | 파일/위치 |
|---|---|
| 구현 상세기술서 | `docs/implementation_spec.md` |
| API 명세 | `docs/api_contract.md` |
| 개인정보/보안 설계 | `docs/privacy_security.md` |
| Android 설계 | `docs/android_design.md` |
| AI 설계 | `docs/ai_design.md` |
| DB migration | `services/api/alembic/` |
| Docker Compose | `infra/docker/docker-compose.yml` |
| Android 앱 | `apps/android/` |
| API 서버 | `services/api/` |
| AI 서버 | `services/ai/` |
| 테스트 | 각 서비스 `tests/` |

---

## 문서 종료

이 문서는 **안심소리 가족콜 / SoriCall**의 MVP 구현을 Codex 또는 개발자가 바로 시작할 수 있도록 작성된 실행형 구현 상세기술서이다.
