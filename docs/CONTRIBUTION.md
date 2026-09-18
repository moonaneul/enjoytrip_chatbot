# ON-GA Contribution

이 문서는 ON-GA 2인 팀 프로젝트에서 **문하늘의 실제 담당 범위**와 팀 전체 기능을 구분하기 위한 기록입니다.

---

## 1. Team Structure

ON-GA는 2인 팀 프로젝트입니다.

- **개발자 1 — Frontend / UX / QA: 문하늘**
- **개발자 2 — Backend / Data / RAG: 팀원**

초기 역할 문서와 실제 Repository 구조에서도 `clients/*`와 `servers/*`가 분리되어 있습니다.

---

## 2. My Main Contribution

한 문장으로 정리하면:

> **가족 여행자가 공식 관광정보를 이해하기 쉽게 사용할 수 있도록 정보 구조와 UX를 설계하고, AI 코딩 도구를 활용해 Frontend를 구현한 뒤 Backend 계약과 실제 통합 상태를 검증했습니다.**

핵심 단계:

1. 사용자 상황과 필요한 정보 정의
2. 화면 정보 구조와 상태 표현 설계
3. AI-assisted Frontend 구현
4. Shared API Contract 정의 / 검사
5. Backend 통합 및 QA

---

## 3. Frontend / UX

직접 담당한 범위:

- 가족 유형 선택
- 유형별 기본 Needs
- 추가 조건 선택 UI
- 채팅형 질문/응답
- 장소 후보 선택
- `current_place_id` 유지
- 추천 질문 / 후속 질문
- 판단 / 조건 / 시설 / 상세 / 출처 정보계층
- 시설 카드
- 지도 검색 링크
- 주소 복사 fallback
- localStorage 기반 조건 기억
- 모바일 대응
- 키보드 / focus / ARIA / 고대비 / reduced-motion 대응

Frontend 구현에는 AI 코딩 도구를 활용했습니다.

따라서 코드량을 수작업 구현량으로 과장하지 않고,
**UX 기준을 정의하고 생성된 구현을 검증·수정한 경험**으로 설명합니다.

---

## 4. Important Product Decisions

### UNKNOWN ≠ false

공식 자료에 정보가 없다는 사실을 시설이 실제로 없다는 의미로 바꾸지 않습니다.

- `false`: 공식 자료에서 명시적으로 없음
- `null`: 공식 자료로 확인할 수 없음

이 차이를 사용자 화면에서도 구분해서 표현했습니다.

### Internal enum ≠ user language

`SATISFIED`, `CONFLICT`, `UNKNOWN`, `CHECK_NEEDED` 같은 내부 용어를 메인 UI에 그대로 노출하지 않고 사용자 문장으로 변환했습니다.

### Structured information before long answer

Backend의 긴 답변보다 구조화된 `comfort`, `facilities`, `unknown_fields`를 우선 사용해 짧게 보여주도록 했습니다.

### Place continuity

후속 질문마다 장소를 다시 검색하지 않고 성공 응답의 `content_id`를 `current_place_id`로 재사용했습니다.

### Ambiguous places

동명이인 장소가 나오면 Backend의 `candidates[]`를 버튼으로 직접 제시하고 사용자가 장소를 선택할 수 있게 했습니다.

---

## 5. Contract / Integration QA

Frontend와 Backend를 붙일 때 요청/응답 규격이 맞는지 확인하기 위해 Shared API Contract 검사기를 사용했습니다.

주요 확인 범위:

- `traveler_type`
- `needs`
- `current_place_id`
- `comfort.level`
- `comfort.items[].status`
- `facilities[]`
- `map_search_text`
- `AMBIGUOUS_PLACE.candidates[]`
- 추천 질문 개수 / 문장 길이 / 사용자 금지 표현

최종 보고 기준:

- Shared API Contract: **필수 위반 0건 · 권고 0건**
- Front JS syntax: PASS
- Backend pytest: **51 passed** — 팀 Backend 검증 결과

Backend 테스트 수를 문하늘 개인 Frontend 테스트 성과로 표현하지 않습니다.

---

## 6. Team Work vs. My Work

### My verified scope

- Frontend / UX
- 정보계층 / 사용자 문구
- Frontend contract 대응
- Mock fixture / Front QA
- 통합 contract 검사
- Backend 응답이 Front UX 요구에 맞는지 검증
- 통합 과정의 계약 불일치 정리

### Team-level / teammate scope

- FastAPI Backend
- TourAPI 연동
- 관광 데이터 정규화
- Comfort Rule Engine
- LangGraph / LangChain
- ChromaDB
- RAG
- RAGAS
- Backend test suite

---

## 7. Evidence

- [clients/README.md](../clients/README.md)
- [docs/인수인계_통합.md](./인수인계_통합.md)
- [docs/통합_인수인계.md](./통합_인수인계.md)
- [INTEGRATION_REPORT.md](../INTEGRATION_REPORT.md)
- [V3_QA_REPORT.md](../V3_QA_REPORT.md)

과거 인수인계 문서에는 통합 전 상태가 남아 있으므로, 현재 상태는 최신 통합 보고서와 코드 기준으로 판단합니다.

---

## 8. Interview-safe Description

> “ON-GA에서 저는 Frontend와 UX를 담당했습니다. 부모님이나 아이와 여행할 때 필요한 조건을 선택하고, 공식 관광정보를 가족 기준으로 이해하기 쉽게 보여주는 정보 구조를 설계했습니다. 특히 공식 자료에 정보가 없는 상태를 시설이 없다고 단정하지 않도록 UNKNOWN과 부재를 구분했고, Backend의 내부 enum과 긴 답변을 사용자 문장과 구조화 카드로 변환했습니다. Frontend 구현에는 AI 코딩 도구를 활용했고, Backend는 팀원이 담당했습니다. 통합 단계에서는 Shared API Contract를 기준으로 요청·응답을 맞추고 최종적으로 필수·권고 위반 0건을 확인했습니다.”

이 범위보다 Backend / RAG 개발 기여를 크게 표현하려면 별도 근거가 필요합니다.
