# 어디로그 Android 사진 검색 캐시 실험

## 실기기 상태

Galaxy S22 `SM-S901N`의 USB 디버깅 연결을 복구한 뒤 실기기에서 100장 A/B와 10장 추가 C를 완료했다. 아래는 반복에 쓰는 실행 기준이며, 수치와 영상은 별도 보고서에 있다. [실기기 결과와 영상](real-device/REPORT.md) · [ADB 상태](device-status.txt) · [시나리오 상태 CSV](run-plan.csv) · [영상·정답 대조 기록 양식](video-observations.csv)

기존 모델 리포트의 **4.3GB 교사 → 191 MiB 배포 ONNX**, 교사·최종 모델의 **검색 Top-5 78.5%**는 모델 평가 결과로 보존한다. 학습 전 B-32 대비 **Top-1 27.3% → 47.4%**는 Windows CPU 재현이다. [모델 리포트](../../ai/docs/reports/ondevice-photo-ai.md) · [CPU 재현](../ONDEVICE-FOLLOWUP.md)

## 계측과 기기 준비

- 앱 기준은 로컬 `c1d241267d99f6fbda526d9e38de771b6b8d7916`과 이 계측 diff다. 계측용 APK를 만들 때 `EXPO_PUBLIC_ONDEVICE_BENCHMARK=1`을 설정하고 작업 커밋 또는 diff SHA-256, APK SHA-256, `versionName`·`versionCode`, JS 번들 방식, Android 모델·OS·SDK, 모델 네 파일 SHA-256과 캐시 버전을 남긴다. 앱 화면과 캐시 구현의 기준 커밋은 장수철 `ae314b33d1715a468d4737e72ee681de0cd05981`, 버전별 캐시·파일 검증은 장수철 `af7ebff010afd8e5f1c23d3fb22cd3618462ad42`다. 계측 diff를 새 캐시 구현으로 귀속하지 않는다.
- `EXPO_PUBLIC_ONDEVICE_MODEL_URL`로 모델을 한 번 받은 뒤 예정된 파일이 있는지 확인한다. 기존 검증 파일 세트의 계산 버전은 `el9kw5`다. 기기는 `index-start` 로그의 실제 버전을 기록한다. 권한과 날짜가 있는 테스트 여행을 준비하고 Android의 모든 사진 접근을 확인한다. 준비 중 다운로드를 잰다면 `model-download`를 별도 행으로 남긴다.
- 전용 기기 또는 전용 사용자 프로필에서 진행한다. `make-fixtures.py`는 기존 합성 JPEG 60장을 늘려 부하를 만든다. 의미가 유사한 중복 구도가 많아 검색 품질과 묶기 비용의 일반화에 제한이 있다. 파일 최대 변은 1280px이고, 원본 타깃은 예약한다. 파일을 기기 공유 사진 폴더에 가져와 MediaStore에 나타나는지 확인한다. 여행 기간에는 기기가 기록한 **생성 시각**이 들어가야 한다. 대상 이외 사진은 범위에 넣지 않는다. 앱 `gallery-list`의 후보 장수와 `index`의 fixture 장수를 대조한 뒤 정식 측정한다.
- 앱에는 **모든 여행 기간을 합한 후보 최대 1,000장** 제한이 있다. 5,000장 투입은 이 빌드에서 탐색 상한을 관측하는 조건이다. 5,000장 인덱싱 실측으로 기록할 수 없다. 1,000장 이후에 추가하면 신규 사진이 기존 후보를 밀어낼 수 있으므로 `fixtureAdded`, `freshAdded`, `reusedAdded`를 확인하고 990장→1,000장 조건도 수행한다. [후보 상한과 캐시 조회](../../frontend/src/features/ondevice/gallery-ai.ts)

예시 PowerShell. 새 폴더 경로를 각각 사용한다.

```powershell
$toolsDir = 'portfolio-verification/android-cache'
python "$toolsDir/make-fixtures.py" ai/eval_data/photos .tmp/cache-base-1000 --count 1000
python "$toolsDir/make-fixtures.py" ai/eval_data/photos .tmp/cache-added-1000 --count 10 --offset 1000
adb devices -l
$device = 'ANDROID_SERIAL'
$package = 'com.ssafy.eodilog'
adb -s $device shell run-as $package ls files
# 테스트 앱 전용 파일 한 개다. 현재 모델 버전과 경로를 확인한 뒤 A에서만 실행한다.
adb -s $device shell am force-stop $package
adb -s $device shell run-as $package rm -f files/ondev-embeddings-el9kw5.json
```

`run-as`가 허용되는 계측 빌드를 사용한다. A에서는 앱 데이터 전체를 초기화하지 않는다. 모델의 세션 로드는 재진입에 포함하고 `modelWaitMs`로도 따로 남긴다. 신규 사진 파일 `EODIBENCH_NEW_*`는 C까지 가져오지 않는다. 5,000장 조건에서 최초 2개 타깃이 상한 밖일 수 있다. 영상과 CSV에는 실제 후보 안에 남은 타깃만 사용하거나 해당 질의를 `excluded_by_cap`으로 표시한다.

## 반복 시나리오와 시점

| 시나리오 | 준비 | 유효성 확인 |
| --- | --- | --- |
| A · 첫 인덱싱 | 매 반복 전에 중지하고 현재 버전의 임베딩 JSON만 삭제한다. 검색 화면을 열고 바로 `정리하기`를 누른다. | `cacheEntriesBefore=0`, `reused=0`, `fresh=indexed`, `download=false` |
| B · 캐시 재진입 | A 완료 후 `am force-stop`으로 프로세스를 종료한다. 사진과 캐시를 그대로 두고 앱을 다시 실행한다. | 기기·사진·모델·APK 동일, `fresh=0`, `reused=indexed`인지 관측한다. |
| C · 새 사진 추가 | A/B와 같은 캐시를 보존하고 파일 10개만 추가한다. 미디어 스캔 후 앱 프로세스를 다시 열어 측정한다. | 신규 인코딩 `freshAdded`, 기존 인코딩 `fresh − freshAdded`, 신규 재사용 `reusedAdded`, 기존 재사용 `reused − reusedAdded`를 기록한다. 남은 후보가 1,000장으로 제한되는 경우 퇴출을 기록한다. |

- 조건당 A→B→C를 3회 권장한다. C 다음 반복은 추가 파일만 테스트 앨범에서 제거한 뒤 MediaStore에 반영하고 원래 파일 집합을 복원한다. 짧은 실행에 메모리 샘플이 없다면 공란으로 남긴다. 원시값, 횟수, 중앙값과 범위를 보고한다.
- **화면 진입**은 검색 화면 마운트, **정리 시작**은 현재 실행 ID의 `index-start`, **임베딩 완료**는 `index-finished`, **전체 검색 준비**는 `ready-frame`이다. `screenToReadyMs`에 버튼 누르기까지의 시간이 포함되므로 `indexStartToReadyMs`도 같이 보고한다. 성공적으로 처리한 후보가 목표 전체인지 확인한 후 완료로 취급한다. 현재 UI는 준비 중 진행 카드만 노출하도록 구현돼 있다. 영상에서 정리 중 사진 노출 여부와 첫 사진 표시 시점을 별도로 관측한다.
- **검색 시작**은 마지막 한국어 텍스트 변경 이벤트. `debounceMs`는 그 이벤트에서 타이머 발화까지, `inferenceMs`는 토큰화와 문장 ONNX 추론, `rankMs`는 순위·필터·타일 매핑 시간이다. `query-frame`은 React 반영 뒤 프레임 콜백이며 실제 디스플레이의 픽셀 표시 시점은 영상으로 확인한다. 키보드 조합 완료 시점과 첫 결과 사진 또는 빈 상태 표시 프레임을 기록한다. 영상만으로 마지막 이벤트를 특정할 수 없으면 영상 지연을 공란에 둔다.
- **메모리**는 정리 시작부터 ready 로그 수신까지 `dumpsys meminfo`로 관측한 최대 표본 PSS다. 1초 간격에 명령 실행 시간이 추가된다. 실제 순간 피크를 보장하는 값으로 해석하지 않는다. 영상 녹화 비용을 피하려면 정량 반복과 영상 실행을 별도로 구분한다.

## 수집과 영상

아래 `--photos`에는 시나리오의 예상 **실제 후보 장수**, `--seeded`와 `--added`에는 기기에 투입한 수를 입력한다. 실행 전에 앱 프로세스를 종료하고, 수집기가 시작된 후 검색 화면을 연다. 마지막 질의가 표시된 뒤 `Ctrl+C`로 수집을 종료한다. 앱을 직접 조작하기 전 ADB의 기기 모델·빌드 정보를 실기기와 대조한다.

```powershell
python "$toolsDir/measure.py" collect --serial $device --package $package --commit COMMIT_OR_DIFF_ID --apk-sha256 APK_SHA256 --scenario A --rep 1 --photos 100 --seeded 100 --out .tmp/cache-runs/100-A-1
python "$toolsDir/measure.py" summarize .tmp/cache-runs --labels "$toolsDir/video-observations.csv"
```

- `index-runs.csv`와 `query-ranks.csv`에서 완료 여부·장수·순위를 확인한다. 질의 순서와 `queryId`는 영상 기록 양식에 매핑한다. 사진은 전체·모든 여행 필터로 맞추고 A/B에서 동일한 두 질의 `그릇에 담긴 비빔밥`, `가을 단풍이 든 산길`을 각각 입력한다. 각 질의 사이 입력을 지우고 결과가 안정된 다음 입력한다. 두 동일 질의의 정답 순위, 순서 있는 결과 목록과 순서를 무시한 집합을 비교한다. C에선 위 두 질문 후 `호텔 문을 여는 카드 키`로 추가 배치의 마지막 타깃을 확인한다. `manifest.csv`의 타깃 ID를 기준으로 판정한다.
- 영상 수집은 별도 터미널에서 `adb -s $device shell screenrecord --time-limit 120 /sdcard/eodilog-cache-demo.mp4`를 시작하고, 조작 완료 뒤 `adb -s $device pull /sdcard/eodilog-cache-demo.mp4 .tmp/cache-runs/`로 받는다. 실기기에서 테스트 앱 한국어 입력, 결과 표시, 정답 타일 확인이 이어지는 한 구간을 보존한다. 논리적 ready와 표시 시점을 영상에서 구분한다.
- 오프라인 검증은 모델·여행·권한을 준비한 **검색 화면을 유지**하고 Wi-Fi·모바일 데이터를 끈 뒤 동일 질의를 실행한다. USB ADB로 로그를 받는다. 프로세스를 끈 상태의 오프라인 첫 진입은 별도 시행이다. 여행·설정 API가 필요한 실제 계정 경로와 테스트 API 환경을 구분해 기록한다. [검색 화면 진입 경로](../../frontend/src/features/ondevice/screens/photo-search-screen.tsx)

## 제목 후보 · 실측 후 채울 값

1. 여행 사진 **[N]장**의 임베딩을 재사용해 Android 재진입 후 검색 준비 시간을 **[A 중앙값]초 → [B 중앙값]초**로 단축.
2. Android 여행 앨범에 사진 **[추가 N]장**을 넣어 기존 **[재사용 N]장**을 재사용하고 새 사진을 한국어 검색 결과에서 확인.
3. **[기기·사진 N장]**에서 캐시 재진입 준비 시간 **[B 중앙값]초**, 오프라인 한국어 입력부터 첫 결과 표시까지 **[영상값]ms** 확인.

실기기에서 확인한 묶기 병목은 동일 임베딩 쌍 연산의 재사용으로 개선했다. 제품 임베딩 캐시 정책, 1,000장 제한, 검색 순위는 유지했다. [실기기 개선 비교](real-device/REPORT.md) · [Expo SDK 58 레퍼런스](https://docs.expo.dev/versions/v58.0.0/)

호스트 검증은 합성 파일 100+10장 생성, 테스트 로그의 CSV 집계와 A/B 순위 비교, 기존 검색·모델 규칙 테스트 21건, 변경 파일 lint를 통과했다. 프로젝트 typecheck는 변경하지 않은 `pressable-scale.tsx:55`의 `hovered` 타입 오류로 실패했다.
Windows SDK 연결 확인은 [device-status.txt](device-status.txt)에 기록했다. ADB가 PATH에 없으면 수집 명령에 `--adb <SDK>/platform-tools/adb.exe`를 지정한다. 영상 기록 양식에 런 ID와 질의 ID를 입력한 뒤 `measure.py summarize <run-directory> --labels <filled-video-observations.csv>`를 실행하면 `rank-comparison.csv`에 A/B 정답 순위와 결과 순서·집합 비교가 생성된다. `index-summary.csv`에는 완료 런의 횟수, 중앙값과 범위를 기록한다.

호스트 준비 검증에서 합성 JPEG BASE 1,000장과 NEW 10장을 생성했다. 합성 이벤트로 원시·요약·질의·A/B 순위 대조 CSV 생성을 확인했다. 온디바이스 Jest 21개가 통과했다. 전체 TypeScript 검사에는 기준과 동일한 기존 진단 8개가 남았으며 계측 코드로 새 진단은 생기지 않았다. 이 검증은 APK 설치 또는 실기기 실행을 포함하지 않는다.
