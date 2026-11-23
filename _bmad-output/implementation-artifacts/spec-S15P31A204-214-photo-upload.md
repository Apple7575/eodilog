---
title: '캡처·여행 사진 업로드 및 여행 사진 등록·조회'
type: 'feature'
created: '2026-11-06'
status: 'done'
baseline_commit: '72140a3de3e1b0543c930c0cb3046c6a45a55fd3'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/EodiLog/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

캡처와 여행 사진을 비공개 S3에 업로드하고 검증한 파일만 이용한다. 여행 사진은 배치 생성·등록·목록·멤버 다운로드까지 연결한다. Jira S15P31A204-214, 작업 브랜치 feature/S15P31A204-214-photo-upload.

## Boundaries & Constraints

CAPTURE는 JPG/PNG 및 소유자 접근, TRIP_PHOTO는 JPG/PNG/HEIC 및 ACTIVE 여행 권한을 적용한다. 외부 업로드는 presigned PUT, 다운로드는 인증 게이트웨이와 private/no-store를 사용한다. 메타데이터의 위치·촬영시각은 비공개 저장하고 제공 이미지에서 제거한다. HEIC는 실제 디코딩·JPEG 표시 변환을 검증한다. 시그니처 검사만으로 READY 처리하지 않는다.

사진 편집·개별 삭제·그룹·AI 분류·장소 추출 실행·피드는 제외한다. 기존 API 경로·DTO를 유지한다. 성공 파일은 부분 실패와 독립적으로 남긴다. 커밋·푸시는 별도 지시 때만 한다.

사용자 승인 정책: 파일당 20MiB, 업로드 URL 15분, 배치 24시간, 미완료 파일 24시간 후 정리. 환경 설정으로 조절한다.

## I/O & Edge-Case Matrix

| 상황 | 입력 | 결과 |
| --- | --- | --- |
| 업로드 | purpose·크기·형식 | PENDING asset 및 만료되는 PUT URL |
| 완료 | 본인 파일과 실제 객체 | 크기·디코딩 검사와 메타데이터 제거 후 READY |
| 취소 | 본인 PENDING | CANCELLED, 객체 정리, 이후 complete 차단 |
| 사진 등록 | READY·본인·같은 여행/배치 | 사진 생성과 등록 수 증가를 원자 처리 |
| 경합·재요청 | 같은 asset, 배치 상한 | 중복 사진·중복 차감·한도 초과 방지 |
| 접근 | 타인 캡처·이탈/삭제 여행 | 파일 제공 차단 |
| 정리 | 여행 삭제 | 즉시 접근 차단, 작업에서 파일·사진·배치 정리 |

</frozen-after-approval>

## Code Map

- `docs/api-spec.md` §7·DTO, `docs/erd.dbml` assets·photo_upload_batches·photos: 외부 계약.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/trip/service/TripAccessChecker.java`: 여행 행 잠금과 ACTIVE 검사 재사용.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/global/idempotency/`: 배치 생성 멱등키 재사용.
- `EodiLog/src/main/java/com/ssafy/a204/EodiLog/trip/service/TripDeleteJobHandler.java`: execute 외부 삭제, complete FK 순서 삭제.
- `EodiLog/build.gradle`, `src/main/resources/application*.yaml`: 의존성·설정. 기존 인증과 B 코드는 유지.

## Tasks & Acceptance

- [x] `EodiLog/src/main/resources/db/migration/V202611061400__extend_assets_and_create_photos.sql`: 자식 FK·유일 제약·상태·기한·배치 생성. 병합 전 번호 확인.
- [x] `EodiLog/src/main/java/com/ssafy/a204/EodiLog/asset/`: 컨트롤러·DTO·저장소·서비스·S3 어댑터·이미지 검증·미완료 정리.
- [x] `EodiLog/src/main/java/com/ssafy/a204/EodiLog/photo/`: 배치·사진 등록·커서 목록·접근 권한 구현.
- [x] `EodiLog/src/main/java/com/ssafy/a204/EodiLog/trip/service/TripDeleteJobHandler.java`: 파일 정리 재시도와 FK 삭제 순서 연결.
- [x] `EodiLog/build.gradle`, `EodiLog/.env.example`, 설정 YAML: S3·이미지 변환 설정. 비밀값 제외.
- [x] `EodiLog/src/test/java/com/ssafy/a204/EodiLog/asset/`, `photo/`: 권한·위조 파일·HEIC·동시 요청·만료·Swagger 검사.
- [x] `docs/api-spec.md`, `docs/erd.dbml`, `EodiLog/docs/plan/photo-upload.md`: 구현 계약·로컬/S3 설정·검증 기록.

Given 정상 파일과 권한, when 업로드·완료·등록, then 목록과 다운로드에 표시된다.

Given 동시 등록·부분 실패, when 재시도, then 성공 사진은 유지되고 배치 상한과 asset 유일성이 지켜진다.

Given 파일 취소·여행 삭제·멤버 이탈, when 완료 또는 다운로드, then 상태·권한에 따라 거부한다.

## Implementation Notes

2026-11-06: 구현 diff 및 테스트 XML 직접 대조. 372개 전부 통과, 실패·오류·건너뜀 0. 실제 HEIC 변환과 S3 호환 HTTP 검증 포함. 실제 AWS 버킷·IAM·CORS 검증은 배포 환경 설정 후 별도 진행. 행렬 전체를 PhotoUploadApiTest·ImageSanitizerTest·S3ObjectStorageTest가 검증했다.

## Spec Change Log

## Review Triage Log
| ID | 판정 | 근거·처리 |
| --- | --- | --- |
| B1 | medium | URL 만료 전 시작한 PUT이 삭제 후 끝날 수 있다. 반복 정리 유예 및 uploads/ 필수 수명 정책 문서 보강으로 패치한다. |
| B2 | medium | 시간당 100개 제한은 정상 사진 배치 여러 개에서도 밀릴 수 있다. 조회 제한을 제거해 현재 대상 전체를 처리한다. |
| B3 | medium | 실패한 앞 100개가 뒤 대상을 가린다. B2와 같은 제한 제거로 패치한다. |
| B4 | low | DELETED 행과 만료 배치 보관은 현재 외부 파일 유출을 일으키지 않는다. 일상 규모에서 추가 보관 정책·분기 도입보다 이득이 작아 기각한다. |
| B5 | medium | 배치 만료 검사가 동일 등록 재요청보다 앞서 있다. 기존 동일 등록 응답 후 새 등록에만 만료 검사하도록 패치한다. |
| B6 | low | 외부 I/O 중 여행 잠금은 실제지만 승인 설계의 이탈·삭제 직렬화 수단이다. 통상 사진에서 장시간 지연은 입증되지 않았으며 두 단계 커밋 도입은 복잡하므로 이번 검토에서는 기각한다. |
| B7 | medium | CAPTURE 병렬 완료에 픽셀 버퍼가 중첩될 수 있다. 기존 503 오류를 이용한 완료 처리 동시 실행 제한으로 패치한다. |
| B8 | low | fileCount는 등록 수 상한이라는 계약과 일치한다. 사용자별 용량 정책 없는 상태에서 정상 실패·재시도에도 영향을 주는 새 quota는 도입하지 않는다. 악의적 무제한 요청은 일상 동작보다 방어 정책 영역이라 기각한다. |
| B9 | low | 오류 원인 진단이 사라진다. 비밀 URL·메시지 없이 예외 타입·업무 코드만 로그에 추가한다. |
| B10 | low | 현재 실행은 IMAGE_MAGICK을 설정해 HEIC 테스트가 실제 통과했고 누락 의존성은 문서와 503으로 드러난다. 배포 파이프라인 신규 도입은 이번 일상 코드의 직접 수정 이상이므로 기각한다. |
| E1 | medium | B3와 동일한 앞 대상 실패 시 기아. 대상 전체 처리 패치에 포함한다. |
| E2 | medium | 삭제 tombstone 제거 뒤 진행 중 PUT이 끝나는 경합이 가능하다. B1의 반복 정리 유예·수명 정책 보강에 포함한다. |
| E3 | medium | original_cleaned_at 이후 진행 중 PUT 완료 시 재검사가 없다. B1 패치와 늦은 완료 모사 테스트에 포함한다. |
| E4 | medium | 극단적인 Instant를 Timestamp로 변환하면 범위를 벗어나 500이 가능하다. 입력 시 지원 범위를 확인해 400으로 처리한다. |
| E5 | medium | 공통 커서 디코드는 극단 Instant도 받아 새 목록 쿼리가 실패할 수 있다. 사진 목록에서 지원 범위 검사로 400 처리한다. |
| V1 | medium | 검증 갭: 방향 6과 8을 바꿔도 크기 검증이 통과한다. 비대칭 색 영역의 실제 위치를 검사한다. |
| V2 | medium | 검증 갭: placeId·capturedAt 등록/목록/동일 재요청/변경 충돌 경로가 빠졌다. 실제 장소와 시간으로 테스트 추가한다. |

검토 후 패치 완료: 정리 대상 제한 제거·실패 격리, 원본 반복 정리와 삭제 키 유예, 처리 동시 실행 제한, 만료 뒤 동일 등록 재요청, 시각 범위 검사, 방향·메타데이터 검증 강화. 보류 항목 없음. 2026-11-06 최종 전체 build 4분 36초, 377개 테스트 통과(실패·오류·건너뜀 0). 실제 AWS 버킷 검증은 실행하지 않았고 운영 설정 조건으로 문서화했다.

## Verification

- `EodiLog/`에서 `.\gradlew.bat build`: 전체 테스트·빌드 통과.
- Testcontainers DB 및 S3 대체 테스트로 경합·오류 확인. 실제 S3·HEIC 검증 여부를 별도 기록.
- `/v3/api-docs` 테스트로 신규 API·DTO·Bearer 문서 확인.

## dev 병합 충돌 통합 (사용자 요청, 2026-11-06)

- 통합 기준 dev: `36d14f16336fcd2ae08b695808470f42e0f67b64`. 로컬 전체 작업 백업 stash: `00f1ea9f3a53395af021222d11bdb5bb1da4490f`(유지).
- 최신 dev에 S15P31A204-218 AI 준비물과 S15P31A204-220 assets/S3가 추가됐다. 사용자 요청은 충돌 해결이며 양쪽 기능을 유지한다.
- 충돌 파일: `.env.example`, `src/test/resources/application-test.yaml`, `docs/erd.dbml`. 자동 병합된 설정·의존성과 새 파일도 의미상 충돌한다.
- dev의 기존 assets 마이그레이션 `V202611061300__create_assets.sql`은 수정하지 않는다. 로컬 V1000 중복 생성은 제거하고 V1300 이후의 새 확장 마이그레이션으로 photos/batches와 assets 추가 열을 만든다. 이미 적용된 기존 assets 데이터도 보존한다.
- 파일 API 경로·Spring 빈·S3 클라이언트는 중복 등록하지 않는다. dev의 PROFILE 지원과 STORAGE_BUCKET/STORAGE_REGION·.env 인증 키 지원, AI 준비물 기능을 보존하며 기존 CAPTURE·TRIP_PHOTO와 로컬 사진 배치·등록·검증·HEIC·정리를 통합한다.
- dev에 공개된 파일 최대 15MiB·URL 10분 정책을 기본값으로 유지한다. 로컬 설정 별칭은 호환하되 값 충돌 시 기존 STORAGE_*를 우선한다. .env의 실제 값·키를 출력하거나 덮어쓰지 않는다.
- 단순 시그니처만 통과시키는 dev 테스트 이미지는 실제 유효한 픽셀 이미지로 바꾸고 검증을 약화하지 않는다. 기존 기능의 정상 사례를 삭제하거나 skip으로 숨기지 않는다.
- 전체 build와 PostgreSQL/S3 대체/HEIC/AI 준비물 회귀 테스트를 실행한다. 실제 AWS/AI 테스트는 사용자가 별도 요청하지 않은 외부 I/O이므로 opt-in 상태를 유지한다. 커밋·푸시 금지, 백업 stash 유지.
### dev 통합 검토 판정

| ID | 판정 | 근거·처리 |
| --- | --- | --- |
| MB1 | medium | 완료가 여행 잠금 뒤 용량을 확인해 같은 여행의 병렬 요청이 기다린다. 처리 용량 확인을 잠금 앞으로 옮기고 재진입 가능한 내부 락으로 lazy 변환 경로도 보호한다. |
| MB2 | medium | 다운로드 전체 버퍼는 사진 동시 열람 시 힙 사용량이 중첩된다. 권한 검사 후 기존 스트리밍 응답을 복원한다. |
| MB3 | medium | 사진이 많은 여행 삭제는 재시도마다 앞부분 외부 삭제를 반복해 실행 예산을 소진할 수 있다. 각 파일 삭제 성공 후 기존 DELETING 상태로 진행을 기록해 재시도에서 건너뛴다. |
| MB4 | medium | 미완료 TTL < URL TTL 설정이 기동을 통과하고 DB CHECK로 요청마다 실패한다. 시작 시 교차 설정을 검사한다. |
| MB5 | medium | 변환 timeout이 INVALID_ASSET으로 분류되어 정상 원본도 삭제된다. 변환기 503으로 분리하고 원본·PENDING을 보존한다. |
| MB6 | medium | read 외 HEAD/write/delete SDK 예외가 공통 저장소 오류로 바뀌지 않는다. S3 어댑터에서 같은 503 업무 코드로 변환한다. |
| MB7 | low | 인코딩 버퍼는 사후 크기 검사지만 픽셀 상한과 인스턴스별 단일 처리로 총량이 이미 제한된다. 일상 파일에서 추가 할당 피해가 입증되지 않았고 새 제한 스트림 구현은 복잡해 기각한다. |
| MB8 | low | 이전 B2/B3 패치로 전체 대상을 처리하며 일반 서비스 규모의 ID 목록 메모리는 작다. 추가 keyset 처리·스케줄 예산은 현재 일상 피해보다 복잡성이 커 기각한다. |
| MB9 | low | carried B10: IMAGE_MAGICK 지정 전체 실행에서 실제 HEIC가 검증됐다. 신규 배포 CI 도입은 범위 밖 일상 직접 수정 이상의 작업이라 기각한다. |
| MB10 | low | create Swagger의 422 안내가 보존한 400 계약과 다르다. 해당 잘못된 응답 설명을 제거하고 문서 검증을 보강한다. |
| ME1 | medium | MB4와 동일한 교차 TTL 불일치. 같은 시작 검증 패치에 포함한다. |
| MV1 | medium | 검증 갭: READY이지만 미등록인 배치 파일의 owner·ACTIVE 멤버 다운로드 거부 사례가 없다. 등록 전 404·등록 후 성공 테스트를 추가한다. |

통합 완료 검증(2026-11-06): 검토 패치 후 전체 build 3분 36초 통과. JUnit XML 412개 중 409개 실행 통과, 실패·오류 0, 실제 AWS 2개·AI 1개 opt-in 제외. Git U 항목·충돌 마커·MERGE_HEAD 없음. V1000 AI·V1300 assets 기존 병합 마이그레이션 수정 없음. 실제 .env 보존, 백업 stash 유지, 커밋·푸시 없음.
