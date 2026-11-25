# 어디로그 AI 기능 목록

2026-11-25 · 공개 `main` `592d2351`, 팀 `dev` `887aa10a` 기준. FastAPI 라우터 12개와 앱의 온디바이스 구현, 백엔드 연결, 문서에 남은 실험을 대조했다. **연결**은 코드로 경로를 확인했다는 뜻이다. 이번 실행 범위는 사진 사례 보고서에 기록했다.

## 실행 환경과 근거 읽는 법

- **API** · `ai/`에서 Python 3.11, `uv sync --group dev`, `uv run uvicorn app.main:app --reload`. `/ai/v1` 아래 경로에 내부 토큰을 설정하고 호출한다. 모델·외부 API 사용 시 로컬 `.env`를 설정한다. 통합은 Spring Boot·PostgreSQL 및 Expo/React Native 앱 설정이 필요하다. [AI 명세](../ai/docs/spec.md) · [설정](../ai/.env.example) · [백엔드 실행](../deploy/README.md)
- **GMS** · 저장소 기본값 `gpt-5.6-luna`, OpenAI 호환 요청. 음성은 `whisper-1`로 전사한다. **지도** · 네이버 지역 검색 또는 카카오 경로 API. 좌표·거리·이동 시간은 공급자 응답을 사용한다.
- **기기** · Android 개발 빌드, 사진 접근 권한, 날짜가 있는 여행, 앱 AI 설정, Expo의 `EXPO_PUBLIC_ONDEVICE_MODEL_URL` 또는 기기에 캐시된 모델 네 파일이 필요하다. `npm ci`, 환경 설정, `npm run build:android`, `npm start` 순서다. [앱 실행](../frontend/README.md) · [모델 설정](../frontend/src/features/ondevice/model-store.ts)
- 커밋은 팀 Git의 저자·변경 파일을 근거로 사용했다. 공개 스냅샷에는 팀 이력이 없어 커밋 ID는 원본 Git에서 조회해야 한다. 표에 적은 범위 밖의 개인 기여는 확인 필요다. [앱·백엔드 API](../docs/api-spec.md)

## 앱 기능과 내부 API

| 기능 | 사용자 입력 → 처리 → 출력 | 언어·모델·프레임워크 / 현재 실행 | 앱 연결 | 기존 평가 | 팀 구현과 장수철 기여 근거 |
| --- | --- | --- | --- | --- | --- |
| 장소 추출 | 링크·메모·캡처 → 공개 메타·이미지 정리 → 모델이 언급·지역 단서 추출 → 네이버 후보 검색·검증 → 후보·근거, 사용자 선택 후 저장 | Python/FastAPI, GMS, 네이버 / API `place-extractions`, 공급자 키 | 저장 화면과 작업 결과 화면, Spring `PlaceExtractionJobHandler` | 링크·메모 17건, 합성 캡처 50장, 간판 실험. [캡처](../ai/docs/reports/capture-eval.md) · [종합](../ai/docs/reports/README.md) | 팀 기능. 장수철 초기 API `53f63f62`, 평가 `f2a15eac`, 광고·순위 `a3a8b0fd`. 정인경 지역 단서 등 후속 `caa4fcea`, `9973f9a4` |
| 여행 취향 추정 | 저장·방문·반응 등 허용 신호 → 분류 규칙과 GMS 보완 → 설명이 있는 취향 후보 | Python/FastAPI, GMS / API `preference-inferences` | 취향 화면, Spring `PreferenceInferenceHandler` | [17건 두 차례](../ai/docs/reports/llm-features-eval.md) | 팀 기능. 장수철 AI `089646d9`, 음식 카테고리 수정 `75963ef5` |
| 준비물 제안 | 일정·장소·날씨·기존 항목 → 규칙·GMS 제안과 중복/삭제 항목 정리 → 추가할 준비물과 이유 | Python/FastAPI, GMS / API `checklist-suggestions` | 체크리스트 제안 화면, Spring `ChecklistSuggestionJobHandler` | [18건 두 차례](../ai/docs/reports/llm-features-eval.md) | 팀 기능. 장수철 AI `2021a222`, 동의어 처리 `28077517` |
| 그룹 여행·장소 추천 | 그룹 저장·겹침·취향·지역 후보 → 제한된 후보 순위, 이유 생성 → 추천 ID·추천 근거/자료 부족 | Python/FastAPI, 규칙과 GMS / API `trip-recommendations` | 여행 추천 화면, Spring `TripRecommendationJobHandler` | 서비스 테스트·[명세](../ai/docs/spec.md). 새 독립 모델 품질 평가 확인 필요 | 팀 기능. 장수철 AI `ef31816d` |
| 홈/탐색 추천 | 좋아요/저장·공개 후보의 태그/지역 → 유사 후보 순위 → 피드/장소 ID, 백엔드가 카드 구성 | Python/FastAPI, 규칙 / API `discovery-recommendations` | Spring `DiscoveryService` 호출·인기/최근 대체 경로 | 서비스 테스트·[명세](../ai/docs/spec.md). 라이브 품질 자료 확인 필요 | 팀 기능. 장수철 AI `ef31816d` |
| 친구 추천 | 공통 태그·여행 후보 → 규칙 순위 → 사용자 ID와 이유 | Python/FastAPI, 규칙 / API `follow-suggestions` | 앱의 친구 추천은 백엔드 경로 사용. 해당 FastAPI 호출은 검색에서 확인되지 않음 | 서비스 테스트·[계약 대조](../ai/docs/backend-contract-check.md) | 팀 코드로 남은 AI API. 장수철 `ef31816d` |
| 날씨 대안 | 여행 일정·예보·장소 후보 → 기상 위험·실내 후보·경로 규칙 → 대체 활동·이유 | Python/FastAPI, 규칙과 카카오 경로 / API `weather-alternatives` | 여행 중 날씨 화면, Spring `WeatherAlternativeJobHandler` | 서비스 테스트·[검증 문서](../ai/docs/verification.md) | 팀 기능. 장수철 AI `2c3739cd` |
| 코스 생성·변경 | 여행 기간·저장 장소·현재 코스·제외 장소/날씨 대안 → 지역·일자 분배, 방문 순서, 체류·이동 시간 → 날짜별 코스·변경 내역 | Python/FastAPI, 휴리스틱과 카카오 경로 / API `itinerary-proposals` | 일정 작성·편집/적용 화면, Spring `ItineraryProposalJobHandler` | 서비스 테스트·[검증 문서](../ai/docs/verification.md). 운영 일정 품질 확인 필요 | 팀 기능. 장수철 AI `ef31816d` |
| 이동 구간 재계산 | 수정된 코스 구간·수단·좌표 → 경로 조회 → 시간·거리·수단 또는 `UNAVAILABLE` | Python/FastAPI, 카카오 경로 / API `route-legs` | 코스 편집, Spring `RouteRecalculationJobHandler` | 경로 예시·[검증 문서](../ai/docs/verification.md) | 팀 기능. 장수철 AI `e7818f18`, `b7717a57` |
| 사진 방문 후보 | 사진의 촬영 위치·시각, 여행 기간·일정 장소 → 반경·시각 규칙 → 방문 후보 | Python/FastAPI, 규칙 / API `visit-detections` | 업로드 후 Spring `VisitDetectionHandler`와 사진 배치 흐름 | 서비스 테스트·[명세](../ai/docs/spec.md). 현장 정확도 확인 필요 | 팀 기능. 장수철 AI `6b1f83fc` |
| 서버 사진 주제·유사 묶음 | 업로드 사진 바이트 → 검증·전처리 → SigLIP2 임베딩과 선형 헤드 → 주제·유사 그룹·개별 오류 | Python/FastAPI/PyTorch/open_clip, fine-tuned SigLIP2 / API `photo-classifications`, `uv sync --extra vision` | 업로드에서 기기 결과 없는 사진의 서버 분류 조건 경로. `AUTO`에서 작업 생성→폴링→적용. Spring `ClassificationHandler` | [Wikimedia 원본 77장 및 파생본 15장](../ai/docs/reports/photo-classification-eval.md) | 팀 기능. 장수철 모델·API `921602bd`, `94a78ba1`, `fa508962`. 황승기 백엔드 적용 `36fd7d67` |
| 기기 사진 주제·유사 묶음 | 여행 기간·허용된 로컬 사진 → ONNX 임베딩·분류·유사도 그래프 → 주제 칩·묶음. 선택 업로드 후 사진별 결과 적용 | TypeScript/Expo/ONNX Runtime RN, 증류한 SigLIP2 B-32 int8 / 기기 | 사진 올리기 S30·여행 사진 S31. Spring 기기 결과 등록 API | [1,931장 분류·쌍 기준 및 별도 사진실험 앱 실측](../ai/docs/reports/ondevice-photo-ai.md) | 팀 앱에 합류한 기능. 장수철 모델 스크립트 `03277461`, 앱 `ae314b33`, 서버 수신 `09174325`, 캐시 `af7ebff0` |
| 기기 한국어 사진 검색 | 한국어 검색어·여행 기간·로컬 사진 → 토큰화·4비트 문장 모델·사진 임베딩 내적·상대 점수 필터 → 사진 카드 | TypeScript/Expo/ONNX Runtime RN, SigLIP2 이미지 int8 + 문장 4비트 / 기기 | 마이페이지 → 내 사진 찾기, 사진 올리기 패널. 웹 엔진은 대체 구현 | [검색 Top-5, Galaxy S10 별도 사진실험 앱 실측](../ai/docs/reports/ondevice-photo-ai.md) | 팀 앱 연결과 모델 실험 모두 장수철 `ae314b33`, `03277461`; 상용 배포 상태 확인 필요 |
| 음성 공동 경비 | M4A 녹음·동행 정보 → 오디오 제한·STT → 발화 근거를 검증하며 금액·분담 구조화 → 사용자 확인용 지출 초안·경고 | Python/FastAPI, Whisper 및 GMS / API `voice-expense-drafts` | 경비 녹음·작업 결과 화면, Spring `VoiceExpenseHandler` | 파서·형식·근거 계약 테스트. 독립 음성 코퍼스 실측 확인 필요 | 팀 기능. 장수철 AI `927887c9`, `8447280d`; 앱·Spring 공헌은 여기서 개인 귀속하지 않음 |
| 음성 여행 초안·수정·장소 찾기 | 녹음/수정 문장·일정 초안 → STT·날짜별 구조화·후보 검색 → 여행 초안, 수정안, 네이버 후보 | Python/FastAPI, Whisper·GMS·네이버 / API `voice-trip/jobs`, `jobs/{job_id}`, `fixes`, `candidates` | 실험 기능이 앱 `new-voice`·`voice-draft`와 Spring 프록시에 연결됨. 운영 배포 확인 필요 | [실험 일지](../ai/docs/voice-trip-experiment.md) | 장수철 실험 API `8a34dc19`, 앱 `0180211e`. 운영 제품 지표로 인용할 근거 확인 필요 |

## 실험과 계획 범위

| 항목 | 입력 → 처리 → 출력 / 실행 | 앱 연결·평가·기여 |
| --- | --- | --- |
| 자체 멀티모달 모델로 장소명 읽기 | 캡처·간판 → H200의 Qwen3-VL 계열 등과 GMS 후보 비교 → 장소명 정답·오독·속도. Python 평가 스크립트와 모델 런타임 필요 | 모델 선택 실험. 팀 앱의 GMS 경로와 별개. 장수철 `6562770c`, `9cddf57b`, `60a50641`. [비교 리포트](../ai/docs/vision-llm-comparison.md) |
| 서버 사진 인코더/헤드·경량 CNN 비교 | 라벨·이미지·텍스트 → 헤드 학습, 파인튜닝·증류·양자화, 대체 CNN → 모델 산출물과 평가표. Python/PyTorch/ONNX, 학습 자료·가중치 필요 | 팀 서버에 들어간 것은 fine-tuned SigLIP2, 기기용 선택은 B-32. 작은 CNN은 개인 비교 실험. 장수철 `94a78ba1`, `fa508962`, `08c4ecce`, `03277461`. [모델 보고서](../ai/docs/reports/ondevice-photo-ai.md) |
| 초기 정의의 트렌드·기록 자동 생성 등 | 공개 반응으로 트렌드 후보 산정, 여행 기록 요약 등 초기 제안 | 트렌드·기록 UI가 있어도 전용 생성형 모델 라우터는 확인되지 않았다. 기획 문서의 장수철 변경 `94e5bad8`; 개별 구현 기여 확인 필요. [기능 정의](../ai/README.md) |
