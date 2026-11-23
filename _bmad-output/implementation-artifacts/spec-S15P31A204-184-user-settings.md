---
title: '사용자 AI·알림 설정 조회 및 변경'
type: 'feature'
created: '2026-11-04'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'c821d00c20a000a094017fee7534945894f25498'
context:
  - 'EodiLog/AGENTS.md'
  - 'docs/api-spec.md'
---

<frozen-after-approval reason="사용자가 A·B 분담과 B 회신대로 개발 승인">

## Intent

**Problem:** AI 기능과 알림 종류별 사용자 설정이 명세에 있지만 저장소와 API가 없어 앱에서 선택을 유지할 수 없다.

**Approach:** `GET/PATCH /api/v1/me/settings`와 사용자별 기본 설정 행을 만든다. PATCH는 요청한 부분만 변경하고 `expectedVersion`으로 원자적 충돌 검사를 한다.

## Boundaries & Constraints

**Always:** API 명세의 `UserSettings`·`SettingsPatch` 모양, AI 네 기능 AUTO/CONFIRM/OFF, 날씨 SUGGEST_ONLY/OFF, 알림 세 불리언과 초기값 CONFIRM/SUGGEST_ONLY/true를 따른다. version은 1에서 시작하고 실제 변경 시 증가한다. 잘못된 입력은 400, 오래된 version은 409 `VERSION_CONFLICT`. 가입 완료한 본인만 접근한다.

**Never:** 설정 API 작업을 AI 작업 실행 정책이나 알림 전달까지 완료한 것으로 표현하지 않는다. 기존 Flyway 파일이나 B 소유 도메인 코드는 바꾸지 않는다.

## I/O & Edge-Case Matrix

| 상황 | 입력·상태 | 결과 | 오류 |
| --- | --- | --- | --- |
| 첫 조회 | 설정 행 없는 활성 회원 | 기본값·version 1 | 없음 |
| 부분 변경 | 현재 version과 AI/알림 일부 필드 | 나머지 유지·version 증가 | 없음 |
| 충돌 | 오래된 expectedVersion | 값·version 모두 유지 | 409 VERSION_CONFLICT |
| 잘못된 값 | 알 수 없는 모드·누락 version·알 수 없는 필드 | DB 불변 | 400 VALIDATION_ERROR |
| 인증 실패 | 비로그인·가입 대기 | 설정 비노출 | 401·403 기존 규칙 |

</frozen-after-approval>

## Code Map

- `docs/api-spec.md` §3 및 `UserSettings`·`SettingsPatch`: 공개 응답·요청 계약.
- `docs/erd.dbml` `user_settings`: DB 열과 기본값 제안.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/user/MemberController.java`, `MemberStore.java`: 현재 `/me` 인증·프로필 관례. 설정은 별도 controller/service.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/domain/auth/BearerFilter.java`: 가입 대기 차단을 그대로 사용.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/trip/exception/TripErrorCode.java`: VERSION_CONFLICT 패턴만 참고.

## Tasks & Acceptance

**Execution:**
- [x] `EodiLog/src/main/resources/db/migration/` -- 새 버전 `user_settings` 테이블 추가. 기존 마이그레이션 수정 금지.
- [x] `EodiLog/src/main/java/com/ssafy/a204/EodiLog/user/` -- 설정 DTO·서비스·컨트롤러·오류 코드 추가, 첫 조회 초기화와 조건부 PATCH 구현.
- [x] `EodiLog/src/test/java/com/ssafy/a204/EodiLog/user/` -- 위 행렬을 DB 연동 API 테스트로 검증.
- [x] `docs/api-spec.md` -- 실제 초기화·version·부분 변경 동작만 보충.

**Acceptance Criteria:**
- Given 활성 사용자가 첫 조회를 하면, when GET을 호출하면, then 기본값과 version 1이 반환된다.
- Given 설정을 변경한 사용자가 재조회하면, when GET을 호출하면, then 저장한 값과 증가한 version이 반환된다.

## Implementation Notes

- 2026-11-04: 첫 조회에서 활성·가입 완료 회원의 기본 행을 안전하게 생성한다. 부분 PATCH는 사용자 설정 행 잠금 뒤 version을 검사한다. 같은 값으로 PATCH하면 version을 유지한다.
- `UserSettingsApiTest` 집중 테스트와 전체 `gradlew.bat build`가 통과했다. 검토는 입력 검증·첫 조회 경쟁·PATCH 롤백 경로를 코드와 테스트로 확인했다.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd EodiLog; .\gradlew.bat build` -- 전체 빌드와 Testcontainers 테스트 통과.
