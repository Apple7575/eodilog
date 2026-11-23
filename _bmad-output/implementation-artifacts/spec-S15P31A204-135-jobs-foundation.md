---
title: 'S15P31A204-135 PostgreSQL jobs 공통 기반'
type: 'feature'
created: '2026-11-02'
status: 'in-review'
route: 'dispatch'
baseline_commit: 'ccc7df396dbb6c6d7c1e87dbe34eecc6e1491002'
review_loop_iteration: 0
context:
  - 'EodiLog/AGENTS.md'
  - 'EodiLog/docs/plan/jobs-leave-contract-to-B-2026-11-02.md'
---

<frozen-after-approval reason="사용자가 B의 전 항목 동의와 Jira 생성 후 구현 진행을 명시적으로 승인함">

## Intent

A가 PostgreSQL 기반 jobs 등록·worker·조회 기반을 구현한다. 승인된 jobs/나가기 계약이 기준이며 B 도메인과 나가기 구현은 변경하지 않는다. 실제 운영 handler 없이도 기반은 테스트 가능하지만 운영용 가짜 작업은 생성하지 않는다.

## Boundaries & Constraints

- 새 `job` 도메인 패키지와 Flyway 신규 마이그레이션만 추가한다. 기존 마이그레이션 수정·외부 큐·배포·원격 작업·커밋·푸시 없음. 기존 미추적 계약 MD를 보존하며 B 동의 상태를 반영한다.
- 기존 JobRef/Job DTO, GET `/api/v1/jobs/{jobId}`, DataResponse/ErrorResponse와 Swagger 계약 유지. POST/retry/cancel 공개 API 없음. jobs 경로는 기존 인증 보호 유지.
- 내부 submit은 MANDATORY 쓰기 트랜잭션 참여. requestedBy userId·kind·nullable tripId·허용 입력·nullable baseVersion·고정 cleanup scope를 받는다. 신규 ID UUIDv7. handler와 조회/실행 정책 없으면 등록 거부.
- 공개 조회는 활성 계정·kind 정책 검사 후 안전한 result만 반환. 존재 숨김은 404 JOB_NOT_FOUND. cleanup kind는 최초 요청자만이며 여행 이탈 후에도 조회 가능, result는 scope/completedCount/failedCount로 제한한다. 일반 AI는 등록·실행·완료·조회 시 현재 정책 재검사. domain 정책이 없으면 활성화 금지.
- 입력/결과·예외 메시지·토큰을 로그에 출력하지 않는다. DB 에러·실패 코드의 공개 문구는 서버가 정한 안전한 값만 사용한다.

## I/O & Edge-Case Matrix

| 상황 | 기대 |
| --- | --- |
| 미등록 kind 등록 | DB 작업 없음, 구성 오류로 호출 트랜잭션 실패 |
| 호출 도메인 rollback / 아직 미커밋 | 작업 rollback / 다른 커넥션 worker에 보이지 않음 |
| 같은 QUEUED에 두 worker | SKIP LOCKED 등 원자 선점으로 한 실행만 획득 |
| 실행 성공 | 유효 실행 식별자·임대 확인 후 결과와 도메인 완료 반영을 같은 짧은 트랜잭션으로 커밋 |
| 일시 실패·timeout | 최초 포함 최대 3회, 재시도 QUEUED와 nextAttemptAt 기록 후 최종 FAILED |
| 영구 실패·권한 철회 | 재시도하지 않고 FAILED 또는 정책 철회 CANCELLED; 안전한 오류만 반환 |
| 죽은 worker 임대 만료 | 재선점 가능; 시도 상한 도달 작업은 FAILED, 무한 RUNNING 방지 |
| 옛 실행의 늦은 완료·heartbeat | 실행 ID·임대 불일치로 무시, 새 실행 결과 덮어쓰기 금지 |
| 남의 작업·정책 거부·없는 작업 | 404 JOB_NOT_FOUND, 입력·결과 비노출 |

</frozen-after-approval>

## Code Map

- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/global/id/UuidV7.java`: ID 재사용.
- `global/common/response/DataResponse`, `global/common/error/*`: 응답·업무 오류 재사용.
- `global/config/TimeConfig`: Clock 주입. JDBC+TransactionTemplate 패턴은 auth 참고.
- `docs/erd.dbml` jobs: 논리 스키마, 상태 QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED. 실행 ID·attempt·임대·next-attempt·heartbeat 열과 선점 인덱스를 신규 물리 설계에 추가한다.
- `docs/api-spec.md` §9·§10: JobRef/Job 및 권한·result. B의 leave·expense 행은 수정하지 않는다.
- `TestcontainersConfiguration`, `AuthUserRequestPostProcessors`: 실제 PostgreSQL 통합 검증에 사용. 전체 Gradle build 필요.

## Tasks & Acceptance

- [x] `EodiLog/src/main/resources/db/migration/V202611021200__create_jobs.sql` — 기본·실행 제어 열, 제약·선점 인덱스. 실행 시점 최신 번호 확인.
- [x] `EodiLog/src/main/java/com/ssafy/a204/EodiLog/job/**` — 명세 DTO·JobKind/Status·오류, 등록/조회 facade, 저장소, handler/access policy SPI·레지스트리. 정규 엔터티 대신 무제한 JSON 구조로 확장하지 않는다.
- [x] 같은 패키지 worker — 짧은 DB 선점·완료, 외부 실행은 트랜잭션 밖. 실행 식별자 fencing, heartbeat/임대 만료 복구, 제한된 executor·timeout·retry. 결과 저장과 완료 도메인 반영을 원자적으로 연결할 완료 hook을 제공하며 stale hook 실행 금지.
- [x] `application.yaml` 및 테스트 설정 — 검증되는 설정값: polling 1초, 실행 timeout 60초, 임대 120초, heartbeat 20초, 재시도 최대3회·간격30초, 한 poll당 한 작업. 설정 불일치 시 시작 실패. 테스트에서 worker 자동 스케줄은 끄고 수동 실행·Clock으로 검증한다. 실제 .env 수정 없음.
- [x] `EodiLog/src/test/java/.../job/**` — 위 matrix를 실제 DB·경쟁 요청으로 검증, 외부 네트워크 대신 등록된 테스트 handler·policy 사용. timeout·복구는 긴 sleep 없이 수행. OpenAPI 경로·DTO·인증 검증.
- [x] `EodiLog/docs/plan/jobs-foundation.md` — 최종 SPI·설정·보장과 at-least-once 한계, 등록 예시·외부 멱등키(jobId)·B 연결 순서. 계약 MD에 동의 사실 표시. API/ERD에는 jobs 관련 사항만 반영.

수용 기준:
- Given 같은 도메인 트랜잭션, when 등록 후 rollback, then jobs도 없고 외부 실행 없음.
- Given 동시 worker와 임대 재선점, when 늦은 실행 완료, then 현 실행과 결과·도메인 상태 보존.
- Given 성공/실패/재시작, when 처리, then 제한된 시도 안에서 올바른 terminal 상태 또는 실행 가능한 QUEUED로 복구.
- Given 권한 변경, when 실행/완료/조회, then kind 정책 적용 및 내용 비노출.
- Given 실제 handler 없는 앱, when 시작, then 정상 시작하고 공개 생성 경로·가짜 작업 없음. 기존 전체 테스트 통과.

## Implementation Notes

- 사용자가 계약 전체 승인 후 코드 진행을 명시했다. 새 사용자 결정 없이 합의 계약을 구현 명세로 구체화한다. 기술 기본값은 외부 계약 변경이 아닌 설정값이다.
- Jira135는 jobs 기반이라는 단일 목적이다. 나가기·AI·삭제 handler는 이슈 범위 밖이다.
- 실행기 부수 효과의 정확히 한 번 보장은 하지 않는다. timeout 후 interrupt 무시 실행이 남을 수 있어 bounded executor·임대 fencing·동일 jobId 멱등키·도메인 완료 hook이 필요하다.

## Verification

`EodiLog/gradlew.bat build --console=plain`, PostgreSQL jobs 통합·OpenAPI 테스트, `git diff --check`.
