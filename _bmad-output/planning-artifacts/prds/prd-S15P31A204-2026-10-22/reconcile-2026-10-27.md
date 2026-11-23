# PRD·API·ERD 대조 기록 — 2026-10-27

검토 대상은 최신 dev에서 수정한 PRD v0.6, `docs/api-spec.md` v0.4, `docs/erd.dbml` v0.4다. 사용자 변경 요약, `docs/design/open-decisions-2026-10-27.md`, `docs/flow/user-flow.md`를 대조했다. C-1~C-51 원문은 작업 폴더에 없어 그 문서 전체의 반영 완료를 판정하지 않는다.

## 판정

핵심 변경은 요구사항·API 계약·논리 모델에 반영됐다. 검토 중 발견한 이전 방장 수동 투표 종료 인수 조건, 설정 기능 WD-FR-35 누락, Q-15·16 표 분리는 수정 확인했다. 실시간 편집·정산 차액·공개 콘텐츠/비공개 계정의 결합은 구현 전에 합의할 항목으로 남아 있으므로 구현 준비 완료나 팀 전체 합의를 선언할 수 없다.

## 입력 반영 대조

| 입력 결정 | PRD | API·ERD 반영 |
| --- | --- | --- |
| 카카오·네이버, 단방향 팔로우, 공개 즉시/비공개 수락 | WD-FR-01·02 | provider KAKAO/NAVER, 방향별 follow API, `follows` 방향별 유일성 |
| 닉네임 검색만, 추천에서 숨긴 사람 재추천 제외 | WD-FR-02·03 | `/users` 닉네임 검색, suggestion-dismissals 만료 없음, `suggestion_dismissals` |
| 관계 무관 링크 참여, 코드 없음, 누구나 여행 정보 수정 | WD-FR-04 | 초대 accept의 관계 제한 없음, 코드 resolve/필드 제거, 멤버 PATCH |
| 마지막 방장 이탈은 여행 삭제, 기간 기반 상태 전환 | WD-FR-04 | leave의 TRIP_DELETED·삭제 작업, status 쓰기 제거·날짜 기반 파생 규칙 |
| 공동 피드는 명시적 게시로 여행당 하나 생성, 모두 게시/삭제 | WD-FR-28 | 여행 생성 시 피드 없음, feed POST/DELETE, `feeds.trip_id` UNIQUE·tombstone |
| 특정 친구 숨김은 설정자의 노출 경로에만, 사진 동의·항목별 설정 없음 | WD-FR-27·28 | `feed_member_visibilities`·`feed_hidden_viewers`, 직접 공동 피드 열람과 분리, consent/include 계약 제거 |
| 원본 피드 소실 뒤 이름·위치·내 메모만 보존 | WD-FR-06·28 | 제한된 Bookmark DTO, `personal_bookmarks` 이름·좌표 보존 필드 |
| 자동 마감, 기본 24시간, 동률 모두, 0표 미확정 | WD-FR-12 | close/finalize/extend 제거, CLOSED/NO_VOTES·FINALIZED, `poll_results` |
| 진행 중 후보 추가·선택 변경, 후보 추가/1시간 전 알림 | WD-FR-12·34 | candidates POST·ballot 교체, addedAt, 기투표자/미투표자 대상 규칙 |
| 단일 코스·구간별 3수단·누구나 AI 적용 | WD-FR-13~15 | 단일 itinerary PUT/apply, 구간 legs, revision/approval 모델 제거 |
| 실시간 편집·접속/편집 표시, AI 적용 직후 1단계 undo | WD-FR-07·13·15 | Q-15 전송/복구 계약 미정 명시, undo API·`itinerary_undo_states` |
| 캡처 10장, 사진 JPG/PNG/HEIC 50장, 정수 1~5점 | WD-FR-05·19·21 | 요청 한도·형식 검증, `photo_upload_batches`·등록 수, score 정수 |
| 공동 준비물·체크 멤버, 시작일 최신 타임라인·미정 마지막 | WD-FR-17·29 | checkedByMemberId/checkedAt, `checklist_items`, 정렬 예외 규칙 |
| 원화만·1인 부담액 10원 올림·정산 완료 표시 없음 | WD-FR-22·23 | KRW 고정, 원금/올림 부담액/차액 분리, 완료 API·필드 제거, 차액 미정 Q-10 |
| 여행 그룹 채팅만, 게시/방장 양도/정산 완료 알림 없음 | WD-FR-33·34 | DIRECT 생성·필드 제거, 그룹 멤버십 판정, 제외 이벤트 명시 |
| 기존 AI·알림 설정 유지 | WD-FR-35 | UserSettings/SettingsPatch·`user_settings`, 세부 모드는 제안으로 구분 |

## 소스 충돌의 처리

- 결정 기록의 “방장이 종료하기 전”과 “투표 종료 가능/코스 확정 요청” 팝업은 같은 기록의 F-14·F-15로 폐기됐다.
- 공동 피드 삭제 알림은 결정 기록 Q-3과 사용자 흐름 §8.1이 충돌한다. PRD §1.1은 구체 Q 결정을 우선해 삭제 알림을 채택하고 게시 알림은 제외한다. 이는 문서가 명시한 정리이며 팀 전체 합의 완료를 의미하지 않는다.
- 최신 사용자 요청에 따라 별도 사진 공개 동의는 제외한다. 사용자 흐름에 남은 “공동 사진 동의 미정”을 다시 활성 요구사항으로 가져오지 않는다.
- AI 변경안의 “그 사이 바뀜 확인 단계 없음”은 추가 확인 화면의 제거다. 서버가 타인의 변경을 보존하는 방법은 Q-15이고 버전 검사는 설계 제안으로 표시했다.

## PRD 품질 기준 7차원

| 기준 | 평가 | 근거 |
| --- | --- | --- |
| Decision-readiness | adequate | §1.1이 입력 우선순위·정책 충돌·남은 합의를 앞에 배치한다. Q-3·10·15·16 미해결 상태에서 구현 준비 완료로 표시하지 않는다. |
| Substance over theater | adequate | 사용자 여정·FR·권한은 여행 준비/기록 동작에 연결되며 임의 시장 수치나 조사 성과를 주장하지 않는다. |
| Strategic coherence | adequate | 지도 발견→저장→동행 준비→코스→기록/정산→공동 피드의 흐름을 유지한다. 이번 수정은 그 흐름의 정책 정합성을 높인다. |
| Done-ness clarity | thin | 기능별 검증 조건과 경계값이 있으나 실시간 저장/충돌 복구·올림 차액·비공개 계정과 공동 공개의 정확한 기대값은 아직 없다. 해당 범위 구현 인수에는 후속 합의가 필요하다. |
| Scope honesty | strong | 1:1·사진 동의·항목별 공개·정산 완료 제외를 명시하고, C-1~C-51 원문 미확보 및 팀 합의 한계를 유지한다. |
| Downstream usability | adequate | FR01~35를 연속 유지하고 API/ERD 범위 연결을 제공한다. 실제 전송 프로토콜·물리 DB 제약·외부 공급자 선택까지 확정하지 않는다. |
| Shape fit | adequate | 소비자 여행 SNS에 맞는 명명된 여정·용어·FR·인수 조건·비범위·미정 정책 구조다. 기능 변경의 요약이 상세보다 먼저 나온다. |

## 정적 확인 및 남은 한계

- FR01~35의 중복/번호 누락 없음.
- PRD/API의 연속 Markdown 표 열 수 정상.
- ERD 57개 테이블, 123개 inline FK의 참조 테이블/필드 존재 확인. 별도 `Ref` 표현도 대상 필드가 존재한다.
- 상호 친구·개인별 게시·사진 동의·코스 승인·DIRECT 채팅·정산 완료의 폐기 계약은 제거됐다. 링크/캡처·저장·취향·추천·방문/평가·날씨/시설·자료 정리 등의 기존 기능은 유지한다.
- DBML 파서·DDL 실행·백엔드/API 실행 검증은 하지 않았다. 실제 동작 완료 판정은 아니다.
- 후속 합의: 공동 공개 내용·비공개 계정 결합/재게시(Q-3), 1인 올림 적용 시점·차액 귀속(Q-10), 실시간 편집/저장/AI·undo 경합·재접속(Q-15), 코스 변경 알림 묶음(Q-16), C-1~C-51 원문 대조.
