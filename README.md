# 온가 (ON-GA) — 가족과 함께하는 편안한 여행

부모님, 영유아, 또는 온 가족이 함께 여행할 때 필요한 **이동·편의시설 정보를 공식 관광데이터 기반으로 확인하는 여행 챗봇**입니다.

단순 관광지 추천보다

> “우리 가족이 이곳을 이용하기에 어떤 점을 확인해야 할까?”

에 초점을 맞춥니다.

![ON-GA demo](test.gif)

---

## 주요 기능

### 가족 유형과 조건 선택

사용자는 동행 유형과 필요한 조건을 선택할 수 있습니다.

- 부모님과 함께
- 아이와 함께
- 온 가족 함께

주요 조건:
- 계단 이용이 어려움
- 오래 걷기 어려움
- 수유실 필요
- 기저귀 교환시설 필요
- 엘리베이터 필요
- 휠체어 필요
- 화장실 중요
- 휴식공간 필요
- 유모차 이용

### 관광지 검색

한국관광공사 무장애 여행 정보를 기반으로 관광지를 찾습니다.

- 지역이 포함된 장소 검색
- 동명이인 장소 후보 제시
- 존재하지 않는 장소 처리

### 가족 편안함 정보

공식 데이터와 사용자가 선택한 조건을 비교해 다음 상태를 내부적으로 사용합니다.

```text
SATISFIED
CONFLICT
UNKNOWN
```

화면에서는 내부 enum 대신 자연어로 보여줍니다.

- 공식 정보에서 확인됐어요
- 방문 전에 추가 확인이 필요해요
- 현재 조건에서는 부담이 있을 수 있어요
- 판단할 정보가 부족해요

### 시설 카드

관광지의 편의시설을 카드 형태로 제공합니다.

- 화장실
- 장애인 화장실
- 수유실
- 기저귀 교환시설
- 주차장
- 휠체어 대여
- 유모차 대여
- 휴식공간

시설별로 카카오맵 / 네이버지도 / 구글지도 검색 링크를 제공합니다.

### 후속 질문

첫 질문에서 확인된 장소의 `content_id`를 Frontend가 기억해 후속 질문에 재사용합니다.

```text
국립중앙박물관 알려줘
        ↓
content_id 저장
        ↓
수유실 위치 알려줘
        ↓
같은 장소 기준으로 답변
```

### 모호한 장소 선택

`AMBIGUOUS_PLACE` 응답에 포함된 후보를 화면에서 직접 선택할 수 있습니다.

---

## 데이터 표현 원칙

ON-GA는 공식 자료보다 더 많이 추정하지 않는 것을 기본 원칙으로 둡니다.

### false
공식 자료에서 **명시적으로 없음**이 확인된 경우

### null
공식 자료만으로 **확인할 수 없음**

예:

```text
유모차 대여 가능
≠
관광지 전체를 유모차로 이동하기 편함
```

서로 다른 사실은 임의로 합치지 않습니다.

---

## 시스템 구조

```text
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

---

## UI / UX

현재 통합 버전은 `integrated-v3`입니다.

주요 원칙:

- 긴 보고서형 답변 대신 핵심 1~2문장 요약
- 내부 Rule Engine 용어를 기본 화면에 노출하지 않음
- 가족 조건 → 시설 → 상세 정보 순으로 정보 계층화
- 상세 정보와 출처는 기본적으로 접어서 표시
- 추천 질문은 기존 대화를 유지한 채 새 턴으로 추가
- `다른 곳 보기`, `조건 바꾸기` 제공
- 모바일 화면 대응
- 키보드 / focus / 고대비 / reduced-motion 고려

---

## 기술 스택

### Frontend
- HTML5
- CSS3
- Vanilla JavaScript
- LocalStorage

### Backend
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

## 검증 상태

최종 통합 기준:

- Backend `pytest`: **51 passed**
- Front JavaScript syntax checks: PASS
- Shared API Contract (Mock TourAPI): **필수 위반 0건 · 권고 0건**
- `AMBIGUOUS_PLACE.candidates` → `content_id` → `current_place_id` 연결 확인

한 통합 환경에서는 Chromium localhost 접근 제한으로 Playwright 전체 Browser QA를 재실행하지 못했습니다.

관련 문서:
- [V3_QA_REPORT.md](./V3_QA_REPORT.md)
- [INTEGRATION_REPORT.md](./INTEGRATION_REPORT.md)

---

## 팀 역할

2인 팀 프로젝트입니다.

- 문하늘: Frontend / UX / 통합 QA
- 팀원: Backend / Data / RAG

자세한 역할 범위는 [docs/CONTRIBUTION.md](./docs/CONTRIBUTION.md)에 정리되어 있습니다.

---

## 실행

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

---

## 문서

- [Integration Report](./INTEGRATION_REPORT.md)
- [QA Report](./V3_QA_REPORT.md)
- [Frontend README](./clients/README.md)
- [Contribution](./docs/CONTRIBUTION.md)
