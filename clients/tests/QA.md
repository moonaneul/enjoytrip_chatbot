# Front-End Persona QA (v5)

2026-09-04, 실제 Chrome 152. `browser-qa.cjs`로 재현합니다. 이번 실행은 **48개 전부 PASS**입니다. v5는 표현만 손그림으로 바꾼 변경이라 기능 항목은 전부 회귀 검증입니다.

## Persona 질문

| 번호 | 유형 | 입력 또는 조건 | 기대 결과 | 결과 |
| --- | --- | --- | --- | --- |
| 1 | 부모님 | 엄마가 계단을 잘 못 오르는데 경복궁 괜찮아? | senior, 계단 근거·미확인 분리 | 통과 |
| 2 | 부모님 | 아빠가 오래 못 걷는데 많이 걸어야 해? | 같은 장소 follow-up | 통과 |
| 3 | 부모님 | 중간에 쉴 곳 있어? | 휴식공간·내부 위치 | 통과 |
| 4 | 부모님 | 휠체어 빌릴 수 있어? | 미확인을 없음으로 바꾸지 않음 | 통과 |
| 5 | 부모님 | 화장실 이용하기 편해? | 시설 카드·지도 링크·주소 복사 | 통과 |
| 6 | 아이 | 유모차로 다닐 수 있어? | baby 카드 | 통과 |
| 7 | 아이 | 수유실 있어? | 수유실 카드·픽토그램 | 통과 |
| 8 | 아이 | 기저귀 갈 곳 있어? | 기저귀 교환시설 카드 | 통과 |
| 9 | 아이 | 엘리베이터 있어? | 엘리베이터 근거 | 통과 |
| 10 | 아이 | 주차 후 유모차로 이동하기 편해? | 주차 이후 경로 확인 안내 | 통과 |
| 11 | 모두 | 부모님하고 두 살 아이 모두 같이 가도 괜찮을까? | both, 부모님·아이 섹션 | 통과 |
| 12 | 모두 | 쉬는 곳이랑 수유실 둘 다 확인해줘. | 휴식시설·수유실 미확인 분리 | 통과 |
| 13 | 예외 | 정보가 없는 시설 (`?mock=insufficient`) | INSUFFICIENT_DATA, 빈 카드 없음 | 통과 |
| 14 | 예외 | 없는 관광지 (`?mock=not_found`) | 장소 재입력 유도, ID 해제 | 통과 |
| 15 | 예외 | 모호한 장소 (`?mock=ambiguous`) | Backend 후보 버튼 표시, 후보 content_id로 재요청 | 통과 |
| 16 | 예외 | 서버 연결 실패 (`?mock=network`) | 연결 안내·재시도 | 통과 |
| 17 | 예외 | map_search_text 없음 (`?mock=no_map`) | 지도 링크·복사 버튼 모두 생략 | 통과 |

Mock은 질문 의미를 분석하지 않고 fixture를 반환합니다. 답변 품질 평가가 아닙니다.

## v2 항목 (회귀 확인)

| 번호 | 확인 내용 | 결과 |
| --- | --- | --- |
| 18 | 유형 미선택으로 질문해도 차단되지 않고 되묻는다 | 통과 |
| 19 | 되묻기 칩이 직전 질문을 자동 재전송한다 | 통과 |
| 20 | 조건 미선택 시 유형별 기본 needs가 전송된다 | 통과 |
| 21 | 조건 서랍 변경이 요약 줄에 반영된다 | 통과 |
| 22 | 답변 3층 중 3층은 접혀 있다 (`이동·편의 정보, 출처 보기`) | 통과 |
| 23 | 시설 4개일 때 2개 먼저 + 더보기 | 통과 |
| 24 | 답변 대기 중 새 질문 → 확인 칩, 확인 전 요청 없음 | 통과 |
| 25 | 새 질문 처리 후 기존 질문 상기, 중단이 오류로 뜨지 않음 | 통과 |
| 26 | 장소 전환 시 마무리 줄과 방문 요약 | 통과 |
| 27~29 | 좁은 화면 가로 넘침 없음 / 중첩 스크롤 없음 | 통과 |
| 30 | prefers-reduced-motion | 통과 (아래 41번으로 자동 검사) |
| 31~34 | 본문 15px·터치 48px·키보드 도달·금지 표현 0건 | 통과 |

## v3 추가 항목

| 번호 | 확인 내용 | 결과 |
| --- | --- | --- |
| 35 | 지도 링크 href가 `encodeURIComponent(map_search_text)`와 정확히 일치 | 통과 |
| 36 | `target="_blank"`, `rel="noopener noreferrer"` | 통과 |
| 37 | `map_search_text`가 null·공백이면 링크·복사 버튼·다른 지도 모두 없음 | 통과 |
| 38 | `location_detail`이 검색어에 섞이지 않음 | 통과 |
| 39 | 지도 3종(카카오·네이버·구글) 제공, 고른 값이 저장되어 다음 카드에 반영 | 통과 |
| 40 | 시설 종류 SVG 픽토그램, 미등록 type은 기본 핀 | 통과 |
| 41 | 아이콘 옆에 시설명 텍스트가 항상 있음 | 통과 |
| 42 | 재방문 시 `지난번처럼 …` 인사, `네, 그대로`로 조건 복원 | 통과 |
| 43 | 재방문 거절 시 유형 3종 다시 표시 | 통과 |
| 44 | 30일 지난 기록 무시 | 통과 |
| 45 | localStorage가 막혀도 첫 방문처럼 동작, JS 오류 0건 | 통과 |
| 46 | 320·360·390·430·768px 가로 넘침 없음 | 통과 |
| 47 | 입력창 font-size 16px 이상 | 통과 (17px) |
| 48 | 본문·버튼·placeholder 대비 4.5:1 이상 (자동 계산) | 통과 |
| 49 | `prefers-contrast: more`에서 테두리 2px→3px, 장식 도형 숨김 | 통과 |
| 50 | `prefers-reduced-motion`에서 animation-name이 전부 none | 통과 |

## v5 추가 항목

| 번호 | 확인 내용 | 결과 |
| --- | --- | --- |
| 51 | 손글씨 폰트가 금지 구역(주소·시설명·판정·근거·오류·버튼·입력창·출처)에 적용되지 않음 | 통과, 0건 |
| 52 | 손글씨가 걸린 자리는 전부 19px 이상 | 통과 |
| 53 | 온이 표정 4종이 `comfort.level` 4종과 1:1로 바뀌고 문구가 항상 함께 있음 | 통과, 4종 모두 서로 다름 |
| 54 | 장식 SVG가 전부 `aria-hidden="true"`이고 클릭을 가로채지 않음 | 통과 |
| 55 | 회전이 걸린 요소의 각도가 전부 1도 이하 | 통과 |
| 56 | 웹폰트(Pretendard·Gaegu)를 차단해도 화면이 깨지지 않음 | 통과, 캡처 `results/nofont-home.png` |
| 57 | 좁은 화면과 `prefers-contrast: more`에서 장식이 사라짐 | 통과 |

51번과 55번은 computed style을 실제로 읽어 검사합니다.

### 대비 실측 (가장 낮은 5개)

`tests/results/contrast.json`에 전체 기록. 기준 4.5:1(큰 글자 3:1).

| 값 | 대상 |
| --- | --- |
| 6.5 | 시설·상세의 항목 이름(dt) |
| 6.5+ | 나머지 전부 |

v5는 글자색이 상태와 무관하게 잉크색(`#2E2E2E`) 하나이고 파스텔은 배경으로만 쓰므로, 대비가 v4보다 올라갔습니다.

배경색은 상속을 거슬러 올라가 실제로 칠해진 색을 찾아 계산했습니다.

### 금지 표현 재현 명령

```bash
grep -nE "에 대해|에 관하여|로부터|을 통하여|를 통하여|제공됩니다|제공되고|지원합니다|가능합니다|확인할 수 있습니다|판단됩니다|요구됩니다|되어집니다|하실 수 있으십니다|귀하|당신|사용자님|고객님|해당 시설|본 서비스" clients/index.html clients/script.js clients/style.css clients/mock-data.mjs
```

## 그 밖에 확인한 동작

- 가족 유형 3종, 조건 6 / 6 / 6(+더보기 4), 유형 전환 시 사용자가 고른 값 유지.
- 빈 문자열·공백 차단. Shift+Enter 줄바꿈, 한글 조합 중 Enter 비전송.
- 장소가 없을 때 추천 칩은 입력창에만 반영. 장소가 있으면 즉시 follow-up. Backend `suggested_questions` 우선.
- 편안함 4종과 미등록 enum 중립 처리. 색·기호·글자 3중 표기.
- 실제 Clipboard API 복사 → 실패 시 execCommand → 둘 다 실패 시 수동 선택 입력. 복사 문자열이 `map_search_text`와 정확히 일치.
- HTTP 503, `success=false`, 연결 실패, 구형 `{answer, source}` 응답, 빈 섹션, 응답 문자열의 HTML 미실행.
- 브라우저 시계를 진행하여 로딩 3단계(0·2.5·10초)와 45초 timeout 확인.
- 메인 사용자 화면에 SSAFY·RAG·업로드·초기화 없음.
- 브라우저 JavaScript 미처리 오류 0건.

## 실제 Backend 결과

이번 실행 시점에 `http://127.0.0.1:8000`이 떠 있지 않아 `net::ERR_CONNECTION_REFUSED`를 받았습니다. 화면은 `잠깐 정보를 못 가져왔어요. / 연결 상태를 확인하고 다시 눌러주세요. / [다시 시도]`를 정상 표시했습니다. 기록은 `results/backend-integration.json`.

`structuredResponseRendered: false`는 통합 성공이 아니라는 뜻입니다. Mock 통과와 fixture 통과는 실제 Backend 검증을 대체하지 않습니다.

## 개발자 2 서버 계약 검사

프런트를 켜지 않고도 서버만 검사할 수 있습니다.

```powershell
node C:\chatbot-project_lab\clients	ests\contract-check.mjs
```

`[필수]`가 0건이면 프런트와 그대로 붙습니다. 자세한 내용은 `docs/인수인계_통합.md`.

## 재실행

정적 서버를 띄운 뒤:

```powershell
$env:PLAYWRIGHT_MODULE='C:/Users/SSAFY/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:CHROME_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe'
node clients/tests/browser-qa.cjs
```

다른 환경에서는 설치된 `playwright` 모듈 경로와 Chrome 경로로 두 환경변수를 맞춥니다. Front-End 실행 자체에는 Playwright·Node가 필요하지 않습니다. `FRONTEND_URL`로 검증 주소를 바꿀 수 있습니다.

테스트는 매 페이지 로드마다 `localStorage`를 비웁니다. 재방문 시나리오는 URL에 `keep`, 저장 차단 시나리오는 `noStore`를 붙여 구분합니다. 지도 링크가 여는 새 창은 자동으로 닫습니다.

캡처: `results/desktop-home.png`, `results/desktop-both.png`, `results/mobile-both.png`, `results/nofont-home.png`(웹폰트 차단). fullPage 캡처는 sticky 입력창이 화면을 가리므로 촬영 동안만 흐름 배치로 되돌립니다. 실제 화면에서는 입력창이 아래에 고정됩니다.
