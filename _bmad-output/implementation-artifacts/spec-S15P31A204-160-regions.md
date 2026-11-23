---
title: 'S15P31A204-160 법정동 지역 시드와 조회 기반'
type: 'feature'
created: '2026-11-02'
status: 'done'
route: 'dispatch'
baseline_commit: '165e84af811d356fa0d81cd64b565f439e3c6e3a'
review_loop_iteration: 0
context:
  - 'EodiLog/AGENTS.md'
  - 'EodiLog/docs/plan/places-regions-contract-to-B-2026-11-02.md'
---

<frozen-after-approval reason="A/B 계약 합의와 사용자의 지역 기반 구현 진행 승인">

## Intent

A의 지역 기반을 구현한다. 공식 법정동 자료에서 존재하는 시·도/시·군·구 2단계를 시드하고 일반구는 상위 시로, 세종은 최상위 하나로 매핑한다. RegionReader와 로그인 필수 검색·상세 API를 제공한다. 카카오 호출·장소 API·즐겨찾기·B 투표/코스는 제외한다.

## Boundaries & Constraints

- 기존 regions 구조·이미 사용된 UUID와 FK·테스트 문자열 코드를 보존한다. 기존 migration 수정·삭제·outOfOrder 없음. 신규 지역 UUID는 고정된 v7이며 재적용·다른 DB에서 같은 시드 ID를 쓴다. 같은 code가 이미 있으면 기존 ID를 유지하고 자식/별칭은 실제 기존 ID를 참조한다. 대표 좌표는 확보 안 된 것이므로 null로 둔다(기존 좌표는 지우지 않음).
- 공식 원본의 현재 존재 코드만 사용한다. 과거 17개 시도 같은 고정 가정을 넣지 않는다. 폐지 코드를 이름 유사성으로 새 코드에 임의 연결하지 않는다. 원문·필터·hash·재생성 절차를 기록한다.
- RegionView는 합의한 id/code/name/parentId/BigDecimal nullable latitude/longitude record. 이름은 공식 전체 법정동명(trim)으로 보존해 동구 등 동명을 구분한다. Reader find/findAll은 Optional/Map, 없는 ID 생략·중복 제거·빈 입력 SQL 없음.
- GET /api/v1/regions?query=...&cursor=...&limit=... → PageResponse<RegionView>. query 필수, strip 후 1~200자, 기본 limit20/최대100. 이름의 문자 그대로 부분 검색(%/_를 wildcard로 취급하지 않음). regions에는 createdAt이 없으므로 code ASC,id ASC 정렬의 전용 Base64URL 커서를 쓰고 query에 바인딩한다. 잘못된/다른 query 커서 400. 공통 응답 모양은 유지하고 정렬 예외를 명세에 기록한다.
- GET /api/v1/regions/{regionId} → DataResponse<RegionDetail>: region, introduction=null, representativePlaces=[],partialErrors=[]. 없는 지역 404 REGION_NOT_FOUND. UUID/입력 오류400, 인증/가입완료는 기존 Security 동작 유지. 명세 경로·필드 및 Swagger 유지.
- RegionCodeResolver는 10자리 법정동 코드에서 Optional<RegionView> 반환. 정상 시군구·하위 읍면동은 5자리 기준 지역, 일반구는 명시적 alias 표로 상위시, 36110xxxxx는 세종3611000000. 잘못된·미매핑·폐지 코드는 empty. 새 장소 provider가 이후 이 인터페이스를 재사용할 수 있게 문서화한다.

## I/O & Edge-Case Matrix

| 상황 | 기대 |
| --- | --- |
| 공식 seed | 최상위16(세종 포함), 하위229, 전체245. 일반구 row 없음, alias39 |
| 기존 코드·참조가 있는 DB에 seed | UUID·기존 참조·좌표 보존, 자식/alias가 기존 부모 ID 사용 |
| 법정동 41111xxxxx / 36110xxxxx | 수원시4111000000 / 세종3611000000 반환 |
| 미매핑·잘못된 코드 | empty, 임의 province fallback 없음 |
| 검색·후속 페이지 | 안정 정렬·누락/중복 없음, no-match 빈 목록 |
| 잘못된 입력·커서·ID | 400 또는 없는 지역404, 공통 JSON |
| Reader 빈/중복/없는 ID | 빈 요청 SQL없음, 한 IN 조회·누락 ID 제외 |

</frozen-after-approval>

## Code Map

- `region/domain/Region.java`, `region/repository/RegionRepository.java`: 기존 B 호환 유지. 낡은 코드체계 미정 주석만 정리 가능.
- `place/service/JdbcPlaceReader.java`, `place/dto/PlaceView.java`: Reader와 record·Swagger 관례 재사용. 기존 PlaceResolver나 B 기능은 수정하지 않는다.
- `global/common/response/PageResponse`, `DataResponse`, `global/common/error/*`, TestcontainersConfiguration 및 AuthUserRequestPostProcessors 재사용.
- 공식 https://www.code.go.kr/etc/codeFullDown.do?codeseId=%EB%B2%95%EC%A0%95%EB%8F%99%EC%BD%94%EB%93%9C . CP949 TXT 임시파일 `C:/Users/SSAFY/AppData/Local/Temp/legal-region-full.txt` (SHA256 962fd4cdfb6ccf2887b745eb97db55f71112b9f9a32c1f8fbd7692fb069b1df0), ZIP은 `legal-region-full.download` (SHA256 44a3fe4cacf88ce98e35fb883807d2725b589f427ff4d73ee40b914d1286bacd).
- 정규화 JSON `C:/Users/SSAFY/AppData/Local/Temp/legal-region-normalized.json` nodes245, metadata포함. 일반구 alias39는 `legal-region-general-gu-aliases.json`. JSON 구조를 직접 확인하고 사용한다. 원본 이름에 부천 일반구 후행 공백이 있어 trim 필요.
- 원본 ZIP entry 수정시각2026-10-01T09:06:34+09:00, 다운로드2026-11-02. 이 시각은 법적 시행일이 아니다. 최신 자료는16개최상위이며 Sejong3611000000, 일반province15개. 3600000000 합성 금지. 12코드 존재·29/46폐지 등 원본 그대로 사용. 원문 일반구명 토큰3개를 같은 앞2개 도시로 연결하며 별칭39개. 원본시도+세종+직접2토큰시군구만 seed.

## Tasks & Acceptance

- [x] `region/dto`, `region/service`, `region/controller`, 오류·cursor — Reader, 안전한 검색/상세, 법정동 매핑·명세 DTO·Swagger.
- [x] `db/migration/V202611021500__seed_regions.sql` — seed245 및 alias39테이블/데이터, 기존ID보존. 원본 seed manifest와 재생성/검증 스크립트는 `EodiLog/docs/data/regions/`·`EodiLog/scripts/` 등 문서화된 경로에 보관. 스냅샷만으로 SQL재생성 가능하게 하고 UUID는 고정한다.
- [x] `src/test/java/.../region/**` — 실제 PostgreSQL에서 matrix 검증. seed 수·계층·별칭전체무결성·일반구/세종·기존행보존·Reader IN/빈SQL·pagination·wildcardliteral·권한/Swagger. 기존 PlaceFoundationTest와 모든 B 테스트 회귀.
- [x] `docs/plan/regions-foundation.md`, 지역계약의 지역 구현 결과, `docs/api-spec.md` 지역행 및 정렬·오류만 갱신. B가 재사용할 정확한 클래스·시드·매핑 사용법·현재코드스냅샷 한계 안내.

수용 기준:
- Given 빈 DB, when Flyway 실행, then 공식245개 지역과39개별칭이 부모참조에 맞게 존재.
- Given 기존 같은code지역과FK, when 신규seed 적용, then 기존UUID/참조/좌표 보존.
- Given 일반구·세종·미매핑코드, when 내부resolve, then 합의한 지역 또는empty.
- Given 로그인사용자와검색조건, when 페이지 탐색·상세, then 명세응답·안정페이지·400/404 동작.
- Given 기존서비스, when 전체build, then 모든기존테스트와지역테스트성공.

## Implementation Notes

- Jira160 / branch feature/S15P31A204-160-regions. 기존 미추적 EodiLog/.omc는 사용자 작업으로 보존·스테이징 금지.
- 사용자가 최신 A/B 장소 계약 다음 지역기반 구현을 승인했다. seed자료 추출·현재계층과cursor기술선택은 본 구현의 구체화이며 추가 정책/배포 변경 없음.
- 커밋·푸시·MR·실제운영DB변경 없음. 전체 build와 diff검증 후 결과를 보고한다.

## Verification

- `EodiLog/gradlew.bat build --console=plain`: BUILD SUCCESSFUL, 267개 테스트, 실패·오류·스킵 0. Swagger는 `/v3/api-docs` 통합 테스트로 검증했다.
- `scripts/generate-region-seed.ps1 -Check`: 공식 ZIP/TXT 해시, 245개 지역 계층, 39개 별칭, UUIDv7 manifest 및 SQL 일치 확인.
- `git diff --check` 통과. 리뷰에서 확인한 경계와 테스트 공백 보완 완료, 보류 없음.
- Jira S15P31A204-160에 결과 기록. 커밋·푸시·MR·운영 DB 적용은 수행하지 않았다.

## Review Triage Log

| ID | 판정 | 근거·처리 |
| --- | --- | --- |
| B1 | medium | 기존 동일 코드 행에 parent_id가 없으면 seed가 계층을 복원하지 못한다. ID·이름·좌표는 보존하고 부모 연결만 갱신하는 patch. |
| B2 | medium | 임의의 기존 자식 행도 현재 코드로 인정되어 폐지 코드가 반환된다. 공식 스냅샷의 현재 대상 목록으로 제한하는 patch. |
| B3 | medium | NUL이 포함된 검색어나 커서 코드는 PostgreSQL text 입력 오류로 500이 된다. DB 전에 VALIDATION_ERROR로 거부하는 patch. |
| B4 | medium | 기존 코드에 구분자 파이프가 있으면 생성한 커서를 다시 해석할 수 없다. 코드 자체를 인코딩하는 patch. |
| B5 | low | 일반 build가 원본·manifest·SQL의 불일치를 검사하지 않아 데이터 변경 오류를 놓친다. 외부 실행환경 없이 JUnit으로 검증하는 patch. |
| B6 | false | 생성기는 manifest의 고정 UUID를 그대로 사용하며 무작위 재생성이 없다. manifest와 Flyway 파일이 코드별 ID의 기록이므로 별도 수정 가능한 해시를 추가해도 ID 변경 방지는 강화되지 않는다. 기각. |
| B7 | low | 구조가 있는 잘못된 커서의 검증 분기를 테스트하지 않는다. 실제 형식별 400 회귀 검증 patch. |
| B8 | low | 정확히 limit개, limit+1개, 마지막 이후 빈 페이지 경계가 검증되지 않았다. 통제된 데이터로 페이지 계약 검증 patch. |
| B9 | low | 다른 검색어의 커서를 RuntimeException으로만 검증하여 DB 오류도 통과한다. 구체적 VALIDATION_ERROR 검증 patch. |
| B10 | low | DTO의 부모·좌표 필드 누락을 기존 테스트가 발견하지 못한다. 값이 있는 자식 지역을 Reader와 상세 JSON에서 검증하는 patch. |
| E1 | medium | B1과 동일하게 기존 도시의 null 부모가 복원되지 않는 상태를 확인했다. 같은 부모 연결 patch. |
| E2 | medium | 보존된 일반구 행과 alias가 함께 존재하면 UNION의 첫 행이 도시라는 보장이 없다. alias 우선 및 공식 대상 조회 patch. |
| E3 | medium | 검색 NUL이 DB까지 전달되는 상태를 확인했다. B3의 입력 검증 patch. |
| V1 | low | 사전 검증된 테스트 공백: 일반 시군구 및 하위 법정동에서 실제 대상 지역으로 매핑되는 성공 경로가 없다. 종로구 두 코드 검증 patch. |
| V2 | low | 사전 검증된 테스트 공백: nonnull 부모와 서로 다른 소수 좌표를 Reader·API에서 확인하지 않는다. B10과 같은 필드 검증 patch. |
| P1 | low | Windows CRLF 체크아웃에서 생성기의 LF 결과와 비교하면 내용이 같아도 -Check가 실패한다. 비교 시 줄바꿈만 정규화하는 patch. |

모든 검토 결과를 개별 판정한 뒤 같은 원인의 수정만 묶었다. 공개 계약 변경이나 보류 항목은 없다.
