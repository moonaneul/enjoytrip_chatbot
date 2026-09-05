# 온가 integrated v2 UI/UX 개선 보고서

## 반영 기준

사용자 피드백 4가지와 추가 폰트 요구를 기준으로 수정했다.

1. 가족 유형 선택 뒤 장소 선택지가 2개뿐이고 추천 질문이 교체되어 보이는 문제
2. Backend의 긴 답변과 Rule Engine 보고서가 화면에 과도하게 노출되는 문제
3. `우리 가족 조건`, 시설 카드, 지도 버튼, 더보기 등 손그림 카드 디자인은 유지
4. `다른 곳 보기` 탐색 흐름 유지
5. 첨부 이미지의 `우리 가족 조건`과 동일한 Gaegu 계열 폰트를 전체 화면에 적용

## 구현 내용

- Global font: Gaegu
- 초기 장소 shortcut: 6개
- shortcut 클릭: 즉시 새 user turn + `/chat`
- onboarding 중복 카드 방지
- sticky quick-actions 비노출
- follow-up 질문: 결과 카드 내부에서 새 turn으로 누적
- 메인 summary: `comfort`/`facilities` 구조화 데이터 기반 최대 1~2문장
- 긴 Backend `answer` 및 `Rule Engine` 원문 기본 화면 비노출
- 결과 순서: verdict → summary → 우리 가족 조건 → 가까운 시설 → 접힌 상세 → 후속 질문/탐색
- 결과 하단: `다른 곳 보기`, `조건 바꾸기`

## 검증

- Backend pytest: 50 passed
- JS syntax: script.js / mock-data.mjs / browser-qa.cjs / contract-check.mjs 통과
- 정적 HTTP serving: index.html / style.css / script.js 정상
- 브라우저 DOM smoke check:
  - computed font-family에 Gaegu 적용
  - 장소 shortcut 6개 확인
  - sticky quick-actions 0개 확인
  - `Rule Engine` 문자열 미노출 확인
  - 구조화 summary 확인
  - follow-up 클릭 후 user turn 및 response sheet 누적 확인
  - `다른 곳 보기` 버튼 확인

현재 실행 환경은 localhost 브라우저 navigation이 관리자 정책으로 차단되어 기존 Node Playwright 전체 회귀 스크립트는 실행하지 못했다. 대신 동일 Chromium 런타임에 HTML/CSS/JS를 직접 주입한 DOM smoke check를 수행했다.
