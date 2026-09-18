# ON-GA Limitations & Evidence Boundaries

이 문서는 ON-GA를 포트폴리오에서 과장 없이 설명하기 위해 현재 검증 범위와 아직 주장하지 않는 범위를 구분합니다.

---

## 1. Personal Ownership

문하늘의 개인 담당은 Frontend / UX / 통합 QA입니다.

다음은 개인 개발 성과로 표현하지 않습니다.

- FastAPI Backend
- TourAPI 서버 연동
- 데이터 정규화
- Comfort Rule Engine
- LangGraph / LangChain
- ChromaDB
- RAG
- RAGAS

---

## 2. AI-assisted Coding

Frontend 구현에는 AI 코딩 도구가 활용되었습니다.

따라서:

- “Frontend 전체를 수작업으로 직접 코딩했다”
- 코드 라인 수를 개인 코딩 생산성으로 제시

하는 표현은 사용하지 않습니다.

대신 다음 범위를 설명합니다.

- UX / 정보 구조 기준 정의
- 화면 상태와 사용자 문구 설계
- AI-assisted 구현
- 실제 화면 검증
- API Contract 검증
- Backend 통합 과정의 불일치 수정

---

## 3. QA Numbers

최신 통합 보고 기준:

- Backend pytest: **51 passed**
- Shared API Contract: **필수 위반 0건 · 권고 0건**
- Front JavaScript syntax check: PASS

주의:

Backend 51개 테스트는 **팀 Backend 검증 결과**입니다.

문하늘 개인 Frontend에서 “51개 테스트를 모두 통과시켰다”고 표현하지 않습니다.

또한 한 통합 환경에서는 Chromium localhost 접근 제한으로 Playwright 전체 Browser QA를 재실행하지 못했습니다.

따라서 다음처럼 표현하지 않습니다.

- “전체 E2E 51개 PASS”
- “모든 브라우저 시나리오 검증 완료”

---

## 4. User Validation

현재 외부 실제 사용자 대상 정식 usability test 증거는 없습니다.

따라서 다음 수치를 사용하지 않습니다.

- 부모님 세대 만족도
- 정보 탐색시간 감소
- 여행 계획시간 절감
- 사용 성공률
- 재사용 의향

Persona / Mock QA를 실제 사용자 테스트처럼 표현하지 않습니다.

---

## 5. Official Data Boundary

ON-GA는 한국관광공사 무장애 여행 정보를 사용하는 구조를 갖추고 있지만,

- Mock fixture는 실제 관광정보가 아님
- 공식 자료에 없는 내용을 임의로 확정하지 않음
- 시설 대여 가능 여부와 전체 이동 편의성을 동일하게 보지 않음

을 원칙으로 합니다.

---

## 6. UI Version History

Repository에는 여러 UI iteration 문서가 함께 남아 있습니다.

- v2 / v3 / v5 기획·인수인계 문서
- 현재 실제 코드의 build marker: `integrated-v3`
- 과거 문서에는 현재 구현과 다른 디자인 원칙이 남아 있을 수 있음

따라서 현재 상태 설명은 **최신 실제 코드와 V3_QA_REPORT / 통합 보고서**를 우선합니다.

예를 들어 과거 v5 프롬프트의 “손글씨는 액센트만” 기준과 달리 현재 실제 CSS는 화면 전체에 Gaegu 계열을 적용합니다.

---

## 7. Service Limitations

현재 포트폴리오에서 다음을 주장하지 않습니다.

- 실제 관광지 현장 상황을 실시간으로 보장
- 모든 시설 정보의 최신성 보장
- 공식 데이터에 없는 접근성 상태를 자동 판정
- 의료적 이동 가능 여부 판단
- 실제 상용 서비스 운영 사용자 수

사용자에게도 방문 전 공식기관 / 현장 확인이 필요하다는 전제를 유지합니다.

---

## 8. Safe Portfolio Description

> **공식 관광정보를 가족 여행 조건에 맞게 구조화해 보여주는 서비스에서 Frontend/UX를 담당하고, UNKNOWN과 부재를 구분하는 정보 표현 원칙과 Frontend–Backend contract를 설계·검증했다. Backend/RAG는 팀원이 담당했으며, 통합 후 Shared API Contract 필수·권고 위반 0건을 확인했다.**

이보다 강한 Backend 또는 사용자 성과 주장은 추가 증거가 필요합니다.
