# SoriCall 작업 기록 — 2026-07-14

## 작업 목적

특허출원서의 핵심 보호 흐름을 기준으로 Web·Android 화면을 재설계하고, 보호받을 가족과 확인 가족이라는 서비스 개념을 DB·API·클라이언트에 일관되게 반영한다.

## 서비스 개념 정리

- **보호받을 가족**: 보이스피싱으로부터 실제 통화 보호를 받는 부모 또는 조부모
- **확인 가족**: 의심전화 발생 시 실제 가족의 전화인지 확인하고 응답하는 가족
- 별도의 역할 선택 및 어르신 단말 연결 화면은 제거하고 가족 등록 흐름 안에서 자연스럽게 설정하도록 단순화
- 보호 관계는 아버지, 어머니, 할아버지, 할머니, 기타로 제한
- 확인 관계는 아들, 딸, 손자, 손녀, 배우자, 기타 가족으로 단순화

## Backend API 및 데이터 모델

- 보호받을 가족과 확인 가족을 구분하는 데이터 필드 및 응답 스키마 추가
- 보호받을 가족 생성·조회 API 구현
- 보호받을 가족별 확인 가족 생성·조회 API 구현
- 통화 세션 생성, 위험도 판정, 대응 액션 및 단말 결과 보고 흐름 구현
- 가족 확인 요청 및 응답 처리 구현
- AI 음성 분석 서비스 연결과 실패 시 안전한 대체 처리 구현
- FCM 알림 전송·재시도 처리 구현
- JWT 접근 토큰, 갱신 토큰 회전, API 인증 미들웨어 및 리소스 권한 검사 구현
- Alembic 마이그레이션 구성 추가

## Web 화면 및 연동

- 회원가입, 필수동의, 로그인, 보호받을 가족 등록, 확인 가족 등록 화면 구현
- 음성·얼굴 등록, 정상전화, 의심전화 분석, 고위험 차단, 가족 확인 요청 화면 구현
- 통화기록, 관리자 화면 구현
- 모바일·데스크톱 반응형 스타일 적용
- 회원가입 및 로그인 API 연동
- 인증 토큰을 후속 API의 Bearer 토큰으로 사용
- 가족 그룹 → 보호받을 가족 → 확인 가족 순차 등록 API 연동
- 입력 검증, 처리 중 상태 및 API 오류 안내 추가

## Android 화면 및 연동

- Jetpack Compose 기반 신규 화면 흐름 구현
- 기존 화면 코드는 `archive/legacy-ui-20260714`에 별도 보관
- 수신 전화 위험등급에 따라 의심전화 또는 고위험 차단 화면으로 진입
- 회원가입 및 로그인 API 연동
- 보호받을 가족 및 확인 가족 등록 API 연동
- 접근·갱신 토큰과 사용자 식별자를 암호화 저장소에 보관
- CallScreeningService에서 통화 세션 생성 및 대응 결과 보고 연동

## 개발환경 구성

- 로컬 OpenJDK 17 설치: `.local/jdk-17`
- 로컬 Gradle 8.7 설치: `.local/gradle/gradle-8.7`
- Android SDK Platform 35 및 Build Tools 설치: `.local/android-sdk`
- Android Gradle Wrapper 추가
- Java/Kotlin JVM Target 17로 통일
- 로컬 도구와 Android 사용자 상태는 Git 추적에서 제외

## 검증 결과

- Web TypeScript 및 Vite 프로덕션 빌드 성공
- Backend API 테스트: **41 passed**
- AI 서비스 테스트: **6 passed**
- Android Kotlin 컴파일 성공
- Android Debug APK 조립 성공
- 생성 APK: `apps/android/app/build/outputs/apk/debug/app-debug.apk`

## 백업

- 백업 파일: `backups/soricall-source-20260714-<timestamp>.tar.gz`
- `.git`, `.local`, `.android`, `.venv`, `node_modules`, 빌드 산출물은 백업에서 제외

## 후속 개발 권장사항

1. 실제 기기 음성 녹음·업로드·등록 완료 처리
2. 얼굴 촬영 및 선택 동의 기반 등록 처리
3. Web·Android 통화기록 실데이터 조회 연동
4. 관리자 통계 및 운영 알림 실데이터 연동
5. 실제 Android 단말에서 CallScreeningService 및 FCM 통합 시험
