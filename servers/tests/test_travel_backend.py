import json
from pathlib import Path

from comfort import evaluate_comfort
from schemas import ComfortLevel, ComfortStatus, NeedType
from travel_data import TravelDataService, make_map_search_text, normalize_place


BASE_DIR = Path(__file__).resolve().parents[1]
FIXTURE = BASE_DIR / "data" / "mock_tour_api.json"


def _fixture_record(title: str):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(x for x in payload["places"] if x["search"]["title"] == title)


def test_false_and_null_are_distinct():
    record = _fixture_record("경복궁")
    place = normalize_place(
        record["search"],
        record["common"],
        record["intro"],
        record["with_tour"],
        mock_source=True,
    )
    assert place["baby"]["nursing_room"] is None
    assert place["baby"]["stroller_rental"] is False
    assert place["accessibility"]["elevator"] is None


def test_comfort_unknown_for_missing_nursing_room():
    record = _fixture_record("경복궁")
    place = normalize_place(
        record["search"],
        record["common"],
        record["intro"],
        record["with_tour"],
        mock_source=True,
    )
    result = evaluate_comfort(place, [NeedType.need_nursing_room])
    assert result.level == ComfortLevel.INSUFFICIENT_DATA
    assert result.items[0].status == ComfortStatus.UNKNOWN


def test_comfort_conflict_has_highest_priority():
    record = _fixture_record("성산일출봉")
    place = normalize_place(
        record["search"],
        record["common"],
        record["intro"],
        record["with_tour"],
        mock_source=True,
    )
    result = evaluate_comfort(
        place,
        [NeedType.need_elevator, NeedType.restroom_important],
    )
    assert result.level == ComfortLevel.BURDEN_POSSIBLE
    assert any(x.status == ComfortStatus.CONFLICT for x in result.items)


def test_comfort_check_needed_when_mixed_satisfied_unknown():
    record = _fixture_record("경복궁")
    place = normalize_place(
        record["search"],
        record["common"],
        record["intro"],
        record["with_tour"],
        mock_source=True,
    )
    result = evaluate_comfort(
        place,
        [NeedType.restroom_important, NeedType.need_nursing_room],
    )
    assert result.level == ComfortLevel.CHECK_NEEDED


def test_map_search_text_is_deterministic_and_never_guesses():
    assert (
        make_map_search_text(
            facility_name="수유실",
            parent_place="국립중앙박물관",
            road_address="서울특별시 용산구 서빙고로 137",
            region="서울특별시 용산구",
            internal_facility=True,
        )
        == "국립중앙박물관 서울특별시 용산구 서빙고로 137"
    )
    assert (
        make_map_search_text(
            facility_name="수유실",
            parent_place=None,
            road_address=None,
            jibun_address=None,
            region=None,
            internal_facility=True,
        )
        is None
    )


def test_mock_search_keeps_ambiguous_candidates(tmp_path):
    service = TravelDataService(
        data_dir=tmp_path,
        service_key=None,
        use_mock_when_no_key=True,
        fixture_path=FIXTURE,
    )
    results = service.search_places("중앙공원")
    assert len(results) == 2
    assert {x["contentid"] for x in results} == {"2001", "3001"}


def test_detail_cache_survives_service_restart(tmp_path):
    service1 = TravelDataService(
        data_dir=tmp_path,
        service_key=None,
        use_mock_when_no_key=True,
        fixture_path=FIXTURE,
    )
    item = service1.search_places("국립중앙박물관")[0]
    place1 = service1.get_place("1001", item)
    assert service1.cache_misses == 1

    service2 = TravelDataService(
        data_dir=tmp_path,
        service_key=None,
        use_mock_when_no_key=True,
        fixture_path=FIXTURE,
    )
    place2 = service2.get_place("1001")
    assert service2.cache_hits == 1
    assert place1["name"] == place2["name"] == "국립중앙박물관"


def test_missing_tour_api_key_without_mock_raises(tmp_path):
    from travel_data import TourApiError, TravelDataService

    service = TravelDataService(
        data_dir=tmp_path,
        service_key="",
        use_mock_when_no_key=False,
    )
    try:
        service.search_places("국립중앙박물관")
        assert False, "TourApiError expected when no key and mock is disabled"
    except TourApiError as exc:
        assert "TOUR_API_SERVICE_KEY" in str(exc)


def test_v43_with_tour_uses_content_id_only():
    from travel_data import TourApiClient

    client = TourApiClient(service_key="dummy")
    captured = {}

    def fake_get(endpoint, **params):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return []

    client._get = fake_get  # type: ignore[method-assign]
    client.detail_with_tour("126508", "12")

    assert captured["endpoint"] == "detailWithTour2"
    assert captured["params"] == {"contentId": "126508"}


def test_v43_common_uses_content_id_only():
    from travel_data import TourApiClient

    client = TourApiClient(service_key="dummy")
    captured = {}

    def fake_get(endpoint, **params):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return []

    client._get = fake_get  # type: ignore[method-assign]
    client.detail_common("126508")

    assert captured["endpoint"] == "detailCommon2"
    assert captured["params"] == {"contentId": "126508"}


def test_accessible_path_uses_exit_and_publictransport_fields():
    place = normalize_place(
        {"contentid": "126508", "contenttypeid": "12", "title": "경복궁"},
        {
            "contentid": "126508",
            "contenttypeid": "12",
            "title": "경복궁",
            "addr1": "서울특별시 종로구 사직로 161",
        },
        {},
        {
            "contentid": "126508",
            "route": "",
            "exit": "주출입구는 경사로가 있어 휠체어 접근 가능함",
            "publictransport": "",
        },
    )

    assert place["accessibility"]["accessible_path"] is True
    assert place["accessibility"]["slope"] is True
    result = evaluate_comfort(place, [NeedType.stairs_difficult])
    assert result.items[0].status == ComfortStatus.SATISFIED


def test_intro_stroller_rental_is_used_as_official_fallback():
    place = normalize_place(
        {"contentid": "1", "contenttypeid": "12", "title": "테스트 관광지"},
        {"contentid": "1", "contenttypeid": "12", "title": "테스트 관광지"},
        {"chkbabycarriage": "없음"},
        {"contentid": "1", "stroller": ""},
    )
    assert place["baby"]["stroller_rental"] is False


def test_stroller_inventory_is_normalized_without_overstating_access():
    place = normalize_place(
        {"contentid": "s1", "title": "테스트과학관", "addr1": "대전광역시 유성구 테스트로 1"},
        {"contentid": "s1", "title": "테스트과학관"},
        {},
        {"infantsfamilyetc": "안내매표소에 유모차 8대 보유"},
    )
    assert place["baby"]["stroller_rental"] is True
    assert place["baby"]["stroller_access"] is None
    result = evaluate_comfort(place, [NeedType.stroller])
    assert result.items[0].status == ComfortStatus.UNKNOWN
    assert "대여 정보는 확인" in result.items[0].reason


def test_public_transport_access_does_not_prove_step_free_route():
    place = normalize_place(
        {"contentid": "p1", "title": "테스트관광지", "addr1": "제주특별자치도 테스트시 테스트로 1"},
        {"contentid": "p1", "title": "테스트관광지"},
        {},
        {"publictransport": "저상버스 이용 가능, 정류장 접근 가능"},
    )
    assert place["accessibility"]["accessible_path"] is None
    result = evaluate_comfort(place, [NeedType.stairs_difficult])
    assert result.items[0].status == ComfortStatus.UNKNOWN


def test_walking_need_preserves_numeric_distance_without_arbitrary_threshold():
    place = normalize_place(
        {"contentid": "w1", "title": "테스트관광지", "addr1": "제주특별자치도 테스트로 1"},
        {"contentid": "w1", "title": "테스트관광지"},
        {},
        {"parking": "관광지까지의 거리 : 약 100m"},
    )
    assert "100m" in place["accessibility"]["walking_info"]
    assert place["accessibility"]["walking_burden"] is None
    result = evaluate_comfort(place, [NeedType.walking_difficult])
    assert result.items[0].status == ComfortStatus.UNKNOWN
    assert "명확한 근거" in result.items[0].reason


def test_walking_need_disability_only_vehicle_access_is_not_generic_satisfaction():
    place = normalize_place(
        {"contentid": "w2", "title": "테스트사찰", "addr1": "경상북도 테스트로 1"},
        {"contentid": "w2", "title": "테스트사찰"},
        {},
        {"handicapetc": "장애인 탑승차량은 매표소 앞까지 차량접근 가능함"},
    )
    assert place["accessibility"]["walking_burden"] is None
    result = evaluate_comfort(place, [NeedType.walking_difficult])
    assert result.items[0].status == ComfortStatus.UNKNOWN


def test_walking_need_conflict_requires_explicit_walking_burden_statement():
    place = normalize_place(
        {"contentid": "w3", "title": "테스트전망대", "addr1": "강원특별자치도 테스트로 1"},
        {"contentid": "w3", "title": "테스트전망대"},
        {},
        {"route": "정상까지 장거리 도보 이동이 필요함"},
    )
    assert place["accessibility"]["walking_burden"] is True
    result = evaluate_comfort(place, [NeedType.walking_difficult])
    assert result.items[0].status == ComfortStatus.CONFLICT
    assert result.level == ComfortLevel.BURDEN_POSSIBLE


def test_real_and_mock_cache_namespaces_are_separate(tmp_path):
    mock_service = TravelDataService(
        data_dir=tmp_path,
        service_key=None,
        use_mock_when_no_key=True,
        fixture_path=FIXTURE,
    )
    real_service = TravelDataService(
        data_dir=tmp_path,
        service_key="dummy-real-key",
        use_mock_when_no_key=False,
    )
    assert mock_service.cache_dir != real_service.cache_dir
    assert "mock" in mock_service.cache_dir.parts
    assert "real" in real_service.cache_dir.parts


def test_walking_need_does_not_treat_disability_only_vehicle_access_as_generic_senior_satisfaction():
    place = normalize_place(
        {"contentid": "x1", "title": "테스트"},
        {"contentid": "x1", "title": "테스트"},
        {},
        {
            "parking": "장애인 주차구역이 있음(주출입구 근처)",
            "handicapetc": "장애인 탑승차량은 매표소 앞까지 차량접근 가능함",
        },
        mock_source=False,
    )
    result = evaluate_comfort(place, [NeedType.walking_difficult])
    assert result.level == ComfortLevel.INSUFFICIENT_DATA
    assert result.items[0].status == ComfortStatus.UNKNOWN
    assert place["accessibility"]["walking_info"] is not None


def test_walking_need_can_still_satisfy_on_general_vehicle_access():
    place = normalize_place(
        {"contentid": "x2", "title": "테스트"},
        {"contentid": "x2", "title": "테스트"},
        {},
        {"handicapetc": "일반 차량은 매표소 앞까지 차량접근 가능함"},
        mock_source=False,
    )
    result = evaluate_comfort(place, [NeedType.walking_difficult])
    assert result.items[0].status == ComfortStatus.SATISFIED


def test_walking_info_does_not_include_general_overview_paragraph():
    place = normalize_place(
        {"contentid": "w9", "title": "테스트봉", "addr1": "제주특별자치도 테스트로 1"},
        {
            "contentid": "w9",
            "title": "테스트봉",
            "overview": "이 관광지는 아름다운 경관으로 유명하며 주변 거리와 역사 이야기를 길게 설명하는 일반 소개문입니다. " * 8,
        },
        {},
        {"parking": "관광지까지의 거리 : 약 100m"},
    )
    info = place["accessibility"]["walking_info"]
    assert info is not None
    assert "100m" in info
    assert "아름다운 경관" not in info
    assert len(info) < 300


def test_walking_info_extracts_only_relevant_snippet_from_mixed_accessibility_field():
    mixed = (
        "장애인 전용 주차구역 주차대수 : 8대(성산일출봉주차장). "
        "관광지까지의 거리 : 약 100m / "
        "해발 180m인 성산 일출봉은 약 5,000년 전 바닷속에서 수중폭발한 화산체이다. "
        "용암과 화산재의 형성과정을 설명하는 일반 관광지 소개문입니다."
    )
    place = normalize_place(
        {"contentid": "w10", "title": "테스트봉"},
        {"contentid": "w10", "title": "테스트봉"},
        {},
        {"handicapetc": mixed},
        mock_source=False,
    )
    info = place["accessibility"]["walking_info"]
    assert info is not None
    assert "100m" in info
    assert "수중폭발" not in info
    assert "화산재" not in info

