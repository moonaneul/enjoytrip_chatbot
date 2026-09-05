import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DISABLE_LLM"] = "true"
os.environ["TOUR_API_SERVICE_KEY"] = ""
os.environ["TOUR_API_USE_MOCK_WHEN_NO_KEY"] = "true"

import main


def test_chat_contract_baby_and_facility_map_search_text():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "국립중앙박물관 아이랑 가기 괜찮아?",
                "traveler_type": "baby",
                "needs": ["need_nursing_room", "need_diaper_station", "stroller"],
                "current_place_id": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["place"]["name"] == "국립중앙박물관"
        assert data["comfort"]["level"] == "CHECK_NEEDED"
        nursing = next(x for x in data["facilities"] if x["type"] == "nursing_room")
        assert nursing["map_search_text"] == (
            "국립중앙박물관 서울특별시 용산구 서빙고로 137"
        )
        assert "suggested_questions" in data


def test_current_place_id_followup():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "수유실 위치는?",
                "traveler_type": "baby",
                "needs": ["need_nursing_room"],
                "current_place_id": "1001",
            },
        )
        data = response.json()
        assert data["success"] is True
        assert data["place"]["content_id"] == "1001"


def test_ambiguous_place_returns_candidates():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "중앙공원 부모님이랑 가기 괜찮아?",
                "traveler_type": "senior",
                "needs": ["stairs_difficult"],
                "current_place_id": None,
            },
        )
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AMBIGUOUS_PLACE"
        assert len(data["candidates"]) == 2


def test_unknown_is_not_claimed_as_absent():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "경복궁 수유실 있어?",
                "traveler_type": "baby",
                "needs": ["need_nursing_room"],
                "current_place_id": None,
            },
        )
        data = response.json()
        item = next(x for x in data["comfort"]["items"] if x["need"] == "need_nursing_room")
        assert item["status"] == "UNKNOWN"
        assert data["comfort"]["level"] == "INSUFFICIENT_DATA"
        assert all(x["type"] != "nursing_room" for x in data["facilities"])


def test_nationwide_code_path_with_jeju_fixture():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "성산일출봉 부모님이랑 가기 괜찮아?",
                "traveler_type": "senior",
                "needs": ["need_elevator", "restroom_important"],
                "current_place_id": None,
            },
        )
        data = response.json()
        assert data["success"] is True
        assert data["place"]["region"].startswith("제주")


def test_place_not_found():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "존재하지않는테스트관광지 가기 괜찮아?",
                "traveler_type": "both",
                "needs": ["restroom_important"],
                "current_place_id": None,
            },
        )
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "PLACE_NOT_FOUND"


def test_invalid_request_contract():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "",
                "traveler_type": "invalid",
                "needs": [],
                "current_place_id": None,
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_REQUEST"


def test_cors_localhost_and_reset_keeps_tour_cache():
    with TestClient(main.app) as client:
        client.post(
            "/chat",
            json={
                "message": "국립중앙박물관 아이랑 가기 괜찮아?",
                "traveler_type": "baby",
                "needs": ["need_nursing_room"],
                "current_place_id": None,
            },
        )
        cache_path = main.travel_service.cache_dir / "1001.json"
        assert cache_path.exists()

        reset = client.post("/reset-db")
        assert reset.status_code == 200
        assert reset.json()["success"] is True
        assert cache_path.exists()

        cors = client.options(
            "/chat",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert cors.status_code == 200
        assert cors.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_senior_suggested_questions_do_not_prioritize_baby_facilities():
    place = {
        "accessibility": {"rest_area": True},
        "baby": {"nursing_room": True, "diaper_station": True},
        "restroom": {"available": True},
    }
    questions = main.build_suggested_questions(main.TravelerType.senior, place)
    assert "수유실 위치 알려줘" not in questions
    assert "기저귀 교환할 곳 있어?" not in questions
    assert questions[0] == "화장실 위치 알려줘"
    assert "쉴 곳 있어?" in questions


def test_prompt_contains_canonical_fact_precedence_rule():
    if main.LANGCHAIN_AVAILABLE:
        prompt = main.init_prompt_templates()
        assert prompt is not None
        text = str(prompt.messages[0].prompt.template)
    else:
        text = (Path(main.__file__).read_text(encoding="utf-8"))
    assert "[정규화된 공식 사실]" in text
    assert "최우선 근거" in text
    assert "있음'인 항목을 '확인되지 않음'" in text
    assert "이용방법·인과관계·동선을 새로 만들지 마세요" in text
    assert "관광지 전체가 전반적으로 편하다거나 이동이 쉽다고 일반화하지 마세요" in text


def test_place_term_extraction_prefers_travel_target_prefix():
    assert main.extract_search_terms("엄마랑 불국사 가려고 하는데 계단이 힘들어.")[0] == "불국사"
    assert main.extract_search_terms("아이랑 해운대 가려고 하는데 유모차 이용하고 화장실 찾기 편한지 궁금해.")[0] == "해운대"


def test_gung_in_gunggeumhae_is_not_place_suffix():
    assert main._extract_explicit_place_phrase("아이랑 해운대 가려고 하는데 화장실 찾기 편한지 궁금해.") is None


def test_candidate_ranking_removes_unrelated_region_results():
    items = [
        {"contentid": "1", "title": "경주 감은사지"},
        {"contentid": "2", "title": "불국사"},
        {"contentid": "3", "title": "경주 교촌마을"},
    ]
    ranked = main._rank_place_candidates(items, "불국사")
    assert [x["title"] for x in ranked] == ["불국사"]


def test_candidate_ranking_keeps_only_relevant_haeundae_titles():
    items = [
        {"contentid": "1", "title": "라마다 앙코르 바이윈덤 부산 해운대"},
        {"contentid": "2", "title": "해운대해수욕장"},
        {"contentid": "3", "title": "광안리해수욕장"},
    ]
    ranked = main._rank_place_candidates(items, "해운대")
    assert "광안리해수욕장" not in [x["title"] for x in ranked]
    assert ranked[0]["title"] == "해운대해수욕장"


def test_candidate_ranking_returns_empty_when_titles_are_unrelated():
    items = [
        {"contentid": "1", "title": "롯데호텔 부산", "addr1": "부산광역시 부산진구 가야대로 772"},
        {"contentid": "2", "title": "부산 기장시장", "addr1": "부산광역시 기장군 기장읍"},
        {"contentid": "3", "title": "그랜드 조선 부산", "addr1": "부산광역시 해운대구 해운대해변로 292"},
    ]
    assert main._rank_place_candidates(items, "해운대") == []


def test_candidate_ranking_prefers_destination_prefix_over_keyword_suffix_business():
    items = [
        {"contentid": "1", "title": "라마다 앙코르 바이윈덤 부산 해운대", "addr1": "부산광역시 해운대구 구남로 9"},
        {"contentid": "2", "title": "해운대해수욕장", "addr1": "부산광역시 해운대구 해운대해변로 264"},
        {"contentid": "3", "title": "해운대 관광특구", "addr1": "부산광역시 해운대구 우동"},
    ]
    ranked = main._rank_place_candidates(items, "해운대")
    assert [x["title"] for x in ranked] == ["해운대 관광특구", "해운대해수욕장"] or [x["title"] for x in ranked] == ["해운대해수욕장", "해운대 관광특구"]
    assert all("라마다" not in x["title"] for x in ranked)


def test_candidate_ranking_treats_region_prefixed_exact_title_as_exact():
    items = [
        {"contentid": "1", "title": "불국사(서울)", "addr1": "서울특별시 강남구 광평로10길 30-71"},
        {"contentid": "2", "title": "경주 불국사 [유네스코 세계유산]", "addr1": "경상북도 경주시 불국로 385"},
        {"contentid": "3", "title": "불국사한옥팜스테이", "addr1": "경상북도 경주시 진티길 5-52"},
    ]
    ranked = main._rank_place_candidates(items, "불국사")
    assert {x["contentid"] for x in ranked} == {"1", "2"}


def test_place_resolver_requests_large_keyword_page(monkeypatch):
    calls = []

    class FakeService:
        def search_places(self, keyword, limit=10):
            calls.append((keyword, limit))
            return [{
                "contentid": "h1",
                "title": "해운대해수욕장",
                "addr1": "부산광역시 해운대구 해운대해변로 264",
            }]

        def get_place(self, content_id, search_item=None):
            return {"content_id": content_id, "name": search_item["title"]}

    monkeypatch.setattr(main, "travel_service", FakeService())
    req = main.ChatRequest(
        message="아이랑 해운대 가려고 하는데 유모차 이용하고 화장실 찾기 편한지 궁금해.",
        traveler_type="baby",
        needs=["stroller", "restroom_important"],
        current_place_id=None,
    )
    resolved = main._resolve_place(req)
    assert resolved["status"] == "ok"
    assert calls[0] == ("해운대", 100)


def test_candidate_ranking_prioritizes_canonical_tourist_destinations_for_generic_area_name():
    items = [
        {"contentid": "m1", "contenttypeid": "38", "title": "해운대시장", "addr1": "부산광역시 해운대구"},
        {"contentid": "l1", "contenttypeid": "14", "title": "부산 해운대도서관", "addr1": "부산광역시 해운대구"},
        {"contentid": "i1", "contenttypeid": "12", "title": "해운대 동백섬", "addr1": "부산광역시 해운대구"},
        {"contentid": "g1", "contenttypeid": "12", "title": "해운대 관광특구", "addr1": "부산광역시 해운대구"},
        {"contentid": "b1", "contenttypeid": "12", "title": "해운대해수욕장", "addr1": "부산광역시 해운대구"},
    ]
    ranked = main._rank_place_candidates(items, "해운대")
    titles = [x["title"] for x in ranked]
    assert titles[0] == "해운대해수욕장"
    assert titles.index("해운대 관광특구") < titles.index("해운대시장")


def test_ambiguous_response_wording_does_not_claim_same_name(monkeypatch):
    class FakeService:
        def search_places(self, keyword, limit=10):
            return [
                {"contentid": "1", "title": "해운대해수욕장", "addr1": "부산광역시 해운대구"},
                {"contentid": "2", "title": "해운대 관광특구", "addr1": "부산광역시 해운대구"},
            ]
    monkeypatch.setattr(main, "travel_service", FakeService())
    req = main.ChatRequest(
        message="아이랑 해운대 가려고 해",
        traveler_type="baby",
        needs=[],
        current_place_id=None,
    )
    resolved = main._resolve_place(req)
    assert resolved["status"] == "ambiguous"


def test_walking_difficult_is_supported_by_chat_contract():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "국립중앙박물관 많이 걸어야 해?",
                "traveler_type": "senior",
                "needs": ["walking_difficult"],
                "current_place_id": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        item = next(x for x in data["comfort"]["items"] if x["need"] == "walking_difficult")
        assert item["status"] == "UNKNOWN"
        assert "걷기 부담" in data["unknown_fields"]
        mobility = next(x for x in data["sections"] if x["key"] == "mobility")
        assert any(x["label"] == "보행 관련 정보" for x in mobility["items"])


def test_prompt_prioritizes_walking_burden_for_senior_questions():
    text = Path(main.__file__).read_text(encoding="utf-8")
    assert "보행거리·걷기 부담" in text


def test_mock_app_cache_is_namespaced_away_from_real_cache():
    with TestClient(main.app) as client:
        client.post(
            "/chat",
            json={
                "message": "성산일출봉 부모님이랑 가기 괜찮아?",
                "traveler_type": "senior",
                "needs": ["walking_difficult"],
                "current_place_id": None,
            },
        )
        assert "mock" in main.travel_service.cache_dir.parts
        assert "real" not in main.travel_service.cache_dir.parts


def test_prompt_qualifies_disability_only_facilities_for_generic_seniors():
    text = Path(main.__file__).read_text(encoding="utf-8")
    assert "장애인 전용 주차구역" in text
    assert "해당 이용 자격이 있는 경우" in text


def test_answer_policy_qualifies_disability_only_recommendation_for_generic_senior():
    answer = "권장 사항\n- 장애인 주차구역이나 장애인 탑승차량 이용을 고려하세요.\n- 휠체어 대여도 가능합니다."
    place = {
        "raw_details": {
            "parking": "장애인 주차구역이 있음",
            "handicapetc": "장애인 탑승차량은 매표소 앞까지 차량접근 가능함",
        },
        "accessibility": {},
    }
    sanitized = main._sanitize_answer_policy(answer, "부모님이 많이 걷기 힘들어", place)
    assert "이용을 고려하세요" not in sanitized
    assert "해당 이용 자격이 있는 경우" in sanitized
    assert "장애인 전용 주차구역·장애인 탑승차량" in sanitized
    assert "휠체어 대여도 가능합니다" in sanitized


def test_answer_policy_does_not_invent_disabled_vehicle_when_only_parking_exists():
    answer = "- 장애인 전용 주차구역·장애인 탑승차량 정보는 확인되지만, 해당 이용 자격이 있는 경우에만 실제 이용 가능 여부를 확인하세요."
    place = {
        "raw_details": {"parking": "장애인 전용 주차구역 주차대수 : 8대"},
        "accessibility": {"walking_info": "관광지까지의 거리 : 약 100m"},
    }
    sanitized = main._sanitize_answer_policy(answer, "부모님이 많이 걷기 힘들어", place)
    assert "장애인 전용 주차구역" in sanitized
    assert "장애인 탑승차량" not in sanitized
    assert "해당 이용 자격이 있는 경우" in sanitized


def test_answer_policy_removes_unsupported_disabled_vehicle_fact_line():
    answer = "확인된 정보\n- 장애인 탑승차량: 매표소 앞까지 접근 가능\n- 휠체어 대여: 있음"
    place = {
        "raw_details": {"parking": "장애인 전용 주차구역 있음"},
        "accessibility": {},
    }
    sanitized = main._sanitize_answer_policy(answer, "부모님과 방문해", place)
    assert "장애인 탑승차량" not in sanitized
    assert "휠체어 대여: 있음" in sanitized


def test_answer_policy_removes_false_map_search_unavailable_claim():
    answer = "더 도와드릴까요? 지도 검색어는 생성 불가합니다.\n수유실 위치는 1층입니다."
    sanitized = main._sanitize_answer_policy(answer, "수유실 위치 알려줘", {})
    assert "지도 검색어는 생성 불가" not in sanitized
    assert "수유실 위치는 1층입니다" in sanitized


def test_success_answer_is_short_and_hides_internal_rule_terms():
    with TestClient(main.app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "국립중앙박물관 아이랑 가기 괜찮아?",
                "traveler_type": "baby",
                "needs": ["need_nursing_room", "need_diaper_station", "stroller"],
                "current_place_id": None,
            },
        )
        data = response.json()
        assert data["success"] is True
        answer = data["answer"]
        assert len(answer) <= 160
        for banned in (
            "Rule Engine", "Comfort 판정", "SATISFIED", "CONFLICT", "UNKNOWN",
            "CHECK_NEEDED", "BURDEN_POSSIBLE", "INSUFFICIENT_DATA", "need_",
            "stairs_difficult", "walking_difficult",
        ):
            assert banned not in answer
