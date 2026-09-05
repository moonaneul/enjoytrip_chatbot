# 온가 통합 v3 UX 정리

## 이번 버전의 강제 규칙

- 성공 화면에서 Backend `answer` 원문을 직접 렌더링하지 않는다.
- 상단 요약은 `comfort`, `facilities` 등 구조화 필드에서 최대 2문장으로 만든다.
- `Rule Engine`, `SATISFIED`, `CONFLICT`, `UNKNOWN`, `CHECK_NEEDED`, `need_*` 등 내부 표현은 사용자 화면에 노출하지 않는다.
- Backend `answer`도 160자 이하/최대 2문장을 hard guard로 보장한다.
- 가족 조건 카드의 이유는 짧은 사용자 문구로 통일한다.
- 상세 `sections`, `sources`, 나머지 조건은 기본 접힘 상태다.
- 추천 질문은 이전 대화를 교체하지 않고 새 사용자 말풍선과 새 결과 카드로 누적한다.
- 장소 추천 6개와 `다른 곳 보기`, `조건 바꾸기`를 유지한다.
- 전체 타이포그래피는 Gaegu를 1순위로 강제한다.
- `style.css?v=integrated-v3`, `script.js?v=integrated-v3`로 브라우저 캐시 혼동을 막는다.
- Console에 `[ON-GA] integrated-v3`가 표시된다.
