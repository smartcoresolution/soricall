# SoriCall 특허 정합화 작업 인수인계

작성일: 2026-07-13 KST  
목적: 다음 작업일에 현재 분석과 개발 계획을 바로 이어가기 위한 상태 기록

## 1. 저장소 기준 상태

- 브랜치: `main`
- 기준 커밋: `c9c5ac4 Refine SoriCall UI flow and API UUID handling`
- `main`과 `origin/main`은 분석 시점에 일치했다.
- 기존 애플리케이션 코드는 이번 분석 과정에서 수정하지 않았다.
- 마지막 재검증 결과:
  - Web production build 성공
  - API tests: `12 passed`
  - AI tests: `6 passed`

현재 별도 생성·첨부된 파일:

- `docs/MP_112026084869603_120260000224.pdf`: 특허출원서
- `docs/SoriCall_국가표준_시스템_상세설계서_v1.0_20260713.pdf`: 국가표준 형식 상세설계서
- `artifacts/soricall-web-screens-2026-07-13/`: Web 전체 화면 PNG 15개
- `artifacts/soricall-web-all-screens-2026-07-13.zip`: 화면 이미지 묶음

주의:

- 상세설계서는 `대외비`로 표시되어 있으므로 저장소 공개 여부와 문서 접근권한을 확인해야 한다.
- `.env.production`, 비밀번호, JWT 비밀키 등 운영 비밀정보는 커밋하지 않는다.

## 2. 오늘 수행한 분석

### 2.1 현재 구현 상태 분석

현재 저장소는 다음을 제공하는 시연 가능한 MVP이다.

- React/Vite 기반 모바일 Web/PWA
- FastAPI 업무 API와 PostgreSQL/SQLite 모델
- FastAPI Mock AI 분석 서비스
- Android Kotlin/Compose 및 `CallScreeningService` 골격
- 가족·어르신·보호자·안심 단어 등록
- 전화번호 기반 위험 평가
- 위험번호·반복전화·심야전화 규칙
- 음성 프로필·얼굴 프로필·화상 확인 데이터 흐름
- 보호자 알림·응답 데이터 흐름

운영 제품 기준 주요 부족사항:

- JWT는 발급하지만 API 라우트의 인증·권한검사에 연결되지 않음
- Web이 JWT를 API 요청의 `Authorization` 헤더로 보내지 않음
- 실제 AI 모델·STT·합성음 탐지가 아닌 Mock/규칙 기반 구현
- 실제 FCM 전송이 아닌 Placeholder
- 실제 통화 오디오 분석 미구현
- Android 실제 서버 연동과 통화 대응이 미완료
- Alembic migration 없음
- E2E·부하·접근성·보안 시험 부족

### 2.2 국가표준 형식 상세설계서 분석

문서는 52쪽, 17개 장 구성으로 요구사항·화면·프로그램·DB·인터페이스·보안·운영·추적표를 포함한다.

강점:

- `FR/NFR → SCR → PGM → TBL → IF → TST` 추적구조
- 고령 사용자 행동 중심 UI 원칙
- 개인정보·생체정보 최소수집·즉시삭제 원칙
- 성능·가용성·배포·롤백·모니터링까지 포함

보완사항:

- 표지는 Ver. 1.0이지만 검토·승인이 미완료
- 실제 국가표준명·표준번호·발행기관 근거가 명확하지 않음
- Spring Boot와 FastAPI 등 기술스택 표현이 현재 코드와 불일치
- 문서 API·DB와 현재 구현 API·DB의 차이가 큼
- 시험 ID는 있지만 상세 시험절차와 증적이 없음
- 성능·가용성 수치는 검증되지 않은 기준안

### 2.3 특허출원서 분석

특허출원서 주요 정보:

- 발명의 명칭: 등록 가족 정보 및 사칭 위험도 기반 가족 사칭 전화 차단 방법
- 출원인: 스마트코아솔루션 주식회사
- 발명자: 장관종
- 심사청구 표시
- 방법 청구항 1개
- PDF만으로는 실제 접수번호·접수 완료·심사 상태를 확인할 수 없음

청구항 1의 기술 흐름:

1. 가족 전화번호·음성 사전등록, 선택적 얼굴 등록
2. 어르신 단말 수신전화 발신번호 확인
3. 등록 가족 번호와 불일치 시 의심 전화 분류
4. 발신자와 등록 가족 음성 유사도 산출
5. AI 생성·보이스클로닝·합성음 의심도 산출
6. 통화음성 STT 및 위험표현 분석
7. 가족에게 실제 통화 여부 확인 요청
8. `전화했음/전화하지 않음/모르겠음` 응답 수신
9. 복수 지표를 통합한 사칭 위험도 산출
10. 유지·추가확인·저장번호 재통화·차단·가족 알림

특허 작성상 검토 필요사항:

- 하나의 독립항에 너무 많은 단계가 함께 기재됨
- 방법항 1개뿐이며 시스템·장치·기록매체·종속항이 없음
- `중 적어도 하나를 통합`이라는 표현의 기술적 명확성 검토 필요
- 실제 통화 오디오·전사·차단의 OS·통신·법률상 실시 가능성 검증 필요
- 등록 가능성·침해·권리범위는 변리사 검토 필요

## 3. 특허와 현재 코드의 차이

| 특허 구성 | 현재 상태 | 핵심 차이 |
|---|---|---|
| 가족 번호 등록 | 부분 구현 | 복수 번호·소유 검증·필수조건 없음 |
| 가족 음성 등록 | Mock 구현 | 모든 가족의 필수 등록을 보장하지 않음 |
| 전화 수신 | Android 골격 | 서버의 등록 가족 DB와 연결되지 않음 |
| 번호 불일치 분류 | API 구현 | Web 수동 입력 중심 |
| 화자 유사도 | Mock AI | 실제 통화 음성과 연결되지 않음 |
| 합성음 탐지 | Mock AI | 실제 모델 없음 |
| STT·내용 분석 | Mock/규칙 기반 | 실제 통화 전사 없음 |
| 가족 확인 | 부분 구현 | FCM Placeholder, 응답 후 재산출 없음 |
| 통합 위험도 | 미완료 | 번호 위험과 AI 위험이 분리됨 |
| 얼굴 결과 반영 | 미완료 | 결과 저장만 하고 위험도에 미반영 |
| 실제 대응 | 부분 구현 | Web 안내 중심, 실제 재통화·차단 미완료 |

핵심 판단:

- 특허 아이디어와 코드의 개념적 정합성은 높다.
- 개별 모듈은 대부분 골격 또는 Mock으로 존재한다.
- 청구항 전체를 실제 수신 통화 한 건에서 연속 수행하는 E2E 흐름은 없다.
- 가장 중요한 미구현 요소는 `CallSessionOrchestrator`와 통합 `RiskDecisionService`이다.

## 4. 특허 정합화 개발 계획

### Phase 0. 결정사항 확정

- Android/제조사/통신사별 수신번호·오디오·차단 가능 범위
- 통화 분석·전사·자동차단 법률 검토
- 얼굴 기능은 선택 기능으로 유지
- AI 분석 실패·가족 미응답 시 안전정책
- 실제 FCM과 대체 알림 채널

### Phase 1. 요구사항과 추적표

- 청구항 각 단계를 `PAT-01~PAT-09` 개발 요구사항으로 정의
- 코드·DB·API·화면·시험 ID 연결
- 특허 정합성 E2E 시나리오 정의

### Phase 2. DB와 migration

추가 후보 모델:

- `FamilyPhone`
- `Device`
- `CallSession`
- `VoiceAnalysis`
- `ContentAnalysis`
- `FamilyConfirmation`
- `RiskDecision`
- `ResponseAction`
- `RiskPolicy`
- `RiskPattern`

Alembic을 도입하고 기존 `CallEvent`, `RiskEvent`, `EmergencyNotification` 데이터를 안전하게 이전한다.

### Phase 3. 가족 등록 강화

- 가족별 복수 전화번호
- 번호 정규화·HMAC·소유 검증
- 음성 등록 상태와 동의 상태 검증
- 얼굴 동의를 선택 항목으로 수정
- 동의 철회·프로필 파기 처리

### Phase 4. CallSession과 번호검증

- Android 수신 이벤트에서 `CallSession` 생성
- 서버의 등록 가족 번호와 실제 비교
- 초기 위험 결과를 Android에 반환
- 기존 로컬 끝 4자리 데모 규칙 제거

### Phase 5. AI 분석 연결

- API 서버에 화자·합성음·STT·내용분석 클라이언트 구현
- 테스트 음성 fixture로 전체 E2E를 먼저 완성
- Mock과 실제 모델을 동일 Port/Adapter 인터페이스로 분리
- 분석결과에 모델 버전·신뢰도 저장

### Phase 6. 가족 확인

- 실제 FCM 전송
- 응답코드를 `CALLED/NOT_CALLED/UNKNOWN`으로 정규화
- 만료·재시도·중복·멱등 처리
- 응답 수신 후 위험도 자동 재산출

### Phase 7. 통합 위험도

상세설계서 초기 기준안:

```text
R_base = 20·N + 15·V + 25·S + 25·C + 15·F
R_total = clamp(R_base + FaceAdj + PolicyAdj, 0, 100)
```

등급 경계를 코드 전체에서 다음으로 통일한다.

```text
LOW       0~29
CAUTION  30~59
HIGH     60~79
CRITICAL 80~100
```

현재 코드의 `31/61/81` 경계는 수정 대상이다.

### Phase 8. 대응 오케스트레이션

- `ALLOW/VERIFY/RECALL/BLOCK/AUTO_BLOCK/ALERT` 결정
- 단말 기능에 따라 차단 불가 시 강한 경고로 대체
- 저장된 가족번호 재통화
- 실제 수행 결과와 실패 이유 기록

### Phase 9. 보안·개인정보·감사

- 모든 API에 JWT·역할·가족관계 권한 적용
- Web Bearer token 전송
- 음성·전사 임시데이터 TTL과 즉시삭제
- 감사로그·정책버전·모델버전 기록
- 데이터 보존·파기 배치
- Rate Limit, 로그인 실패 제한, 민감로그 필터링

### Phase 10. 특허 정합성 시험 증적

위험 시나리오:

```text
미등록 번호
+ 가족과 유사한 음성
+ 합성음 의심도 높음
+ 송금 요구
+ 가족 NOT_CALLED 응답
= CRITICAL
→ 통화 종료/차단
→ 가족 알림
→ 전체 판단 근거 저장
```

정상 시나리오:

```text
등록 가족 번호
+ 높은 화자 유사도
+ 낮은 합성음 의심도
+ 위험 표현 없음
+ 가족 CALLED 응답
= LOW
→ 통화 유지
```

## 5. 다음 작업일 권장 시작점

바로 실제 통화 오디오 구현부터 시작하지 않는다. 먼저 `Milestone 1: 특허 정합 시뮬레이터`를 구축한다.

첫 구현 단위:

1. `PAT-01~PAT-09` 추적 문서 작성
2. Alembic 도입
3. `CallSession`, `RiskDecision`, `ResponseAction`, `FamilyConfirmation` 모델 추가
4. `POST /api/v1/call-sessions` 추가
5. 기존 번호 위험 평가를 `CallSession`에 연결
6. 테스트 fixture로 AI 분석 호출
7. 가족 응답 후 `RiskDecision` 재산출
8. E2E API 테스트 추가

권장 서비스 구조:

```text
CallSessionOrchestrator
  ├─ NumberMatchService
  ├─ SpeakerVerificationClient
  ├─ SyntheticVoiceClient
  ├─ ConversationRiskClient
  ├─ FamilyConfirmationService
  ├─ RiskDecisionService
  └─ ResponseActionService
```

## 6. 다음 작업 시 주의사항

- 기존 API와 Web 흐름을 한 번에 제거하지 말고 호환성을 유지한다.
- DB 변경 전에 테스트와 백업·마이그레이션 경로를 먼저 만든다.
- 실제 통화 녹음이나 Accessibility API를 이용한 숨은 오디오 수집은 구현하지 않는다.
- 실제 통화 음성 연동은 법률·OS 가능 범위 확정 후 진행한다.
- 특허 정합성은 API 이름이 아니라 처리 순서·입력·결정·조치의 연결로 판단한다.
- Mock 결과와 실제 모델 결과를 운영 환경에서 혼동하지 않도록 명시적으로 분리한다.
- 특허출원서와 상세설계서의 법적·사업적 최종 판단은 변리사·법률·개인정보 전문가 검토 대상으로 남긴다.

