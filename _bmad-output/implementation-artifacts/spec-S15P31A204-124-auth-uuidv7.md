---
title: 'S15P31A204-124 인증 신규 ID UUIDv7 전환'
type: 'refactor'
created: '2026-10-30'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**문제:** A 인증의 영속 ID 네 곳은 UUIDv4이고 B 및 A·B 계약은 신규 ID를 UUIDv7로 합의했다.

**접근:** 기존 Hibernate UUIDv7 전략을 재사용해 신규 회원·소셜 계정·로그인 시도·세션 ID를 생성한다. 기존 v4 회원·계정·세션은 변경하지 않고 계속 인증할 수 있어야 한다. DB 스키마와 데이터, PKCE·리프레시 보안 난수, 추적 ID는 유지한다. 토큰 갱신·로그아웃과 운영 설정은 다음 이슈다.

</frozen-after-approval>

## Implementation Notes

- 시작 기준: `0f25e7f402d6bb9932a4bf57624230041bc62c79`, 브랜치 `feature/S15P31A204-124-auth-uuidv7`, Jira S15P31A204-124.
- 사용자 승인에 따라 기존 B 전달 MD는 미커밋 상태로 보존하며 이번 구현 범위에서 제외한다.
- 의도상 미정 사항 없음. 마이그레이션·데이터 변경 없음. 작은 유틸·서비스 호출 네 곳·테스트·관련 계약 설명만 수정하는 oneshot 경로다.
- 설치된 Hibernate 7.4.13.Final의 `UuidVersion7Strategy.generateUuid`는 세션을 사용하지 않고 AtomicReference로 상태를 관리한다. B의 VERSION_7과 같은 전략을 래핑하며 새로운 UUID 알고리즘·의존성을 도입하지 않는다.
- `AuthService`의 네 생성 지점을 `global.id.UuidV7`로 전환한다. DB 통합 테스트로 네 테이블의 v7·variant·JWT 연결과 기존 v4 회원/계정/세션 호환성을 확인한다. 유틸 테스트는 타임스탬프와 동시 생성 유일성을 검증한다.
- 명세 전체 문자열 제한 정리나 B의 !50 리뷰는 별도다. UUID 관련 계약만 현재 구현과 맞춘다.
- 전체 `gradlew.bat build` 성공: 147개 테스트, 실패·오류 0. 이후 리뷰로 v4 로그인 시도 교환과 기존 세션 필드 보존 검증을 추가했다.
- 커밋·푸시는 이번 요청에서 명시적으로 요구하지 않았으므로 저장소 AGENTS.md의 명시적 요청 규칙에 따라 수행하지 않는다.
- 리뷰 보강 후 `gradlew.bat test --tests '*AuthIntegrationTest' --tests '*UuidV7Test'` 성공. 실제 PostgreSQL에서 신규 v7 및 기존 v4 로그인 시도·회원·계정·세션 호환성 검증을 통과했다. `git diff --check`도 통과했다.

## Review Triage Log

- low / 보류하지 않고 기각: 타임스탬프 검사 중 큰 역방향 시스템 시계 조정은 일반 실행에서 드물며, 이 변경은 Hibernate의 시계 보정 정책을 구현하지 않는다. 별도 제어 시계 주입은 작은 래퍼 검증보다 범위가 커진다. 정상 시계에서 실제 생성 시각은 현재 테스트로 확인한다.
- low / 기각: 같은 밀리초 내 단조 정렬 추가 검증 제안은 재사용 라이브러리 알고리즘의 보장 범위다. 이번 전환의 사용자 계약은 v7·variant·유일성·기존 ID 호환이며 자체 정렬 알고리즘을 도입하지 않았다.
- low / 수정: 배포 전 v4 로그인 시도가 누락된 검증을 보완했다. 유효한 미소비 시도의 ID를 v4로 만든 뒤 교환과 인증 성공을 확인한다.
- low / 수정: 기존 v4 세션의 user_id·refresh_token_hash·expires_at·revoked_at 보존을 로그인 이후 직접 조회해 검증한다.

- 후속 게시 요청(10/30)에 따라 최신 dev eac4ff074b2136c98858c3302d86fd0930d497ab에서 UUIDv7만 분리했다. 분리 상태 전체 build 162개 테스트 통과(실패·오류 0). 사용자 승인으로 커밋·푸시·MR을 진행한다.
