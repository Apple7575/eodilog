---
title: '사진 AI 분류와 유사 사진 그룹 적용'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
baseline_commit: '870db3f9f9aa2112625daaa25fd51c062596dadc'
review_loop_iteration: 0
context:
  - '{project-root}/EodiLog/AGENTS.md'
  - '{project-root}/EodiLog/docs/plan/backend-a-b-ai-work-split-2026-11-09.md'
---

<frozen-after-approval reason="사용자가 A 분담 전체를 'A가자!!!'로 승인">

## Intent

사진을 AI로 주제 분류하고 유사 사진으로 묶어, 결과를 확인한 사용자가 명시적으로 적용한다. 기존 수동 보정을 보호하고 사진 목록·요약에 반영한다.

## Boundaries & Constraints

- 기존 명세 경로·jobs·settings·assets를 재사용한다. 현재 ACTIVE 여행 멤버만 요청/조회/apply. 설정 OFF는 차단하고 AUTO도 명시적 apply만 허용한다.
- 요청은 photoIds 1~50개, UUID·중복·같은 여행·삭제 여부 검사. Idempotency-Key로 같은 요청의 중복 작업을 막는다. 사진 ID·asset·version·표시 파일 키를 입력 스냅샷에 고정한다.
- 원본은 정리되므로 메타데이터 없는 display 파일을 사용한다. 50장 전체를 메모리 byte[]로 모으지 않는다. 파일당 최대 15MiB를 검증하고 임시파일/스트리밍 등 bounded 자원으로 multipart 전송, 종료·실패 시 정리한다.
- AI 응답의 사진 ID 집합·중복·상태·주제·UUID 그룹을 검증하고 허용 필드만 결과에 저장한다. 일부 실패는 사진별 FAILED, 모델 5xx/연결 오류는 재시도한다.
- apply는 성공한 사진 중 요청에 지정한 ID만 대상으로 사진별 snapshot/expected/current version을 검사한다. topics_manually_edited=true면 해제 이력도 보호하여 409. 장소·수동 source를 덮어쓰지 않는다. 어떤 대상이라도 충돌하면 전체 rollback.
- 작업당 apply 한 번. 같은 apply 본문 재요청은 처음 결과를 그대로 반환하고, 다른 본문 재사용은 409. 재요청도 현재 권한/설정과 사진의 생존·version을 재검사해 삭제/후속 수정 결과를 되살리지 않는다.
- AI groupId(UUID)는 내부 명세처럼 행 ID로 사용할 수 있으나 다른 작업/여행과 충돌하면 거부한다. 이번에 선택한 성공 사진 2장 이상인 묶음만 새 그룹으로 적용한다. 이후 사진 삭제로 한 장이 남은 그룹은 유지하고 빈 그룹은 요약에서 제외한다. 임의의 다른 사진을 수정하지 않는다.
- 사진 이동·방문 감지·B 추출/코스 구현·자동 원본 삭제·대표 선정은 제외한다. .env·기존 미추적 자료를 보존하고 커밋·푸시는 별도 요청 전 수행하지 않는다.

## I/O & Edge-Case Matrix

| 상황 | 기대 결과 |
| --- | --- |
| 정상 분석→apply | 202 JobRef→사진별 결과→200 photos, source=AI·version 증가·그룹 필터/요약 반영 |
| 빈/중복/다른 여행/삭제 사진·51장 | 검증 오류/404, 초과 422 INPUT_LIMIT_EXCEEDED, 작업 생성 없음 |
| 설정 OFF·이탈·삭제 여행 | 요청/apply 거부, 실행/완료 정책 철회 시 CANCELLED, 조회 권한 없음 |
| 수정·수동 해제·삭제 후 apply | 409 또는404, 사진/그룹 전체 변경 없음 |
| 일부 파일 실패·과대 표시 파일 | 해당 사진 FAILED, 정상 사진은 성공 가능, 원본 유지 |
| 잘못된 AI 결과·모델 장애 | 결과 검증 실패는 EXECUTION_FAILED, 일시 장애는 TEMPORARY_FAILURE |
| 중복/동시 요청·apply | 작업/그룹 중복 없음, 동일 재요청 version 증가 없음 |
| 사진·여행 삭제 경합 | 새 FK 오류 없음, 삭제 파일 접근 및 작업 결과에서 삭제 사진 노출 없음 |

</frozen-after-approval>

## Code Map

- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/photo/PhotoService.java`, `PhotoController.java`, `dto/`: PHOTO_SELECT는 topic projection 포함. group은 현재 null/빈 결과 고정. trip 먼저 잠그는 쓰기 순서 유지.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/checklist/suggestion/`: Service/Access/JobHandler/AccessPolicy의 요청 snapshot·기본 CONFIRM·jobs 연결 패턴 재사용. `user_settings.photo_classification_mode` 사용.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/job/`: PHOTO_CLASSIFICATION enum만 존재. jobs.applied_at/applied_by_member_id 있음. JobService.submit은 쓰기 트랜잭션 필수. 실행 예외 throw는 영구 실패이므로 재시도 오류는 JobOutcome.failed로 반환.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/global/ai/`: AiServerClient는 JSON post만 제공. 기존 구현/대역을 깨지 않도록 multipart 메서드를 추가한다. B 원격216은 frontend뿐이며 재사용할 multipart 코드는 아직 없음. 토큰/traceId 전달, 실패 로그에 외부 본문·사진·서명 URL을 남기지 않는다.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/global/storage/ObjectStorage.java`: display_key/type을 read/open/head로 접근. 원본 byteSize를 표시 파일 크기로 쓰지 않는다.
- `EodiLog/src/main/resources/db/migration/`: 새 migration으로 photo_groups·photos.group_id 및 apply 재요청 기록 추가. 기존 V202611091000 사진 관리 스키마 유지.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/trip/service/TripDeleteJobHandler.java`, `photo/PhotoDeleteJobHandler.java`: 사진/그룹/작업 FK 삭제 순서 통합.
- `ai/docs/spec.md` §0.2·8.1, `ai/app/features/photo_classification/`: multipart meta JSON(photoIds)와 반복 files 순서 일치. 주제 4종 중 하나, AI 그룹 최소2장. 모델 SigLIP2/webli, threshold0.94. AI45s < HTTP50s < worker60s.

## Tasks & Acceptance

- [x] `photo/classification/`, `photo/dto/` — 요청·결과 검증·정책·핸들러·원자 apply와 재요청 구현.
- [x] `global/ai/` — 호환 가능한 bounded multipart 호출과 실제 HTTP 계약 테스트.
- [x] `db/migration/`, `photo/PhotoService.java`, 삭제 핸들러 — 그룹 저장·필터·요약·FK 정리.
- [x] `src/test/` — 매트릭스 API/worker/경합 검증, 실제 AI opt-in 통합 테스트.
- [x] `docs/api-spec.md`, `docs/erd.dbml`, Swagger 및 AI 분담 문서 — 실제 계약·완료 기록 갱신.

Given 정상 사진과 현재 권한, when 분석 후 적용, then 주제·그룹이 저장되고 재요청은 동일 결과다.
Given 작업 이후 사진/권한/설정 변경, when 조회·적용·삭제 경합, then 오래된 정보나 삭제 파일을 노출/복구하지 않는다.
Given 기존 사진 관리 기능, when 전체 build, then 업로드·삭제·jobs 테스트를 포함해 통과한다.

## Implementation Notes

- Jira S15P31A204-229. 새 브랜치 feature/S15P31A204-229-photo-classification. 이전 MR161은 dev 병합 확인.
- 전체 A 범위 진행은 사용자 승인 상태다. 실제 모델 검증용 로컬 Python vision 환경은 root가 별도로 준비하며 생산 AI 코드는 변경하지 않는다.
- 후속 B 전달 문서 확인: MR163의 `355fb40e18b4cabdabc255a11e4072ecb44071a3`에는 실제 백엔드 multipart가 있다. 초기 조사한 frontend216과 별개다. B FilePart/Map 호출 계약을 A 디스크 기반 overload와 함께 보존하고 같은 전송 함수를 사용한다. jobs discard는 A와 직접 충돌하지 않는다. 권한 전용 HEIC 테스트는 JPEG로 교체해 외부 도구 없이도 항상 검증한다.

## Spec Change Log

## Review Triage Log

### 독립 검토 1회 — 2026-11-09

| ID | 판정 | 근거·처리 |
| --- | --- | --- |
| blind-1 | medium | stage 전체 트랜잭션이 50장 S3 I/O 동안 trip lock을 보유한다. 파일별 승인/읽기 트랜잭션으로 분리해 배치 전체 네트워크 대기를 다른 여행 쓰기에 전파하지 않도록 보완한다. |
| blind-2 | medium | 저장소 STORAGE_UNAVAILABLE와 IOException도 FILE_UNAVAILABLE로 성공 결과에 들어간다. 일시 인프라 실패는 재시도 가능한 작업 실패로 분리한다. |
| blind-3 | low | 최대 임시 용량은 50×15MiB×worker 동시 실행 수로 이미 유한하고 정상 종료/실패 정리는 존재한다. 강제 프로세스 종료 잔류물의 다중 인스턴스 안전 청소는 별도 관리 구성이 필요하여 이번에 복잡한 시작 청소기를 추가하지 않는다. 아래 commit 실패 누수는 실제 경로가 확인되어 별도 수정한다. |
| blind-4 | medium | 결과 조회가 최대50개를 위해 여행 전체 live ID를 읽는다. snapshot ID로 SQL 범위를 제한한다. |
| blind-5 | low | 요청50개·적용50개로 DB 구문 수는 고정 상한이고 일반적인 네트워크 지연은 staging에서 발생한다. 실제 병목이 입증되지 않은 snapshot/apply 전면 배치화는 보류하고 외부 I/O 잠금 범위를 먼저 줄인다. |
| blind-6 | low | 예외 분류가 운영 로그에 없어 장애 진단이 어렵다. 메시지/본문 없이 jobId·분류·예외 클래스만 기록한다. |
| blind-7 | medium | 외부 결과 검증 테스트가 foreign ID 한 경우뿐이다. 검증기 입력의 독립된 잘못된 상태·커버리지·주제·그룹 조합 테스트를 추가한다. |
| blind-8 | medium | staging 시작 전 interrupt만 검증되어 중간 취소의 파일 정리를 놓칠 수 있다. 이전 파일 생성 뒤 스트림 중간 취소 회귀 테스트를 추가한다. |
| blind-9 | medium | 과대 HEAD에서 먼저 거부되어 스트림 크기 상한은 실제 실행되지 않는다. 잘못된 HEAD로 스트림 상한 경로를 검증한다. |
| blind-10 | medium | multipart의 오류 분류는 JSON post 테스트로 검증되지 않는다. multipart5xx/4xx/연결/읽기/응답형식 실패를 직접 검증한다. |
| verification-1 | medium | 그룹 외 사진이 없는 필터 테스트는 SQL 조건 제거를 감지하지 못한다. 경쟁 그룹·미분류 사진을 함께 둔 exact ID 검증을 추가한다. |
| verification-2 | medium | blind-9와 같은 스트림 상한 검증 누락, 함께 수정한다. |
| verification-3 | medium | blind-7과 같은 외부 응답 검증 누락, 함께 수정한다. |
| edge-1 | medium | stage 내부 catch는 Spring proxy가 이후 commit하면서 실패한 경우 반환된 Staged를 닫지 못한다. rollback/commit 실패 동기화와 자원 정리를 보완한다. |

## Verification

- JDK25·Docker로 `cd EodiLog; .\gradlew.bat build` 통과.
- 실제 AI 서버와 SigLIP 모델을 준비하여 실제 사진 업로드→분석→apply→목록/그룹·요약을 검증한다. 테스트 대역만으로 완료를 주장하지 않는다. opt-in 테스트 환경/미실행 사유가 있으면 정확히 보고한다.

### 구현 검증 중간 기록

- 실제 S3+실제 SigLIP 모델 검증 성공: AssetRealS3Test 4개 포함, HttpAiServerClientTest·AssetApiTest 합계 15개 성공(skip0). 실제 S3에 2장 업로드→분류 worker 성공→apply→유사 그룹 목록/요약→동일 apply 재요청을 확인했다. 테스트 객체는 finally에서 정리했다.
- B MR163 공통 코드를 읽어 FilePart 호출 호환을 추가했고 UTF-8/null 생략도 실제 HTTP로 검증했다. 전체 최종 build를 root가 실행 중이다.

### 최종 검증 — 2026-11-09

- 검토 보완 후 root 전체 build 성공: 465개 중459개 성공, 실패0·오류0·외부 opt-in skip6. 모델/저장소 대역 API·worker·HTTP·sanitizer·임시파일/트랜잭션 테스트 포함.
- 별도 실제 연동 최종 성공: AssetRealS3Test.realS3PhotosClassifyWithRealModelAndApplySimilarGroup 1개 성공(skip0). 실제 S3에 같은 PNG2장 업로드→complete/등록→실제 SigLIP 분류→명시 apply→groupId 목록/그룹 집계→동일 apply 재요청을 확인하고 만든 객체를 정리했다. 앞선 실제 S3 전체4개도 모두 성공했다.
- 모델: ViT-B-32-SigLIP2-256/webli, torch2.15.0+cpu. 공식 HF open_clip_pytorch_model.bin 1,507,551,262 bytes와 SHA256 ae518aef1c263e252bafb671a2ffc6a92bbc179261afc42a1de889c9ea5e4196 일치 확인. 기존 캐시의 다른 가중치 파일 해시와 구분했다.
- B MR163 공통 코드 확인·호환 기록은 EodiLog/docs/plan/to-B-photo-ai-compat-2026-11-09.md. jobs discard는 복사하지 않고, B FilePart multipart 호출 계약을 A에 맞췄다. HEIC 권한 테스트는 JPEG로 항상 실행되게 했다.
- 구현/검토 지적 보완 완료. 무관한 미추적 자료·.env는 보존했다. 커밋·푸시는 실행하지 않았다.

### B 코스 제안 통합 후속 — 사용자 '이것도 부탁'

- 원래 baseline은 보존. 현재 통합 기준 dev는 4481f3875e0aaa6e760346f717ccc079e1a9fa35, 원본 A 변경 백업 stash는37470c2debf86fffe1587e99017dd651c1bfeaf7이다. root가 dev fast-forward 후 stash를 복원하고 충돌을 해결했다. 아직 커밋/푸시하지 않는다.
- root가 A 신규 migration을 V202611091300__create_photo_classification_groups.sql로 이름 변경했다. 이미 병합된1200파일은 수정하지 않는다. TripDeleteJobHandler는 photo_topics→photos→photo_groups와 itinerary_undo_states→route_legs→itinerary_items→itineraries를 모두 유지했다.
- 공통 AiServerClient는 B FilePart 메서드와 A 디스크 overload를 모두 유지하며 HttpAiServerClient는 B의 call/MultipartBodyBuilder를 공유한다. 오류로그에서 외부본문/URL을 출력하지 않는다. 필요 시 컴파일/병합 실수만 최소수정하고 A기능을 재작성하지 않는다.
- 추가 작업: 새 migration upgrade 회귀 테스트를 작성한다. Testcontainers 격리 스키마에서 Flyway를1200까지 적용한 뒤1300으로 정상 upgrade/validate 되는지, 이전 사진/코스 관련 데이터·제약이 보존되는지 검증한다. 공개/운영 DB나 .env는 사용하지 않는다.
- 추가 작업: 적용된 사진 그룹과 itinerary_undo_states가 동시에 있는 여행의 TRIP_DELETE가 FK 오류 없이 둘 다 정리하는 통합 테스트를 추가한다. 기존 PhotoUploadApiTest fixture/worker를 재사용할 수 있다.
- B의 AVAILABLE 제약은 시간 필수, 거리/지도선NULL 허용이며 숫자 음수 제한은 기존 CHECK로 유지된다. 기존 ItineraryApiTest/ItineraryProposalApiTest와 A 사진·공통HTTP·jobs 테스트를 검증해 PUT/AIapply/undo/삭제의 공존을 확인한다. root는 B 회신MD와 문서 기록을 담당한다.

### B 코스 제안 통합 검증 완료 — 2026-11-09

- 현재 통합 기준4481f3875e0aaa6e760346f717ccc079e1a9fa35에서 전체 build 성공(4분10초). 총512개 중503개 성공, 실패0·오류0·외부 opt-in skip9.
- PhotoClassificationMigrationUpgradeTest의 Testcontainers 격리 스키마1200→1300 upgrade/validate 및 기존 사진/수동 주제/코스/undo/구간 제약 보존 통과. 적용 사진 그룹+코스undo 공존 여행의 TRIP_DELETE 회귀 검증 통과.
- 통합된 공통AI 호출로 실제S3+실제SigLIP 사진 왕복도1개 성공(skip0, 1분27초): 업로드·분석·apply·group목록/요약·동일apply. 생성객체 정리 완료. 코스 외부AI를 재호출했다고 주장하지 않는다.
- 사진 그룹 migration은 V202611091300__create_photo_classification_groups.sql로 변경했고 구1100 build resource는 남지 않음을 확인했다. 기존 병합1200은 수정하지 않았다.
- B 회신: EodiLog/docs/plan/to-B-itinerary-proposal-check-2026-11-09.md. 백업stash37470c2debf86fffe1587e99017dd651c1bfeaf7 보존. 커밋/푸시 없음.
