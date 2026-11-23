---
title: 'S15P31A204-126 토큰 갱신·현재 세션 로그아웃'
type: 'feature'
created: '2026-10-30'
status: 'done'
route: 'dispatch'
baseline_commit: '0f25e7f402d6bb9932a4bf57624230041bc62c79'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

기존 API 계약대로 POST `/api/v1/auth/sessions/refresh`와 DELETE `/api/v1/auth/session`을 제공한다. 성공은 각각 기존 Session 응답과 204다. 액세스 1시간·리프레시 2주 설정과 해시 저장을 재사용한다.

## Boundaries & Constraints

- 갱신은 Bearer 없이 리프레시 토큰으로 인증한다. 만료된 Authorization 헤더도 갱신을 막지 않는다.
- 로그아웃은 유효한 Bearer의 현재 세션만 대상으로 하고 다른 기기는 유지한다. 카카오 연결 해제·계정 탈퇴는 제외한다.
- 회원 상태 검증, 공통 오류·traceId·Swagger 계약을 유지한다. 토큰 원문은 로그·DB에 남기지 않는다.
- 기존 v4 ID 및 S15P31A204-124의 신규 v7 ID와 호환한다. 병합된 migration과 AuthUser의 userId 계약은 변경하지 않는다.
- 사용자 확정: 매 갱신 시점부터 리프레시 만료를 새로 14일 부여한다. 회전 성공 시 이전 access·refresh는 즉시 폐기한다.
- 사용한 refresh 재사용 시 해당 로그인 계열의 모든 후속 세션도 폐기하고 401을 반환한다. 다른 기기 로그인은 유지한다. 앱은 갱신 요청을 직렬화한다.
- 가입 대기 사용자도 갱신·로그아웃을 허용하되 /me 외 서비스 접근은 계속 403으로 제한한다.

## I/O & Edge-Case Matrix

| 상황 | 기대 결과 |
| --- | --- |
| 유효 refresh | 새 토큰·Session, isNewUser=false |
| 없는·만료 refresh, 비활성 회원 | 401 UNAUTHENTICATED |
| 로그아웃 성공 후 인증·갱신 | 폐기된 세션은 401, 다른 기기는 유지 |
| 빈 토큰·알 수 없는 필드 | 400 공통 오류 |
| 동일 refresh 동시 사용 | 중복 후속 세션 없음. 재사용으로 해당 로그인 계열 폐기, 다른 기기는 유지 |
| 가입 대기 사용자 | 갱신·로그아웃 허용, 여행 등 서비스는 계속 403 |

</frozen-after-approval>

## Code Map

경로 기준은 `EodiLog/`다.

- `src/main/java/com/ssafy/a204/EodiLog/domain/auth/AuthService.java`: TransactionTemplate·회원 조회·토큰 발급 재사용.
- 같은 디렉터리 `AuthDtos.java`, `Tokens.java`, `BearerFilter.java`: DTO·JWT 검증·세션 인증.
- `src/main/java/com/ssafy/a204/EodiLog/global/config/SecurityConfig.java`: 공개 refresh 경로와 필터 제외를 함께 변경.
- `src/main/resources/db/migration/V202610301000__create_auth.sql`: 기존 sessions.rotated_from_id와 revoked_at 사용. 파일 수정 없음.
- `src/test/java/com/ssafy/a204/EodiLog/domain/auth/AuthIntegrationTest.java`: 전용 PostgreSQL Testcontainers 재사용.

## Tasks & Acceptance

- [x] 위 auth 디렉터리에 `SessionController.java` 추가: 두 경로와 Swagger 정의.
- [x] `AuthDtos.java`: 유효성 검증된 RefreshRequest 및 Session 설명 갱신.
- [x] `AuthService.java`: 갱신·로그아웃 트랜잭션과 회원/세션 재검사 구현. 같은 회원 행 잠금으로 관련 변경 직렬화 검토. 재사용 폐기는 롤백되지 않게 커밋 후 401 처리.
- [x] `BearerFilter.java`, `SecurityConfig.java`: refresh 공개, 로그아웃에 검증된 세션 ID 전달. AuthUser 변경 금지.
- [x] `AuthIntegrationTest.java`: 정상·실패·회전 다세대·동시 갱신·로그아웃 경합·기기 격리·가입 대기·로그 비노출·OpenAPI 검증.
- [x] `docs/api-spec.md`, `docs/design/backend-auth-integration.md`: 확정 정책·앱의 토큰 교체 흐름 반영.

Given 유효 토큰, when 갱신, then 새 토큰의 해시·연결된 세션과 응답이 일치한다.
Given 서로 다른 로그인, when 한 세션 로그아웃, then 해당 세션만 인증·갱신 불가다.
Given 동시 갱신·폐기, when 경합, then 폐기된 로그인 계열이 다시 살아나지 않는다.

## Implementation Notes

- Jira S15P31A204-126 생성. 기존 UUIDv7 구현과 초대 정책 문서는 보존한다. 미결 정책 응답 후 구현 명세를 확정한다.
- 신규 스키마 없이 구현 가능하며 실제 사용자 DB·환경 키는 수정하지 않는다.
- 사용자가 세 정책을 모두 승인하여 미결 항목이 해소됐다. 브랜치는 feature/S15P31A204-126-session-lifecycle. 기존 미커밋 UUIDv7 구현과 여행 정원·링크 정책·B 전달 문서는 보존하고 해당 변경을 삭제하거나 되돌리지 않는다.
- 커밋·푸시는 요청 범위에 없어 수행하지 않는다. 외부 API 호출이나 원격 Git 작업 없이 로컬 구현·테스트만 수행한다.
- 전체 검증은 JAVA_HOME=C:/Users/SSAFY/.jdks/temurin-25.0.3 을 사용한다. Docker·Gradle·JDK 접근이 기본 샌드박스에서 제한되면 승인된 exec require_escalated를 이용한다. .env 값을 출력하지 않는다.
- 구현 전체 build 158개 테스트 통과(실패·오류·skip 0). 매트릭스 여섯 행은 AuthIntegrationTest의 정상 회전, 오류 검증, 로그아웃 기기 격리, 동일 토큰 동시 갱신, 가입 대기 테스트로 실제 실행을 확인했다.
- 사용자 지시로 최신 dev `eac4ff074b2136c98858c3302d86fd0930d497ab`를 fast-forward 반영했다. 원래 baseline_commit은 보존한다. 진행 작업은 `backup-session-126-before-dev-pull-20261030` stash로 백업하고 복원했다. SecurityConfig·API 명세 충돌 두 곳은 초대와 인증 변경을 모두 보존하여 해소했다. 루트·백엔드 .env 해시가 유지됨을 확인했다.
- 리뷰 patch 다섯 건 반영 후 AuthIntegrationTest 32개 통과. 부모가 최신 dev 통합 상태에서 전체 build를 재실행해 173개 테스트(인증 통합 32·초대 API 9 포함), 실패·오류·skip 0을 확인했다. 충돌 파일 0, git diff --check 통과. 세션 이력 정리만 기존 미결 과제로 deferred-work.md에 기록했다. 커밋·푸시·MR은 수행하지 않았다.

## Review Triage Log

- blind-1 / low, 기각: rotated_from_id 단독 인덱스는 없지만 후손 탐색은 user_id 필터와 기존 sessions_user_idx를 사용한다. 큰 계열에서의 성능 가능성은 있으나 일반 규모에서 확인된 장애가 없고 신규 migration을 추가할 정도의 실측 근거는 없다.
- blind-2 / low, defer: 만료 세션 이력 정리 정책 부재는 기존 로그인도 계속 세션을 추가하던 선행 문제다. 회전 계열 정리 시 재사용 감지 의미가 유지돼야 하므로 후속 이력 보존·정리 작업으로 기록한다.
- blind-3 / low, 기각: 회원 행 잠금은 서로 다른 계열의 경합까지 안전하게 직렬화하려는 의도된 설계다. 다른 기기 세션을 폐기하지 않는 동작은 테스트로 검증됐으며 짧은 DB 트랜잭션에 별도 계열 잠금 체계를 추가할 필요는 확인되지 않았다.
- blind-4 / low, 기각: 공용 Clock 주입 제안은 테스트 개선이며 현재 정상 시계의 만료 검사는 올바르다. 기존 토큰 발급도 Instant.now를 사용한다. 신규 auth 전체의 시간 의존성 변경은 단순 수정 범위를 넘으며 경계 값은 기존 Instant 비교로 확인된다.
- blind-5 / low, patch: 후속 INSERT 실패 시 이전 세션 폐기의 롤백 검증을 추가한다. 구현은 이미 같은 TransactionTemplate 트랜잭션이다.
- blind-6 / low, patch: 만료된 조상 refresh 재사용으로 살아 있는 후속 세션까지 폐기됨을 검증한다.
- blind-7 / low, patch: 토큰 로그 비노출 검사에 정상 로그아웃 성공 경로를 추가한다.
- blind-8 / low, patch: 공용 Swagger 설정이 400·보호 API 401을 자동 추가하므로 코드 누락 주장은 일부 false다. 다만 refresh의 명시적 401에는 공통 스키마가 자동 추가되지 않으므로 해당 스키마와 OpenAPI 검증을 보완한다.
- blind-9 / low, patch: 앱의 오프라인·시간 초과 로그아웃 시 로컬 자격 증명을 지우고 서버 폐기 미확인 상태를 구분하도록 연동 문서를 보완한다.
- edge / 발견 사항 없음.
- verification / 검증 누락 발견 사항 없음.

## Verification

- `EodiLog/gradlew.bat build`: PostgreSQL 통합 테스트 포함 전체 성공.
- `git diff --check`: 형식 오류 없음.

- 후속 게시 요청(10/30)에 따라 UUIDv7 MR !59의 4ebf7e516852fd8a8b2d0f84978dc1e352d01128 뒤에 인증 생명주기 변경을 분리해 커밋한다. 정책 문서 변경은 S15P31A204-127로 분리한다. 코드·테스트는 173개 전체 build 통과 상태와 동일하다.
