# 온가 (ON-GA) — 가족 여행 편의정보 챗봇

부모님, 영유아, 또는 온 가족이 함께 여행할 때 필요한 **이동·편의시설 정보를 공식 관광데이터 기반으로 확인하는 서비스**입니다.

단순히 관광지를 추천하기보다,

> **“우리 가족이 이곳을 이용하기에 어떤 점을 미리 확인해야 하는가?”**

를 빠르게 파악할 수 있도록 설계했습니다.

![ON-GA demo](test.gif)

> 이 저장소는 2인 팀 프로젝트의 Frontend와 Backend를 함께 포함합니다.  
> 문하늘의 개인 담당은 **Frontend / UX / 통합 QA**이며, Backend / RAG / TourAPI / Rule Engine 구현은 팀원이 담당했습니다.

---

## 1. Problem

가족 여행에서는 같은 장소라도 동행자에 따라 확인해야 할 정보가 달라집니다.

예를 들어 부모님과 갈 때는 계단·걷는 거리·휴식공간·화장실이 중요하고,  
영유아와 갈 때는 유모차·수유실·기저귀 교환시설·엘리베이터가 중요할 수 있습니다.

하지만 공식 관광정보를 직접 찾으면 다음 문제가 있습니다.

- 필요한 편의정보가 여러 항목에 흩어져 있음
- 장소명만으로 검색하면 동명이인 관광지가 섞일 수 있음
- 공식 자료에 정보가 없을 때 실제로 “없음”인지 “확인되지 않음”인지 구분하기 어려움
- 긴 원문을 읽어도 우리 가족 조건에 맞는 정보가 바로 보이지 않음

ON-GA는 이 정보를 **가족 조건 → 편안함 판단 → 시설 → 상세 근거** 순서로 재구성합니다.

---

## 2. Core Product Principles

### 1) ‘없음’과 ‘확인할 수 없음’을 구분

이 프로젝트에서 가장 중요하게 둔 원칙 중 하나입니다.

- `false` → 공식 자료에서 **명시적으로 없음**
- `null` → 공식 자료만으로 **확인할 수 없음**

예를 들어,

```text
유모차 대여 가능
≠
관광지 전체를 유모차로 이동하기 편함
```

처럼 서로 다른 사실을 임의로 합치지 않습니다.

### 2) 내부 시스템 용어를 사용자에게 그대로 노출하지 않음

Backend 내부에서는 다음 상태를 사용합니다.

```text
SATISFIED
CONFLICT
UNKNOWN
```

최종 판단 레벨:

```text
COMFORTABLE
CHECK_NEEDED
BURDEN_POSSIBLE
INSUFFICIENT_DATA
```

하지만 사용자 화면에는 enum이나 Rule Engine 용어를 그대로 보여주지 않고,

- 공식 정보에서 확인됨
- 방문 전 추가 확인 필요
- 현재 조건에서는 부담 가능
- 판단할 정보 부족

처럼 이해 가능한 문장으로 변환합니다.

### 3) 공식 데이터보다 더 많이 추정하지 않음

시설 존재 여부, 이동 편의성, 접근성 등을 공식 자료가 뒷받침하지 않으면 임의로 확정하지 않습니다.

---

## 3. Main User Flow

```text
동행 유형 선택
→ 필요한 조건 선택
→ 관광지 질문
→ 장소 식별
→ 공식 관광데이터 조회
→ 가족 조건과 데이터 비교
→ 편안함 판단
→ 시설 / 미확인 정보 / 출처 표시
→ 후속 질문
```

### Follow-up

첫 질문에서 확정된 장소의 `content_id`를 Frontend가 보관합니다.

```text
국립중앙박물관 알려줘
        ↓
content_id 저장
        ↓
수유실 위치 알려줘
        ↓
같은 장소 기준으로 후속 질문
```

### Ambiguous place

동일하거나 비슷한 장소가 여러 개 나오면 Backend의 `candidates[]`를 Frontend에서 직접 선택지로 보여줍니다.

선택 후에는 장소명을 다시 검색하지 않고 해당 `content_id`를 `current_place_id`로 전달합니다.

---

## 4. System Architecture

```text
[ User ]
   │
   ▼
[ Frontend ]
HTML / CSS / Vanilla JavaScript
   │
   │ traveler_type / needs / current_place_id
   ▼
[ FastAPI Backend ]
   │
   ├─ 장소 식별
   ├─ TourAPI 공식 데이터 조회
   ├─ 데이터 정규화
   ├─ Comfort Rule Engine
   ├─ 시설 구조화
   ├─ Chroma RAG / LLM 보조
   └─ 사용자용 응답 생성
   │
   ▼
[ 한국관광공사 무장애 여행 정보 ]
```

> Backend와 RAG 구현은 팀원 담당입니다.  
> 문하늘은 Frontend가 이 구조화된 응답을 사용자가 이해할 수 있는 형태로 표현하도록 UI/UX와 API contract를 설계·검증했습니다.

---

## 5. My Contribution

### 담당 범위

**Frontend / UX / 통합 QA**

직접 수행한 범위:

- 가족 유형 및 필요 조건 선택 UX
- 채팅형 질문/응답 UI
- 가족 조건 → 판단 → 시설 → 상세정보의 정보계층 설계
- `UNKNOWN`을 “시설 없음”으로 오해하지 않게 하는 표현
- 동명이인 장소의 `candidates[]` 선택 UI
- `current_place_id` 기반 후속 질문 흐름
- 시설 카드와 지도 검색 링크
- 주소 복사 fallback
- 모바일 / 키보드 / 고대비 / reduced-motion 대응
- Frontend–Backend Shared API Contract 검사
- Mock fixture와 Persona QA 시나리오
- Backend 통합 후 계약 불일치 수정 및 검증

구현 과정에서는 AI 코딩 도구를 활용했습니다.  
포트폴리오에서는 이를 **UX/정보구조 설계 → AI-assisted 구현 → 통합 검증**으로 표현합니다.

### 담당하지 않은 범위

- FastAPI Backend 구현
- TourAPI 연동 로직
- Comfort Rule Engine 구현
- LangGraph / LangChain / ChromaDB / RAG 구현
- RAGAS 평가 로직

자세한 개인 기여 범위:
- [Contribution](./docs/CONTRIBUTION.md)

---

## 6. Frontend UX Decisions

### 짧은 요약 우선

긴 Backend 원문을 그대로 메인 화면에 노출하지 않고,  
구조화된 `comfort`와 `facilities`를 기반으로 핵심 1~2문장을 먼저 보여줍니다.

### 정보 계층

```text
판단
→ 짧은 요약
→ 우리 가족 조건
→ 가까운 시설
→ 접힌 상세 정보
→ 출처
→ 이어서 물어보기
```

### 시설 지도 연결

지도 SDK나 인증키를 Frontend에 넣지 않고,  
Backend가 제공한 `map_search_text`를 사용해 카카오맵 / 네이버지도 / 구글지도 검색 링크를 생성합니다.

### 접근성 / 반응형

현재 Frontend에는 다음을 고려한 구현이 있습니다.

- skip link
- ARIA live region
- 48px 이상 터치 영역
- focus-visible
- `prefers-contrast: more`
- `prefers-reduced-motion`
- 320 / 360 / 390 / 430 / 768px 대응
- iOS 키보드 확대 방지를 위한 입력 크기
- visualViewport 기반 모바일 키보드 겹침 대응

---

## 7. Validation

최종 통합 기준으로 확인된 결과:

- Backend `pytest`: **51 passed**
- Front JavaScript syntax checks: PASS
- Shared API Contract (Mock TourAPI): **필수 위반 0건 · 권고 0건**
- `AMBIGUOUS_PLACE.candidates` → `content_id` → `current_place_id` 연결 확인

관련 문서:

- [V3_QA_REPORT.md](./V3_QA_REPORT.md)
- [INTEGRATION_REPORT.md](./INTEGRATION_REPORT.md)
- [clients/tests/QA.md](./clients/tests/QA.md)

### 검증 한계

통합 과정의 한 실행 환경에서는 Chromium localhost 접근이 정책상 차단되어 **Playwright 전체 Browser QA를 재실행하지 못했습니다.**

따라서 Backend 51개 테스트와 Shared Contract 0건 위반을  
“전체 브라우저 E2E 51개 통과”처럼 표현하지 않습니다.

---

## 8. Tech Stack

### My Frontend Scope

- HTML5
- CSS3
- Vanilla JavaScript
- LocalStorage
- DOM / Web API
- Responsive UI
- Accessibility-oriented UI
- Contract QA / Mock fixtures

### Team Backend Stack

- Python
- FastAPI
- Pydantic
- HTTPX
- LangGraph
- LangChain
- ChromaDB
- OpenAI-compatible LLM / Embedding API
- RAGAS
- Pytest

### External Data

- 한국관광공사 무장애 여행 정보
- `KorWithService2`
- Data ID `15101897`

---

## 9. Project Structure

```text
clients/                  # 문하늘 담당 Frontend
├─ index.html
├─ style.css
├─ script.js
├─ mock-data.mjs
└─ tests/

servers/                  # 팀원 담당 Backend
├─ main.py
├─ schemas.py
├─ comfort.py
├─ travel_data.py
├─ eval_ragas.py
└─ tests/

docs/                     # 통합 / UX 문서
README.md
INTEGRATION_REPORT.md
V3_QA_REPORT.md
```

---

## 10. Run

### Backend

```bash
cd servers
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
python -m http.server 5500 --bind 127.0.0.1 --directory clients
```

브라우저:

```text
http://127.0.0.1:5500/
```

환경변수와 실제 TourAPI 설정은 기존 `servers/.env.example`을 참고합니다.

---

## 11. Current Boundaries

현재 포트폴리오에서 다음을 개인 성과로 주장하지 않습니다.

- Backend / RAG 직접 개발
- TourAPI Backend 구현
- RAGAS 성능 개선
- 외부 사용자 대상 정식 usability test
- 실제 운영 사용자 수
- 사용시간 단축 / 만족도 등 사용자 성과 수치

또한 Mock fixture의 관광정보를 실제 공식 데이터 성과처럼 표현하지 않습니다.

자세한 한계:
- [Limitations](./docs/LIMITATIONS.md)

---

## 12. Documents

- [Contribution](./docs/CONTRIBUTION.md)
- [Limitations](./docs/LIMITATIONS.md)
- [Integration Report](./INTEGRATION_REPORT.md)
- [QA Report](./V3_QA_REPORT.md)
- [Frontend README](./clients/README.md)
