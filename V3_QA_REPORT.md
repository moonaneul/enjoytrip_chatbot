# family_travel_integrated_v3 QA

## 변경 핵심
- 성공 화면에서 `data.answer` 원문을 직접 렌더링하지 않음
- 상단 요약은 구조화 `comfort/facilities`에서 최대 2문장으로 생성
- Backend `answer`도 구조화 결과에서 결정적으로 생성하여 160자 이하 유지
- `Rule Engine`, `SATISFIED`, `CONFLICT`, `UNKNOWN`, `CHECK_NEEDED`, `need_*` 등 내부 문자열 사용자 화면 비노출
- 가족 조건 카드의 상세 reason을 짧은 사용자 문구로 치환
- 상세 sections/sources는 기본 접힘
- Gaegu 폰트를 body/button/input/textarea/summary/details/link까지 강제 적용
- `style.css?v=integrated-v3`, `script.js?v=integrated-v3` cache bust 적용
- Console build marker: `[ON-GA] integrated-v3`
- 과거 `clients/index_v0.html` 제거

## 검증
- `python -m pytest -q`: **51 passed**
- `node --check clients/script.js`: PASS
- `node --check clients/mock-data.mjs`: PASS
- `node --check clients/tests/browser-qa.cjs`: PASS
- `node --check clients/tests/contract-check.mjs`: PASS
- Shared API Contract (Mock TourAPI): **필수 위반 0건 · 권고 0건**

## 사용자 화면 금지 표현
다음 문자열은 기본 성공 UI에 직접 노출하지 않는다.
- Rule Engine
- Comfort 판정
- SATISFIED / CONFLICT / UNKNOWN
- CHECK_NEEDED / BURDEN_POSSIBLE / INSUFFICIENT_DATA
- need_* / stairs_difficult / walking_difficult
