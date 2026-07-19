# SoriCall 현행 DB 레이아웃

- 작성 기준일: 2026-07-19
- 기준 소스: `services/api/app/models.py`, `services/api/alembic/versions/`
- 기본 키: UUID
- 운영 DB: PostgreSQL 호환
- 개발·테스트 DB: SQLite 호환 `GUID` 타입

## 1. 전체 논리 구조

```mermaid
flowchart LR
    AUTH[인증·사용자<br/>users<br/>phone_verifications<br/>refresh_tokens]
    FAMILY[가족·권한<br/>families<br/>seniors<br/>family_members<br/>guardians<br/>safe_words]
    ENROLL[등록·신뢰자료<br/>enrollment_invitations<br/>device_enrollments<br/>device_keys<br/>enrollment_qr_challenges<br/>media_import_sessions<br/>voice_profiles/samples<br/>face_profiles]
    CALL[통화·위험판정<br/>call_events<br/>call_sessions<br/>risk_decisions<br/>response_actions<br/>risk_events]
    NOTIFY[확인·알림<br/>family_confirmations<br/>device_push_tokens<br/>push_deliveries<br/>emergency_notifications]
    OPS[운영·규정<br/>consent_logs<br/>audit_logs<br/>risk_numbers]

    AUTH --> FAMILY
    FAMILY --> ENROLL
    FAMILY --> CALL
    ENROLL --> CALL
    CALL --> NOTIFY
    AUTH --> OPS
    CALL --> OPS
```

## 2. 핵심 ERD

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ FAMILIES : creates
    USERS ||--o{ FAMILY_MEMBERS : links
    USERS ||--o{ SENIORS : links
    USERS ||--o{ GUARDIANS : acts_as
    USERS ||--o{ DEVICE_KEYS : registers
    USERS ||--o{ CONSENT_LOGS : accepts
    USERS ||--o{ AUDIT_LOGS : performs

    FAMILIES ||--o{ SENIORS : protects
    FAMILIES ||--o{ FAMILY_MEMBERS : contains
    FAMILIES ||--o{ SAFE_WORDS : has
    FAMILIES ||--o{ ENROLLMENT_INVITATIONS : issues
    FAMILIES ||--o{ MEDIA_IMPORT_SESSIONS : imports

    SENIORS ||--o{ FAMILY_MEMBERS : has_contacts
    SENIORS ||--o{ GUARDIANS : has
    SENIORS ||--o{ DEVICE_ENROLLMENTS : enrolls
    SENIORS ||--o{ CALL_EVENTS : receives
    SENIORS ||--o{ CALL_SESSIONS : opens
    SENIORS ||--o{ RISK_EVENTS : generates
    SENIORS ||--o{ VIDEO_VERIFICATION_REQUESTS : requests

    FAMILY_MEMBERS ||--o{ ENROLLMENT_INVITATIONS : receives
    FAMILY_MEMBERS ||--o{ MEDIA_IMPORT_SESSIONS : targets
    FAMILY_MEMBERS ||--o{ VOICE_PROFILES : owns
    FAMILY_MEMBERS ||--o{ FACE_PROFILES : owns
    FAMILY_MEMBERS ||--o{ VIDEO_VERIFICATION_REQUESTS : answers

    DEVICE_KEYS ||--o{ ENROLLMENT_QR_CHALLENGES : signs
    DEVICE_KEYS ||--o{ ENROLLMENT_INVITATIONS : verifies
    ENROLLMENT_INVITATIONS ||--o{ ENROLLMENT_QR_CHALLENGES : challenges

    VOICE_PROFILES ||--o{ VOICE_SAMPLES : contains
    CONSENT_LOGS o|--o{ VOICE_PROFILES : authorizes

    CALL_EVENTS ||--o{ CALL_SESSIONS : groups
    CALL_EVENTS ||--o{ RISK_EVENTS : raises
    CALL_SESSIONS ||--o{ RISK_DECISIONS : evaluates
    CALL_SESSIONS ||--o{ RESPONSE_ACTIONS : executes
    CALL_SESSIONS ||--o{ FAMILY_CONFIRMATIONS : requests
    VOICE_PROFILES o|--o{ RISK_DECISIONS : compared_in
    RISK_DECISIONS ||--o{ RESPONSE_ACTIONS : determines

    GUARDIANS ||--o{ DEVICE_PUSH_TOKENS : owns
    GUARDIANS ||--o{ EMERGENCY_NOTIFICATIONS : receives
    FAMILY_CONFIRMATIONS ||--o{ PUSH_DELIVERIES : sends
    DEVICE_PUSH_TOKENS ||--o{ PUSH_DELIVERIES : targets
    RISK_EVENTS ||--o{ EMERGENCY_NOTIFICATIONS : triggers
    EMERGENCY_NOTIFICATIONS o|--o{ FAMILY_CONFIRMATIONS : supports
```

## 3. 테이블 목록

| 도메인 | 테이블 | 역할 |
|---|---|---|
| 인증 | `users` | 사용자 계정과 역할 |
| 인증 | `phone_verifications` | 휴대전화 OTP 요청·검증·소비 상태 |
| 인증 | `refresh_tokens` | 회전형 로그인 갱신 토큰 |
| 가족 | `families` | 데이터 접근의 가족 경계 |
| 가족 | `seniors` | 통화 보호 대상 |
| 가족 | `family_members` | 확인 가족 및 가족 전화번호 |
| 가족 | `guardians` | 보호자·알림 수신자 연결 |
| 가족 | `safe_words` | 가족 안전문구 해시 |
| 등록 | `enrollment_invitations` | 링크·QR·직접 등록 초대 |
| 등록 | `device_enrollments` | 보호 대상 Android 기기 등록 |
| 등록 | `device_keys` | QR 서명 검증용 공개키 |
| 등록 | `enrollment_qr_challenges` | 단기 QR challenge |
| 등록 | `media_import_sessions` | 외부 음성·영상 자료 반입 |
| 생체 | `voice_profiles` | 가족 음성 임베딩 프로필 |
| 생체 | `voice_samples` | 음성 샘플 검증 메타데이터 |
| 생체 | `face_profiles` | 얼굴 참조와 검증 결과 |
| 생체 | `video_verification_requests` | 통화 중 영상 확인 요청 |
| 통화 | `call_events` | 기존 통화 이벤트 요약 |
| 통화 | `call_sessions` | 특허 흐름 단위 통화 세션 |
| 판정 | `risk_decisions` | 순차 위험 분석 결과 |
| 판정 | `response_actions` | 판정별 대응 명령과 실행 결과 |
| 판정 | `risk_numbers` | 위험 전화번호 해시 목록 |
| 판정 | `risk_events` | 사용자에게 노출할 위험 사건 |
| 확인 | `family_confirmations` | 확인 가족에게 보낸 확인 요청 |
| 알림 | `device_push_tokens` | 보호자 기기 푸시 토큰 |
| 알림 | `push_deliveries` | 푸시 발송 시도와 결과 |
| 알림 | `emergency_notifications` | 위험 사건별 긴급 알림 |
| 규정 | `consent_logs` | 동의 종류·버전·수락 증적 |
| 운영 | `audit_logs` | 주요 변경 감사 기록 |

## 4. 인증·사용자 레이아웃

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email UK "nullable/구버전 호환"
        string phone_number "indexed"
        string display_name
        string role
        text password_hash
        datetime created_at
        datetime updated_at
    }
    PHONE_VERIFICATIONS {
        uuid id PK
        string phone_number "indexed"
        text code_hash
        string purpose
        datetime expires_at
        datetime verified_at
        datetime consumed_at
        int attempts
        datetime created_at
    }
    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        text token_hash UK
        datetime expires_at
        datetime revoked_at
        datetime created_at
    }
    USERS ||--o{ REFRESH_TOKENS : owns
```

설계 포인트:

- 신규 UI의 로그인 식별자는 휴대전화 번호다.
- `users.email`은 nullable이며 현재 이메일 가입 화면에서는 사용하지 않는다.
- OTP 원문과 새로고침 토큰 원문은 저장하지 않고 해시를 저장한다.
- `verified_at`, `consumed_at`, `revoked_at`으로 재사용을 방지한다.

## 5. 가족·권한 레이아웃

```mermaid
erDiagram
    FAMILIES {
        uuid id PK
        string name
        uuid created_by FK
        datetime created_at
    }
    SENIORS {
        uuid id PK
        uuid family_id FK
        uuid user_id FK
        string name
        string member_type
        string relation_code
        string protection_status
        string phone_number
        text phone_number_hash
        string phone_number_last4
        int birth_year
        datetime created_at
    }
    FAMILY_MEMBERS {
        uuid id PK
        uuid family_id FK
        uuid protected_user_id FK
        uuid user_id FK
        string name
        string relation
        string member_type
        string relation_code
        bool is_primary_contact
        int notification_priority
        bool notify_enabled
        string phone_number
        text phone_number_hash
        string phone_number_last4
        bool is_verified
        string approval_status
        string trust_level
        uuid approved_by FK
        datetime approved_at
        datetime revoked_at
        string revocation_reason
        datetime created_at
    }
    GUARDIANS {
        uuid id PK
        uuid senior_id FK
        uuid user_id FK
        string relation
        int priority
        bool notify_enabled
        datetime created_at
    }
    SAFE_WORDS {
        uuid id PK
        uuid family_id FK
        text word_hash
        string hint
        uuid updated_by FK
        datetime updated_at
    }

    FAMILIES ||--o{ SENIORS : contains
    FAMILIES ||--o{ FAMILY_MEMBERS : contains
    SENIORS ||--o{ FAMILY_MEMBERS : confirmation_contacts
    SENIORS ||--o{ GUARDIANS : notifies
    FAMILIES ||--o{ SAFE_WORDS : secures
```

`family_members.protected_user_id`로 확인 가족을 특정 보호 대상에 종속시킨다. 동일 가족 그룹 안에서도 보호 대상별 확인 가족 목록과 승인 상태가 분리된다.

## 6. 등록·신뢰자료 레이아웃

```mermaid
erDiagram
    ENROLLMENT_INVITATIONS {
        uuid id PK
        uuid family_id FK
        uuid family_member_id FK
        string channel
        string requested_assets
        string status
        text token_hash UK
        datetime sent_at
        datetime expires_at
        datetime phone_verified_at
        datetime used_at
        uuid device_key_id FK
        datetime device_verified_at
        string liveness_action
        datetime liveness_expires_at
        datetime liveness_verified_at
        datetime completed_at
    }
    DEVICE_ENROLLMENTS {
        uuid id PK
        uuid senior_id FK
        text token_hash UK
        string status
        datetime phone_verified_at
        datetime permissions_confirmed_at
        datetime expires_at
        datetime completed_at
    }
    DEVICE_KEYS {
        uuid id PK
        uuid user_id FK
        string device_id
        string algorithm
        text public_key_der_b64
        string fingerprint UK
        bool active
    }
    ENROLLMENT_QR_CHALLENGES {
        uuid id PK
        uuid invitation_id FK
        uuid device_key_id FK
        string challenge_hash
        datetime expires_at
        datetime verified_at
        datetime consumed_at
    }
    VOICE_PROFILES {
        uuid id PK
        uuid family_member_id FK
        string display_name
        string status
        uuid consent_id FK
        text embedding
        string embedding_model
        string embedding_version
        int quality_score
        datetime enrolled_at
    }
    VOICE_SAMPLES {
        uuid id PK
        uuid voice_profile_id FK
        text object_key
        text audio_ref
        int duration_ms
        int sample_rate
        string mime_type
        string purpose
        bool retained
        string content_hash
        int size_bytes
        string validation_status
        datetime deleted_at
    }
    FACE_PROFILES {
        uuid id PK
        uuid family_member_id FK
        text image_ref
        string status
        bool consent_accepted
        int match_score
        string content_hash
        int size_bytes
        string validation_status
        datetime consented_at
        datetime deleted_at
    }

    FAMILY_MEMBERS ||--o{ ENROLLMENT_INVITATIONS : receives
    SENIORS ||--o{ DEVICE_ENROLLMENTS : enrolls
    DEVICE_KEYS ||--o{ ENROLLMENT_QR_CHALLENGES : signs
    ENROLLMENT_INVITATIONS ||--o{ ENROLLMENT_QR_CHALLENGES : creates
    FAMILY_MEMBERS ||--o{ VOICE_PROFILES : owns
    VOICE_PROFILES ||--o{ VOICE_SAMPLES : contains
    FAMILY_MEMBERS ||--o{ FACE_PROFILES : owns
```

## 7. 외부 자료 반입 레이아웃

`media_import_sessions`는 실제 미디어 바이너리보다 반입·검증·동의 상태를 관리한다.

| 컬럼군 | 컬럼 | 의미 |
|---|---|---|
| 대상 | `family_id`, `family_member_id` | 자료가 속할 가족과 인물 |
| 원본 정보 | `source`, `filename`, `declared_mime_type` | 사용자가 제공한 정보 |
| 서버 검증 | `detected_mime_type`, `content_hash`, `size_bytes` | 탐지·무결성 결과 |
| 상태 | `status`, `quality_status`, `failure_code` | 처리 단계와 실패 원인 |
| 신뢰 | `trust_level` | 외부 자료의 초기 신뢰 등급 |
| 증적 | `validated_at`, `phone_verified_at`, `consented_at` | 각 검증 단계 완료시각 |
| 보존 | `expires_at`, `purged_at` | 자동 폐기 기준과 결과 |

## 8. 통화·위험 판정 레이아웃

```mermaid
erDiagram
    CALL_EVENTS {
        uuid id PK
        uuid senior_id FK
        text phone_number_hash
        string phone_number_last4
        string direction
        string caller_type
        int risk_score
        string risk_level
        string action_taken
        datetime occurred_at
    }
    CALL_SESSIONS {
        uuid id PK
        uuid senior_id FK
        uuid call_event_id FK
        text caller_number_hash
        string caller_number_last4
        string direction
        bool family_number_matched
        uuid matched_family_member_id FK
        bool suspected
        string status
        datetime started_at
        datetime ended_at
    }
    RISK_DECISIONS {
        uuid id PK
        uuid call_session_id FK
        int sequence "UK with call_session_id"
        bool number_mismatch
        float speaker_similarity
        float spoof_probability
        int content_risk_score
        string family_response
        int face_match_score
        uuid voice_profile_id FK
        text transcript
        float transcript_confidence
        int risk_score
        string risk_level
        string decision
        text reason_codes
        string policy_version
        text model_versions_json
    }
    RESPONSE_ACTIONS {
        uuid id PK
        uuid call_session_id FK
        uuid risk_decision_id FK
        string action
        string status
        text failure_reason
        datetime requested_at
        datetime executed_at
    }
    RISK_EVENTS {
        uuid id PK
        uuid senior_id FK
        uuid call_event_id FK
        string event_type
        int risk_score
        string risk_level
        text reason_codes
        text summary
        datetime created_at
    }
    RISK_NUMBERS {
        uuid id PK
        text phone_number_hash
        string phone_number_last4
        string label
        string source
        int risk_score
        bool active
    }

    CALL_EVENTS ||--o{ CALL_SESSIONS : details
    CALL_SESSIONS ||--o{ RISK_DECISIONS : recalculates
    RISK_DECISIONS ||--o{ RESPONSE_ACTIONS : commands
    CALL_SESSIONS ||--o{ RESPONSE_ACTIONS : contains
    CALL_EVENTS ||--o{ RISK_EVENTS : raises
```

핵심 제약:

- `risk_decisions`는 `(call_session_id, sequence)` 복합 유일 제약을 갖는다.
- 최초 번호 판정과 이후 음성·내용·가족 응답 판정을 같은 세션에서 순차 보존한다.
- 전화번호 원문 대신 비교용 해시와 사용자 표시용 끝 4자리를 통화 테이블에 저장한다.
- `response_actions`는 요청 조치뿐 아니라 단말 실행 상태와 실패 원인까지 기록한다.

## 9. 가족 확인·알림 레이아웃

```mermaid
erDiagram
    FAMILY_CONFIRMATIONS {
        uuid id PK
        uuid call_session_id FK
        uuid family_member_id FK
        uuid guardian_id FK
        uuid notification_id FK
        string channel
        string status
        string response
        datetime requested_at
        datetime expires_at
        datetime responded_at
    }
    DEVICE_PUSH_TOKENS {
        uuid id PK
        uuid guardian_id FK
        text token UK
        string platform
        bool active
        datetime updated_at
    }
    PUSH_DELIVERIES {
        uuid id PK
        uuid confirmation_id FK
        uuid push_token_id FK
        string status
        int attempt_count
        text provider_message_id
        text error_message
        datetime sent_at
    }
    EMERGENCY_NOTIFICATIONS {
        uuid id PK
        uuid risk_event_id FK
        uuid guardian_id FK
        string status
        string response
        text message
        datetime sent_at
        datetime responded_at
    }

    FAMILY_CONFIRMATIONS ||--o{ PUSH_DELIVERIES : dispatches
    DEVICE_PUSH_TOKENS ||--o{ PUSH_DELIVERIES : delivers_to
    GUARDIANS ||--o{ DEVICE_PUSH_TOKENS : owns
    GUARDIANS ||--o{ EMERGENCY_NOTIFICATIONS : receives
    RISK_EVENTS ||--o{ EMERGENCY_NOTIFICATIONS : triggers
```

## 10. 삭제 및 보존 규칙

모델에 선언된 주요 `ON DELETE CASCADE` 흐름:

```mermaid
flowchart TD
    U[users 삭제] --> RT[refresh_tokens]
    U --> DK[device_keys]
    U --> CL[consent_logs]

    F[families 삭제] --> S[seniors]
    F --> FM[family_members]
    F --> EI[enrollment_invitations]
    F --> MI[media_import_sessions]

    S --> DE[device_enrollments]
    S --> G[guardians]
    S --> CE[call_events]
    S --> CS[call_sessions]
    S --> RE[risk_events]

    FM --> VP[voice_profiles]
    VP --> VS[voice_samples]
    FM --> FP[face_profiles]

    CS --> RD[risk_decisions]
    CS --> RA[response_actions]
    CS --> FC[family_confirmations]
    FC --> PD[push_deliveries]
```

주의사항:

- 일부 FK는 `CASCADE`가 없으므로 사용자·위험 이벤트 등 상위 데이터 삭제 전에 참조 정리가 필요하다.
- 음성·얼굴은 `deleted_at`을 사용하는 논리 삭제 필드도 갖고 있다.
- 외부 반입 자료는 `expires_at`과 `purged_at`으로 만료·폐기 상태를 관리한다.
- 운영 보존기간과 개인정보 삭제 SLA는 DB 모델 외의 운영 정책으로 추가 확정해야 한다.

## 11. 인덱스 및 유일 제약

| 테이블 | 인덱스·제약 |
|---|---|
| `users` | `email` UNIQUE + INDEX, `phone_number` INDEX |
| `phone_verifications` | `phone_number` INDEX |
| `refresh_tokens` | `user_id` INDEX, `token_hash` UNIQUE + INDEX |
| `device_enrollments` | `senior_id` INDEX, `token_hash` UNIQUE + INDEX |
| `enrollment_invitations` | 가족·가족원 INDEX, `token_hash` UNIQUE + INDEX |
| `device_keys` | `user_id`, `device_id` INDEX, `fingerprint` UNIQUE + INDEX |
| `enrollment_qr_challenges` | 초대·기기키 INDEX |
| `media_import_sessions` | 가족·가족원·`content_hash` INDEX |
| `voice_samples`, `face_profiles` | `content_hash` INDEX |
| `call_sessions` | `caller_number_hash` INDEX |
| `risk_decisions` | `call_session_id` INDEX, 세션+순번 UNIQUE |
| `response_actions` | `call_session_id` INDEX |
| `family_confirmations` | `call_session_id` INDEX |
| `device_push_tokens` | `guardian_id` INDEX, `token` UNIQUE |
| `push_deliveries` | `confirmation_id` INDEX |
| `risk_numbers` | `phone_number_hash` INDEX |

## 12. 개인정보·보안 저장 원칙

| 데이터 | 현행 저장 방식 | 검토 사항 |
|---|---|---|
| 비밀번호 | 단방향 `password_hash` | 운영 해시 비용·알고리즘 점검 |
| OTP | `code_hash`, 만료·시도 횟수 | 발송 사업자 및 시도 제한 연동 |
| 토큰 | 초대·갱신 토큰 해시 | 원문 로그 출력 금지 |
| 전화번호 | 업무 테이블에는 원문과 해시가 혼재 | 원문 컬럼 암호화 또는 최소화 검토 |
| 안전문구 | `word_hash` | 힌트에 원문 포함 금지 |
| 음성 | 참조값·임베딩·검증 메타데이터 | 객체 저장소 암호화 및 수명주기 필요 |
| 얼굴 | 이미지 참조·검증 메타데이터 | 객체 저장소 삭제와 DB 논리 삭제 연계 |
| 통화 내용 | `risk_decisions.transcript` | 보존기간·마스킹·접근통제 필요 |
| 푸시 토큰 | 원문 토큰 | 암호화 저장과 폐기 정책 검토 |
| 감사정보 | 행위·대상·JSON 메타데이터 | 민감정보를 메타데이터에 넣지 않도록 제한 |

## 13. 물리 구현 시 권장 보완

1. `users.phone_number`에 정규화 기준을 적용한 유일 제약을 DB 수준에서도 명시한다.
2. `families.created_by`, `seniors.user_id`, `family_members.user_id` 등 권한 조회 FK에 인덱스를 추가한다.
3. `family_members`에 보호 대상·전화번호 해시 중복을 막는 업무 유일 제약을 검토한다.
4. `risk_numbers.phone_number_hash`는 활성 항목 기준 중복 방지 정책을 추가한다.
5. `reason_codes`, `requested_assets`, `model_versions_json`, `metadata_json`은 PostgreSQL 배열 또는 JSONB 전환을 검토한다.
6. `created_at`뿐 아니라 변경 가능한 핵심 테이블에 `updated_at`을 일관되게 둔다.
7. 생체·통화 내용·전화번호 원문 컬럼에 애플리케이션 또는 DB 암호화를 적용한다.
8. 파티셔닝 또는 보존 작업 대상은 `call_sessions`, `risk_decisions`, `audit_logs`, `push_deliveries` 순으로 검토한다.
