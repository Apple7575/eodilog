---
title: '여행 사진 수동 관리'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
baseline_commit: '895723489e16ed4d52896d3be5b6ea38cea06b13'
review_loop_iteration: 0
context:
  - '{project-root}/EodiLog/AGENTS.md'
  - '{project-root}/EodiLog/docs/plan/backend-a-b-work-split-2026-11-09.md'
---

<frozen-after-approval reason="사용자가 분담안의 A 전체 진행을 승인">

## Intent

**문제:** 여행 사진은 등록·목록만 가능해서 잘못된 장소/주제를 고치거나 사진을 지울 수 없다.
**접근:** 사진 수동 편집·개별 비동기 삭제·분류별 요약을 제공해 업로드 후 관리 흐름을 완성한다. 사용자의 ‘A진행해’는 전달한 A 분담 전체에 대한 구현 승인이다.

## Boundaries & Constraints

**항상:** 현재 ACTIVE 여행 멤버인 업로더만 편집·삭제한다. 타인 사진은 404 PHOTO_NOT_FOUND. 수정은 expectedVersion을 검사해 409 VERSION_CONFLICT, 성공 시 version 증가. 장소 null은 해제, 생략은 유지. topics는 기존 명세 LANDSCAPE/FOOD/PEOPLE/OTHER 중 중복 없는 0~4개, 빈 배열은 해제, null/미지원 값은 400. 수동 장소·주제 변경/해제 이력을 보존해 후속 AI의 덮어쓰기를 방지한다. 삭제는 승인 트랜잭션에서 사진·파일 접근을 차단하고 고정 대상 PHOTO_DELETE 작업을 등록한다. 작업은 이탈·여행 삭제 후에도 승인 범위를 정리한다.

**제외:** 그룹 관리·사진 이동·일괄 변경·AI 분류·피드·실제 운영 데이터 삭제. groupId 변경은 이번 API에서 명시적으로 거부한다. 기존 등록/목록/다운로드·배치 한도·여행 삭제 계약을 보존한다. 기존 Flyway는 수정하지 않는다. .env와 무관한 기존 미추적 파일은 건드리지 않는다. 커밋·푸시·원격 작업은 이번 구현에 포함하지 않는다.

## I/O & Edge-Case Matrix

| 상황 | 입력/상태 | 기대 결과 | 오류 |
| --- | --- | --- | --- |
| 수동 수정 | 본인 ACTIVE, 현재 version, placeId/topics | 200 Photo, 생략 유지·null 장소 해제·빈 주제 해제, version 증가 | 잘못된 장소/주제/빈 수정/누락 version은 400 |
| 권한/경합 | 타인·이탈·여행 삭제 또는 오래된 version | 변경 없음 | 타인/없는 사진 404, 여행 접근 실패 404, version 409 |
| 개별 삭제 | 본인 등록 사진 | 202 JobRef, 커밋 후 목록·요약·새 다운로드에서 제외 | 중복 요청은 같은 작업 반환, 사진 미존재는 404 |
| 파일 정리 실패 | S3 원본/표시 삭제 일부 실패 | 기존 worker 재시도, 숨김 유지·범위 확대 없음 | 실패를 완료로 처리하지 않음 |
| 전체 삭제와 경합 | PHOTO_DELETE와 TRIP_DELETE 중복 실행 | FK 오류 없이 정리, 중복 삭제 안전 | 멤버 이탈로 기존 정리 취소 금지 |
| 요약/필터 | 사진별 장소·주제, 삭제 사진 | 필터와 독립된 PhotoSummary, topic 목록 필터 실제 적용 | 잘못된 topic 400 |

</frozen-after-approval>

## Code Map

- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/photo/PhotoService.java`: JdbcTemplate, TripAccessChecker 여행 잠금 → assets 잠금 순서. 현재 map은 topics 빈 배열, 목록 필터는 빈 결과. register는 asset 고유/배치 한도를 보존한다.
- 같은 패키지 `PhotoController.java`, `PhotoErrorCode.java`, `dto/`: 기존 등록·목록 응답을 확장. API 경로는 docs/api-spec.md §7, PhotoSummary 필드 totalCount/unplacedCount/topics/places/groups. groups는 빈 배열.
- `EodiLog/src/main/resources/db/migration/V202611061400__extend_assets_and_create_photos.sql`: photos 및 배치 생성. 새 V20261109 마이그레이션으로 photo_topics, 수동 보정 표시, 삭제 작업 참조 등을 추가한다.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/job/`: JobService.submit은 기존 쓰기 트랜잭션 필수. JobSubmission·CleanupScope는 불변 대상. JobKind.PHOTO_DELETE 이미 존재. 정책/핸들러를 등록해야 활성화된다. JobService는 정리 결과 scope/count만 공개한다.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/trip/service/TripDeleteJobHandler.java`, `TripDeleteJobAccessPolicy.java`: 기존 삭제 처리 패턴. 새 photo_topics FK 정리 추가. execute 외부 삭제 후 complete DB 정리.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/asset/service/AssetService.java`, `asset/AssetCleanup.java`: 다운로드 READY/등록 검사. 삭제 승인과 즉시 접근 차단을 연동한다. AssetCleanup은 photos 참조가 남으면 assets를 물리 삭제하지 않는다. 원본 PUT 만료 후 유예기간 반복 정리 정책을 유지한다.
- `docs/erd.dbml`: photo_topics(photo_id,topic,source) 구조, 사진 version과 deleted_at. AI 주제 4종은 `ai/docs/spec.md` §8.1.
- `EodiLog/src/test/`: 기존 Photo/Asset/TripDelete API 및 jobs 테스트를 재사용한다. 테스트 DB는 Testcontainers PostGIS.

## Tasks & Acceptance

**실행:**
- [x] `photo/`, `src/main/resources/db/migration/` — 수정 DTO·주제 저장·수동 보정 이력·version 검사와 사진 요약/필터 구현.
- [x] `photo/`, `job/` 기존 인터페이스 — PHOTO_DELETE 핸들러/정책·삭제 요청·대상 고정·재시도/재요청 구현.
- [x] `asset/`, `trip/service/TripDeleteJobHandler.java` — 삭제 즉시 파일 접근 차단과 정리 순서/경합 보존.
- [x] `EodiLog/src/test/` — 위 매트릭스 전체와 기존 업로드 회귀 검증.
- [x] `docs/api-spec.md`, `docs/erd.dbml`, 컨트롤러/DTO Swagger — 실제 계약·정리 한계 기록.

**인수 기준:**
- Given 기존 업로드 사진, when 사용자가 보정·필터·요약 조회, then 변경된 동일 사진과 정확한 전체 집계를 확인한다.
- Given 삭제 요청이 커밋됨, when 다른 멤버가 목록/파일 접근, then 삭제 사진을 제공하지 않는다. 이미 열린 다운로드 스트림은 회수하지 않음을 명시한다.
- Given 삭제 작업이 실패 후 재실행됨, when 사용자 이탈 또는 여행 삭제가 겹침, then 최초 승인 파일만 정리하고 타인 자료/새 사진은 보존한다.
- Given 기존 업로드와 여행 삭제 기능, when 전체 build, then 기존 테스트를 포함해 통과한다.

## Implementation Notes

- 기존 미추적 문서와 .omc는 이번 작업과 독립된 기존 상태로 보존한다. 로컬 dev에서 파일 변경만 진행한다.
- 조사 추가: JobHandler.execute 예외 throw는 영구 EXECUTION_FAILED이다. 일시 저장소 장애는 `JobOutcome.failed(TEMPORARY_FAILURE)`로 반환해야 자동 재시도된다. PHOTO_DELETE는 CleanupScope.photoIds 한 개·messageIds 빈 목록으로 고정하고 승인 후 canExecute/canComplete를 멤버십에 종속시키지 않는다.

## Spec Change Log

## Review Triage Log

### 2026-11-09 독립 검토 1회

| ID | 판정 | 근거·처리 |
| --- | --- | --- |
| blind-1 | high | JobProperties 최대 3회 후 FAILED, 재요청 receipt 반환, AssetCleanup의 모든 photos 참조 차단을 확인. 장애가 길면 파일이 영구 잔류하므로 기존 DELETING 정리 루프가 논리 삭제 사진 참조에도 객체 삭제를 재시도하도록 최소 수정. 참조 asset 행은 보존한다. |
| blind-2 | medium | Long 바인딩은 Jackson 정수 변환을 허용. expectedVersion의 소수/문자열 토큰을 엄격히 거부하고 회귀 검증한다. |
| blind-3 | low | 순차 중복 요청은 검증돼 있으나 동시 DELETE는 누락. 현재 trip 잠금이 단일 작업을 보장하는 의미 있는 경합 테스트를 추가한다. |
| blind-4 | medium | 다운로드 잠금 변경을 제거해도 순차 테스트는 통과. storage.open 시점을 제어해 승인 경계 직렬화를 검증한다. |
| blind-5 | low | 여행 삭제 후 사진 삭제 순차 테스트만 있어 동시 자식 정리 FK 경합 검증을 추가한다. |
| blind-6 | low | 삭제 승인 rollback 주입 테스트 누락은 사실이나 전체 작업은 동일 Spring 쓰기 트랜잭션 안이다. 입증된 원자성 위반이 없고 신규 실패 주입 구성이 필요하므로 이번 보강에서 제외한다. |
| blind-7 | low | 동시 집계 테스트는 없지만 summary의 REPEATABLE_READ로 모든 집계 쿼리가 동일 DB 스냅샷을 사용한다. 입증된 불일치가 없고 쿼리 중간 주입 구성이 필요하므로 제외한다. |
| blind-8 | low | 새 EXISTS 필터는 단건만 검증됐다. 같은 시각·복수 주제의 페이지 연결을 직접 검증한다. |
| blind-9 | low | Swagger 설명에는 제약이 있으나 생성 클라이언트용 schema 제약과 400 응답이 빠졌다. 직접 annotation 보정한다. |
| verification-1 | medium | topics=[] 뒤 placeId만 검사한 뒤 다시 주제를 채워 잘못된 clear 구현을 놓친다. 빈 topics 응답과 기존 필터 제외를 즉시 검사한다. |
| verification-2 | medium | 다운로드 승인 직렬화 검증 누락. blind-4와 동일 원인으로 통합 보강한다. |
| edge-1 | medium | 소수/문자열 version 강제 변환은 blind-2와 동일 원인으로 엄격 역직렬화한다. |

## Verification

- `cd EodiLog; .\gradlew.bat build` — 전체 컴파일/테스트 통과. JAVA_HOME은 설치된 JDK 25 사용.
- 실제 S3 삭제는 호출하지 않는다. InMemoryStorage/테스트 대역으로 실패·재시도·접근 차단을 검증한다.

### 2026-11-09 구현 검증

- JDK `C:/Users/SSAFY/.jdks/temurin-25.0.3`, `IMAGE_MAGICK=C:/Users/SSAFY/AppData/Local/Temp/eodilog-photo-tools-214/magick.exe`로 `cd EodiLog; .\gradlew.bat build` 성공(3분 11초).
- JUnit XML 합계: 61개 suite, 418개 test, 실패 0, 오류 0, skip 3. PhotoUploadApiTest 28개, JobIntegrationTest 23개 모두 통과. HEIC 변환 테스트 포함, 실제 S3 opt-in 테스트는 실행하지 않음.
- 추가 통합 검증: PATCH null/생략·수동 해제 표시·허용 주제·권한/버전·동시 수정 단일 승자, 실제 topic 필터와 장소별 집계, 삭제 즉시 숨김/다운로드 차단, 고정 파일 재시도, worker QUEUED 재시도→SUCCEEDED 및 최소 공개 결과, 완료 후 동일 작업 재요청, 이탈·여행 삭제 경합과 FK 순서, 늦은 PUT 유예 정리.
- Swagger UI 대신 `/v3/api-docs` 통합 테스트에서 신규 경로·DTO 설명·409/202 응답·Bearer 표시를 확인. `git diff --check` 통과.
- 첫 전체 실행에서 기존 JobIntegrationTest의 가짜 PHOTO_DELETE 빈과 실제 신규 빈이 충돌한 것을 발견. 테스트 전용 BeanDefinitionRegistryPostProcessor로 해당 컨텍스트의 실제 사진 빈 두 개만 제외해 일반 worker fixture와 실제 사진 통합 테스트를 분리한 뒤 전체 build 재통과.
- 전체 build 이후 JobIntegrationTest setup의 FK 정리 순서 한 줄(`photo_delete_requests` → `jobs`)을 보강. 해당 최종 테스트 설정은 별도 `test --tests '*JobIntegrationTest'` 실행도 성공(39초, 23개 통과)했으며, 생산 코드는 전체 build 통과본과 동일.

### 검토 보완 후 최종 검증

- root에서 최종 uild 성공(2분 15초). 총 423개 중 420개 성공, 실패 0·오류 0·외부 연동 opt-in skip 3. 사진 API 33개 모두 성공.
- 독립 3개 검토 결과의 삭제 재시도 소진 복구·엄격 정수 version·주제 해제 검증·동시 삭제/다운로드/여행 정리·필터 커서·Swagger 제약을 보완했다. 별도 미해결 결함 이관은 없다.
- 정리 작업 FAILED 후에도 기존 cleaner가 PUT 만료 뒤 승인된 파일을 재정리한다. 살아 있는 사진 참조는 차단하고 soft-delete 참조/FK는 유지한다. 완료/실패 job 상태를 임의 변경하지 않는다.
- 실제 S3 삭제는 테스트 대역으로 검증했다. .env 변경과 커밋·푸시는 없으며 기존 미추적 자료는 보존했다.

### 실제 S3 삭제 검증 — 2026-11-09

- 후속 요청으로 `AssetRealS3Test`에 실제 사진 삭제 API 왕복 테스트를 추가했다. `test --tests '*AssetRealS3Test' -PrealS3=true` 실행 결과 3개 성공, 실패·오류·skip 0.
- 실제 S3ObjectStorage 사용을 확인하고 새 테스트 사용자/여행/배치/사진만 생성했다. presigned PUT → complete → 사진 등록 → 다운로드 200 → 사진 DELETE 202 → 다운로드 404 → 실제 jobs worker SUCCEEDED를 검증했다.
- finally 안전 정리 **이전**에 S3 HEAD로 원본·표시 객체 모두 없음을 확인했다. 작업 결과 PHOTO_DELETE/completedCount=1 및 중복 DELETE의 동일 jobId도 검증했다. 기존 버킷 파일은 삭제하지 않았다.
- `.env` 수정 없이 기존 연결 설정을 사용했다. 자격 증명과 서명 URL은 출력하지 않았다. 이 기록은 위의 실제 S3 삭제 미실행 상태를 대체한다.

### 작업 공유 — 2026-11-09

- Jira: S15P31A204-226, `[BE] 여행 사진 수동 편집 삭제 및 분류 요약`.
- 사용자 요청으로 `feature/S15P31A204-226-photo-management` 브랜치에서 커밋·푸시한다. 브랜치 기준 origin/dev는 `56aeff6068e9a416d971af199864279b4c1fcaef`이며 원래 검증 기준 이후 추가 변경은 frontend 파일뿐이다. 위 baseline_commit은 원래 구현 검증 기준으로 보존한다.
