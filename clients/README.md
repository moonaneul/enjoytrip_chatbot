# 온가 — 가족과 함께하는 편안한 여행 (Front-End v5)

개발자 1 인수인계. HTML / CSS / Vanilla JS만 사용하며 빌드·패키지 설치 없이 실행합니다.
**Shared API Contract는 v1부터 지금까지 한 번도 바뀌지 않았습니다.** v5는 표현만 손그림으로 바꿨습니다.

## 주요 기능과 화면

### 1. 지도로 바로 가는 링크 (v3)

시설 카드에서 주소를 복사하는 데서 끝나지 않고, 눌러서 지도 앱으로 넘어갑니다.

```
🚻 화장실
   경복궁
   어디 안   입구 안내소 옆
   주소      서울특별시 종로구 사직로 161
   [ 카카오맵에서 열기 ↗ ]
   [ 주소 복사 ]
   ▸ 다른 지도로 열기        ← 펼치면 네이버지도 · 구글지도
```

- **지도 SDK를 쓰지 않습니다.** 인증키도, 외부 스크립트도, 좌표 처리도 없습니다. 평범한 하이퍼링크입니다.
- 링크는 서버가 준 `map_search_text`를 `encodeURIComponent`로 감싸서 만듭니다. 프런트에서 주소를 조합하지 않고, `location_detail`을 검색어에 섞지 않습니다.
- `target="_blank" rel="noopener noreferrer"`.
- 마지막에 고른 지도 앱을 기억해 다음 카드부터 기본으로 올립니다.
- `map_search_text`가 없거나 공백이면 링크도 복사 버튼도 만들지 않습니다.
- **복사 버튼은 그대로 둡니다.** 인앱 브라우저에서 새 창이 막히면 그게 유일한 수단입니다.

| 지도 | URL 형식 |
| --- | --- |
| 카카오맵 | `https://map.kakao.com/link/search/{검색어}` |
| 네이버지도 | `https://map.naver.com/p/search/{검색어}` |
| 구글지도 | `https://www.google.com/maps/search/?api=1&query={검색어}` |

카카오톡 링크 미리보기처럼 상대 페이지의 OG 태그를 긁어오지는 않습니다. 브라우저에서는 CORS로 막히고 그러려면 서버가 필요합니다. 대신 이미 가지고 있는 시설명·상위 장소·내부 위치·주소로 카드를 직접 만들고, 썸네일 자리에는 **시설 종류별 인라인 SVG 픽토그램**을 넣었습니다. 외부 이미지 요청이 0건이라 느려지지 않습니다.

픽토그램: 화장실 · 수유실 · 기저귀 교환시설 · 주차장 · 쉴 곳 · 엘리베이터. 미등록 `type`은 기본 핀으로 그립니다. 아이콘만으로 뜻을 전하지 않고 항상 시설명 텍스트와 함께 둡니다.

### 2. 화면 — 손그림 (v5, 이번 변경)

v4의 기하학적 스타일 위에서 선과 색과 폰트만 손그림으로 바꿨습니다. 기능은 한 줄도 건드리지 않았습니다.

**선과 모서리**

- 8값 `border-radius`(`255px 15px 225px 15px / 15px 225px 15px 255px`)로 손으로 그린 상자를 만듭니다. 이미지도 SVG도 쓰지 않습니다.
- 카드마다 `--hand-1 / 2 / 3`을 번갈아 줍니다. 전부 같으면 손그림으로 보이지 않습니다.
- 하드 섬도우를 전부 걷어냈습니다. 깊이는 2.5px 잉크 선과 1도 이하 기울기가 만듭니다.
- 시설 카드와 메모지에만 기울기를 줍니다. 대화 카드와 입력창은 반듯합니다.

**색 — 파스텔 채움 + 진한 잉크 글자**

| 항목 | 값 |
| --- | --- |
| 종이 / 잉크 | `#FDFBF3` / `#2E2E2E` |
| 채움 | `#FFE9A8` 버터 · `#CFE9D4` 민트 · `#FBD9DE` 블러시 · `#CFE2F3` 스카이 · `#E0D7F5` 라일락 |
| 형광펜 | `#FFE066` |

글자색은 상태와 무관하게 늘 잉크색 하나입니다. 바뀌는 것은 배경뿐이라 대비가 오히려 좋아졌습니다.

**폰트 — 손글씨는 액센트만**

이 서비스의 주 사용자는 부모님 세대이고, 화면에 담기는 것은 주소·시설명·판단 결과 같은 사실 정보입니다.
그래서 손글씨(Gaegu)는 아래에만 씁니다.

```
브랜드 · 표제 h1 · 섹션 라벨 · 서랍 제목 · 첫인사 첫 줄 · 메모지 제목 · 장소 마무리 · 방문 요약
```

아래는 **손글씨 금지 구역**입니다. 자동 검사로 매번 확인합니다.

```
주소 · 시설명 · 판정 문구 · 조건 근거 · 오류 문구 · 지도/복사 버튼 · 입력창 · 출처 · 모든 숫자
```

손글씨는 같은 px에서 작아 보이므로 그 자리는 19px 이상으로 잡았습니다. CDN을 못 받아오면 Pretendard로 떨어지고, 그 상태도 자동 검사합니다.

**온이 얼굴**

인라인 SVG로 그린 얼굴을 **첫인사와 판정 줄 두 자리에만** 둡니다. 말풍선마다 붙이면 다시 채팅앱이 됩니다.

| `comfort.level` | 표정 |
| --- | --- |
| COMFORTABLE | 웃는 입 |
| CHECK_NEEDED | 한쪽 눈썹 + 갸웃한 입 |
| BURDEN_POSSIBLE | 내려간 입 |
| INSUFFICIENT_DATA | 일자 입 + 물음표 |

표정은 색에 기대지 않는 두 번째 신호입니다. 판정 문구는 지금처럼 항상 함께 나가고, SVG는 `aria-hidden`입니다.

**형광펜과 메모지**

- 형광펜은 한 화면에 3개까지. 브랜드, 표제의 핵심 낱말, 판정 문구의 핵심 낱말.
  낱말 경계를 조사 끝에 맞춰 `확인할 정보가` 처럼 끊습니다. `정보` 에서 끊으면 조사가 떨어져 보입니다.
- `아직 확인 안 된 정보`와 `오늘 살펴본 곳`은 마스킹테이프를 붙인 메모지입니다. 원래부터 메모 성격인 자리입니다.

**장식**

별·하트·점선 화살표·물결·반짝임을 표제부와 첫인사 주변에만 둡니다. 답변 카드 안에는 하나도 없습니다.
좁은 화면(700px 미만)과 `prefers-contrast: more`에서는 전부 감춥니다.

### 3. 지난번을 기억합니다 (v3)

`localStorage`에 유형·조건·선호 지도만 남깁니다. 질문 내용은 저장하지 않습니다.

- 다시 오면 `지난번처럼 부모님과 함께 가시나요?` + `[ 네, 그대로 ]` `[ 아니요, 바꿀게요 ]`
- `네, 그대로`를 누르면 조건까지 복원하고 바로 질문을 받습니다.
- 30일이 지난 기록은 버립니다.
- 저장이 막힌 환경(시크릿 모드 등)에서는 `try/catch`로 넘기고 첫 방문처럼 동작합니다.

### 4. 모바일 (v3)

- `100dvh`, `viewport-fit=cover`, `env(safe-area-inset-bottom)`
- 키보드가 올라오면 `visualViewport`로 겹치는 높이를 재서 입력창을 그만큼 띄웁니다
- 입력창 17px (iOS 자동 확대 방지선 16px 이상)
- 320 / 360 / 390 / 430 / 768px 검증

### 5. 접근성

- 본문 15px 이상(기본 17px), 터치 영역 48px 이상, 입력 16px 이상
- **모든 표시 글자의 대비를 자동 계산해 검사합니다.** 이번 실행에서 가장 낮은 값이 6.5:1 (기준 4.5:1)
- `prefers-contrast: more`에서 테두리를 3.5px로 올리고 장식·형광펜·기울기를 제거
- `prefers-reduced-motion`에서 등장·흔들림·누름 변형까지 전부 정지

## v2에서 이어지는 것 (그대로 유지)

- 유형 미선택 시 차단 대신 되묻기 → 칩 클릭 시 직전 질문 자동 재전송
- 시작 화면 조건 체크박스 0개, 유형별 기본 `needs` 자동 전송, 조건 서랍(6개 + 더보기)
- 답변 3층 구조. 3층 요약 문구는 `이동·편의 정보, 출처 보기`
- 시설 2개 먼저 + `+ 시설 N곳 더 보기`
- 끼어들기 확인 → 기존 질문 상기, 장소 마무리 줄과 방문 요약
- 오류는 `이유 + 차선 + 버튼 하나`
- 해요체 통일, 금지 표현 0건
- 페이지 스크롤 하나(대화 영역 내부 스크롤 없음)

| 유형 | 기본 `needs` |
| --- | --- |
| senior | `stairs_difficult`, `need_rest_area`, `restroom_important` |
| baby | `stroller`, `need_nursing_room`, `need_diaper_station` |
| both | `stairs_difficult`, `need_rest_area`, `restroom_important`, `stroller`, `need_nursing_room` |

## 실제 수정한 파일

| 파일 | 변경 |
| --- | --- |
| `clients/index.html` | 손그림 장식 SVG, 온이 얼굴, Gaegu 폰트 링크, 형광펜 마크업 |
| `clients/style.css` | 전면 재작성. 손그림 모서리·파스텔 채움·형광펜·마스킹테이프 메모지 |
| `clients/script.js` | 온이 표정 4종, 형광펜 낱말 분리, 손그림 체크박스, 메모지 클래스 (기능 로직은 v3 그대로) |
| `clients/mock-data.mjs` | v2에서 추가한 `many` 케이스 유지 |
| `clients/tests/browser-qa.cjs` | v5 DOM, 손글씨 금지 구역·표정 4종·회전 각도·웹폰트 차단 검사 추가 |
| `clients/tests/QA.md`, `clients/README.md` | v5 기록 |
| `clients/tests/contract-check.mjs` | 신규. 개발자 2 서버를 계약 기준으로 검사하는 스크립트 |

`servers/*`, `.venv`, DB, `index_v0.html`, `sample_data/`는 수정하지 않았습니다.

## 실행 방법

프로젝트 루트 `C:\chatbot-project_lab`에서:

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory clients
```

기본 화면: <http://127.0.0.1:5500/index.html>

기본값은 **실제 API 모드**입니다. `index.html`의 `chat-api-base` meta 값이 `http://127.0.0.1:8000`입니다.

### Mock 실행

예: <http://127.0.0.1:5500/index.html?mock=baby>

| query 값 | 확인 시나리오 |
| --- | --- |
| `senior` | 부모님, CHECK_NEEDED, 시설 1개 |
| `baby` | 아이, COMFORTABLE, 시설 3개 (2개 + 더보기) |
| `both` | 모두, UNKNOWN 4개 |
| `many` | 시설 4개, 픽토그램 4종 |
| `burden` | BURDEN_POSSIBLE, 시설 0개 |
| `insufficient` | INSUFFICIENT_DATA, 빈 섹션 생략 |
| `no_address` / `no_map` | 주소 없음 / 지도 링크·복사 버튼 생략 |
| `not_found` / `ambiguous` / `failure` | 업무 오류 |
| `network` / `http_error` | 연결 실패 / HTTP 503 |
| `slow` / `timeout` | 12초 지연 / 45초 후 중단 |
| `auto` | 질문 속 장소명과 이전 ID에 따른 fixture 전환 |

Mock은 임의의 UI 예시이며 실제 관광 정보가 아닙니다. 일반 실행에서는 fixture 모듈을 불러오지 않습니다.

## Backend Shared API Contract (Backend v11 기준)

`POST /chat`, `Content-Type: application/json`. 추가 인증키나 `use_rag`를 보내지 않습니다.

```json
{
  "message": "엄마랑 경복궁 가려고 하는데 계단이 힘들어.",
  "traveler_type": "senior",
  "needs": ["stairs_difficult", "need_rest_area", "restroom_important"],
  "current_place_id": null
}
```

- `traveler_type`: `senior | baby | both`. 확정 전에는 전송하지 않고 화면에서 되묻습니다.
- `needs`: `walking_difficult`, `stairs_difficult`, `need_rest_area`, `wheelchair_needed`, `restroom_important`, `stroller`, `need_nursing_room`, `need_diaper_station`, `need_elevator`만 사용합니다.
- `current_place_id`: 최초/마무리 시 null. 성공 응답의 `place.content_id`를 저장합니다. 새 관광지명이 포함된 질문도 기존 ID와 함께 보낼 수 있으며, **현재 message의 명확한 장소명을 기존 ID보다 우선**해 주세요.

성공 응답 예시:

```json
{
  "success": true,
  "answer": "계단 구간이 있어서 우회로를 미리 봐두시면 좋아요.",
  "place": {"content_id": "12345", "name": "경복궁", "address": "서울특별시 ...", "region": "서울특별시"},
  "comfort": {
    "level": "CHECK_NEEDED",
    "label": "방문 전 확인할 정보가 있어요",
    "items": [
      {"need": "restroom_important", "status": "SATISFIED", "reason": "화장실 정보가 확인돼요."},
      {"need": "walking_difficult", "status": "UNKNOWN", "reason": "걷기 부담을 판단할 공식 근거가 부족해요."}
    ]
  },
  "sections": [{"key": "mobility", "title": "이동", "items": [{"label": "엘리베이터", "value": "있음"}]}],
  "facilities": [{"type": "restroom", "name": "화장실", "parent_place": "경복궁", "address": "서울특별시 ...", "location_detail": "입구 안내소 옆", "map_search_text": "경복궁 서울특별시 ..."}],
  "unknown_fields": ["걷기 부담"],
  "sources": [{"organization": "한국관광공사", "title": "무장애 여행 정보", "updated_at": null}],
  "suggested_questions": ["화장실 위치 알려줘", "많이 걸어야 하는지 알려줘"]
}
```

| `comfort.level` | 사용자 표시 |
| --- | --- |
| COMFORTABLE | ✓ 편안하게 이용할 가능성이 높아요 |
| CHECK_NEEDED | ⓘ 방문 전 확인할 정보가 있어요 |
| BURDEN_POSSIBLE | ! 현재 조건에서는 부담이 있을 수 있어요 |
| INSUFFICIENT_DATA | ? 판단할 정보가 부족해요 |

`comfort.label` 문장으로 색이나 등급을 바꾸지 않습니다. 네 가지 enum의 고정 문구만 표시하며, 알 수 없는 enum은 중립적인 `판단 상태를 확인하지 못했어요`.

`comfort.items[].status`는 `SATISFIED`, `CONFLICT`, `UNKNOWN` 3종 기준이며 과거 `UNSATISFIED`, `NOT_SATISFIED`, `CAUTION`도 방어적으로 지원합니다.

- **표시 순서가 곧 우선순위입니다.** 2층에 앞 3개만 보이므로 중요한 항목을 앞에 담아 주세요.
- `answer`는 두 문장 이내로 짧게 보내 주세요.
- `suggested_questions`는 3개까지 화면에 붙습니다.
- 시설 주소가 없어도 `parent_place`와 `location_detail`은 각각 표시합니다.

실패 응답:

```json
{"success": false, "answer": "...", "error": {"code": "PLACE_NOT_FOUND", "message": "검색 결과 없음"}}
```

권장 code는 `PLACE_NOT_FOUND`, `AMBIGUOUS_PLACE`이며 alias로 `NOT_FOUND`, `PLACE_AMBIGUOUS`, `MULTIPLE_PLACES`를 지원합니다.

## 통합 검증 결과와 한계

현재 이 폴더는 **Front v5 + Backend v11 통합 계약**에 맞춰 갱신되어 있습니다.

- Backend pytest: `51 passed`
- Front → Backend `contract-check.mjs`: **필수 위반 0건 · 권고 0건**
- Front JavaScript 정적 문법 검사: 통과
- `AMBIGUOUS_PLACE.candidates` 선택 시 `content_id → current_place_id` 전달 로직 반영
- 기존 Front v5 Browser QA 스크립트도 신규 계약에 맞춰 갱신

이 실행 환경에서는 Chromium의 localhost 접속이 관리자 정책으로 차단되어 Browser QA 전체 재실행은 하지 못했습니다. Windows 개발환경에서는 아래 명령으로 재검증하세요.

```powershell
$env:PLAYWRIGHT_MODULE='C:/Users/SSAFY/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:CHROME_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe'
node .\clients\tests\browser-qa.cjs
```

## 통합 완료 사항

1. `long_walk_difficult` → `walking_difficult`로 계약 통일
2. `driving`은 Comfort Need에서 제거. 주차는 자유질문 및 `sections`/`facilities`로 표시
3. `comfort.items[].status` 표준을 `SATISFIED / CONFLICT / UNKNOWN`으로 동기화
4. `AMBIGUOUS_PLACE`에서 Backend의 `candidates[]`를 직접 버튼으로 표시
5. 후보 선택 시 `content_id`를 `current_place_id`로 전달해 이름 재검색을 피함
6. 과거 localStorage의 `long_walk_difficult` 자동 마이그레이션, `driving` 제거
7. Backend 추천 질문 최대 3개로 Front 표시 수와 동기화
8. Backend 답변 프롬프트를 상단 요약용 1~2문장 중심으로 조정

## Backend 통합 참고

현재 `servers/`는 이미 여행 계약이 구현된 Backend v11 기반입니다. 과거 `{message, use_rag}` 서버로 교체하거나 Front에서 받은 구형 `servers.zip`을 덮어쓰지 마세요.

- 요청: `{ message, traveler_type, needs, current_place_id }`
- 장소 식별: `PLACE_NOT_FOUND`, `AMBIGUOUS_PLACE` + `candidates[]`
- Follow-up: 성공 응답의 `place.content_id`를 `current_place_id`로 재사용
- 지도: `facilities[].map_search_text`를 Front가 지도 링크로 변환
- 실제 TourAPI 키는 `servers/.env`에만 저장하고 커밋하지 않음

### 팀에 확인받을 한 줄

원래 명세의 "지도 API를 연결하지 않는다"를 지키면서 링크만 추가했습니다.

> 지도 SDK·인증키·좌표는 계속 쓰지 않고, 지도 앱으로 넘어가는 하이퍼링크만 추가했습니다. 복사 버튼은 그대로 둡니다.


## integrated v2 UI 원칙

- 전체 화면은 `Gaegu` 손글씨 계열 폰트를 사용합니다. 제목/본문/버튼/주소/입력창에 별도 본문 폰트를 섞지 않습니다.
- 가족 유형을 고르면 전국 대표 장소 6개를 한 번만 제시하며, 장소 칩은 즉시 조회합니다.
- 추천 질문은 결과 카드 안에만 표시하고 클릭 시 기존 대화를 유지한 채 새 사용자 메시지로 이어집니다.
- Backend `answer`의 긴 보고서 문장을 메인 카드에 그대로 노출하지 않습니다. `comfort`/`facilities` 기반 1~2문장 요약을 Front가 구성합니다.
- `Rule Engine`, `SATISFIED`, `UNKNOWN` 같은 내부 용어는 사용자 화면 기본 영역에 직접 노출하지 않습니다.
- 기본 정보 구조는 판정 배너 → 짧은 요약 → 우리 가족 조건 → 가까운 시설 → 접힌 상세 → 이어서 물어보기 순서입니다.
- 결과 하단에 `다른 곳 보기`, `조건 바꾸기`를 유지합니다.