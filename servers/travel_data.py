from __future__ import annotations

import json
import os
import re
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

import httpx


TOUR_API_DEFAULT_BASE_URL = "https://apis.data.go.kr/B551011/KorWithService2"
DEFAULT_MOBILE_OS = "ETC"
DEFAULT_MOBILE_APP = "FamilyComfortTravelChatbot"


class TourApiError(RuntimeError):
    pass


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text or None


def _first_nonempty(*values: Any) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


def _presence(
    text: Optional[str],
    *,
    positive: Tuple[str, ...] = ("있음", "가능", "구비", "설치", "운영"),
    negative: Tuple[str, ...] = ("없음", "불가", "미설치", "미운영", "제공하지 않"),
) -> Optional[bool]:
    if not text:
        return None
    lowered = text.replace(" ", "")
    if any(word.replace(" ", "") in lowered for word in negative):
        return False
    if any(word.replace(" ", "") in lowered for word in positive):
        return True
    return None


def _keyword_presence(
    text: Optional[str],
    keyword: str,
    *,
    positive_suffixes: Tuple[str, ...] = ("있음", "가능", "구비", "설치", "운영", "제공"),
    negative_suffixes: Tuple[str, ...] = ("없음", "불가", "미설치", "미운영"),
) -> Optional[bool]:
    if not text:
        return None
    compact = text.replace(" ", "")
    key = keyword.replace(" ", "")
    if key not in compact:
        return None

    for suffix in negative_suffixes:
        if key + suffix.replace(" ", "") in compact:
            return False
    for suffix in positive_suffixes:
        if key + suffix.replace(" ", "") in compact:
            return True

    # 키워드가 공식 상세문구에 등장했지만 존재/부재를 명시하지 않은 경우는 UNKNOWN
    return None


def _walking_evidence(*texts: Optional[str]) -> Tuple[Optional[bool], Optional[str]]:
    """Extract conservative walking-burden evidence from official text.

    Return value semantics:
    - True: official text explicitly indicates a walking burden
    - False: official text explicitly indicates a generally usable low-walking/close-access condition
    - None: walking information is missing or not strong enough to classify

    Important: disability-only benefits (e.g. 장애인 탑승차량, 장애인 전용 주차)
    are preserved as walking_info but do not satisfy a generic senior
    ``walking_difficult`` need, because eligibility cannot be assumed.
    Numeric distances/times are also preserved but never thresholded arbitrarily.
    """
    cleaned: List[str] = []
    for value in texts:
        text = _clean_text(value)
        if text and text not in cleaned:
            cleaned.append(text)

    if not cleaned:
        return None, None

    walking_keywords = re.compile(
        r"도보|보행|걷|걸어|거리|차량\s*(?:접근|진입)|주출입(?:구|문)|매표소|주차장|경사로|계단|엘리베이터|휠체어",
        re.I,
    )

    def _snippets(text: str) -> List[str]:
        # Some TourAPI accessibility fields occasionally contain a useful
        # accessibility sentence followed by a long general-description paragraph.
        # Field-level filtering is therefore not enough: split into clauses/sentences
        # first and retain only the pieces that actually contain walking evidence.
        parts = re.split(r"(?:\r?\n)+|\s*/\s*|_+|(?<=[.!?])\s*", text)
        selected: List[str] = []
        for part in parts:
            part = part.strip(" -•\t")
            if not part or not walking_keywords.search(part):
                continue
            # Defensive bound for malformed source text with no punctuation. Keep a
            # local window around the first walking keyword instead of exposing a
            # whole unrelated overview paragraph in the mobility section.
            if len(part) > 320:
                match = walking_keywords.search(part)
                if match:
                    start = max(0, match.start() - 100)
                    end = min(len(part), match.end() + 180)
                    part = part[start:end].strip()
                    if start > 0:
                        part = "…" + part
                    if end < len(text):
                        part = part + "…"
            if part and part not in selected:
                selected.append(part)
        return selected

    evidence: List[str] = []
    for text in cleaned:
        for snippet in _snippets(text):
            if snippet not in evidence:
                evidence.append(snippet)

    if not evidence:
        return None, None

    walking_info = " / ".join(evidence)

    burden_markers = (
        "장거리도보",
        "많이걸",
        "도보필수",
        "도보로만",
        "장시간도보",
        "긴거리도보",
    )
    low_burden_markers = (
        "차량접근가능",
        "차량진입가능",
        "매표소앞까지차량",
        "주출입문에서최단거리",
        "주출입구에서최단거리",
        "주출입문과인접",
        "주출입구와인접",
        "바로앞",
    )
    restricted_markers = (
        "장애인",
        "휠체어",
        "교통약자",
        "장애인전용",
    )

    has_burden = False
    has_general_low_burden = False
    for text in evidence:
        compact = re.sub(r"\s+", "", text)
        if any(marker in compact for marker in burden_markers):
            has_burden = True
        if any(marker in compact for marker in low_burden_markers):
            # Do not infer that a generic senior can use a disability-only benefit.
            restricted = any(marker in compact for marker in restricted_markers)
            if not restricted:
                has_general_low_burden = True

    if has_burden and has_general_low_burden:
        return None, walking_info
    if has_burden:
        return True, walking_info
    if has_general_low_burden:
        return False, walking_info
    return None, walking_info


def _derive_region(address: Optional[str], area_name: Optional[str] = None) -> Optional[str]:
    if area_name:
        return _clean_text(area_name)
    if not address:
        return None
    parts = address.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return parts[0] if parts else None


def make_map_search_text(
    *,
    facility_name: Optional[str],
    parent_place: Optional[str],
    road_address: Optional[str],
    jibun_address: Optional[str] = None,
    region: Optional[str] = None,
    internal_facility: bool = True,
) -> Optional[str]:
    """
    Deterministic map search text.
    Never invents or geocodes an address.
    """
    address = _clean_text(road_address) or _clean_text(jibun_address)
    if internal_facility:
        if parent_place and address:
            return f"{parent_place} {address}".strip()
    else:
        if facility_name and address:
            return f"{facility_name} {address}".strip()

    if parent_place and region:
        return f"{parent_place} {region}".strip()
    return None


def _extract_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        response = payload.get("response", {})
        header = response.get("header", {})
        result_code = str(header.get("resultCode", "0000"))
        if result_code not in {"0000", "0"}:
            msg = header.get("resultMsg") or "TourAPI returned an error"
            raise TourApiError(f"{result_code}: {msg}")

        items = response.get("body", {}).get("items", {})
        if not items:
            return []
        item = items.get("item", [])
        if isinstance(item, dict):
            return [item]
        if isinstance(item, list):
            return item
        return []
    except TourApiError:
        raise
    except Exception as exc:
        raise TourApiError(f"Unexpected TourAPI response format: {exc}") from exc


class TourApiClient:
    """
    한국관광공사 무장애 여행 정보 (KorWithService2) adapter.

    MVP에서 사용하는 endpoint:
    - searchKeyword2: 관광지 식별
    - detailCommon2: 관광지명/주소/개요/기본 메타데이터
    - detailIntro2: 콘텐츠 유형별 소개정보(운영시간/휴무/일반 주차 등)
    - detailWithTour2: 무장애/고령자/영유아 상세정보
    """

    def __init__(
        self,
        service_key: str,
        base_url: str = TOUR_API_DEFAULT_BASE_URL,
        mobile_app: str = DEFAULT_MOBILE_APP,
        timeout: float = 10.0,
    ):
        if not service_key:
            raise ValueError("TOUR_API_SERVICE_KEY is required")
        # 공공데이터포털의 Encoding 키가 들어와도 httpx가 한 번만 인코딩하도록 decode.
        self.service_key = unquote(service_key.strip())
        self.base_url = base_url.rstrip("/")
        self.mobile_app = mobile_app
        self.timeout = timeout

    def _params(self, **extra: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "serviceKey": self.service_key,
            "MobileOS": DEFAULT_MOBILE_OS,
            "MobileApp": self.mobile_app,
            "_type": "json",
        }
        params.update({k: v for k, v in extra.items() if v is not None})
        return params

    def _get(self, endpoint: str, **params: Any) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=self._params(**params))
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise TourApiError(f"TourAPI HTTP error: {exc}") from exc
        except ValueError as exc:
            raise TourApiError("TourAPI did not return valid JSON") from exc
        return _extract_items(payload)

    def search_keyword(self, keyword: str, num_of_rows: int = 10) -> List[Dict[str, Any]]:
        return self._get(
            "searchKeyword2",
            keyword=keyword,
            numOfRows=num_of_rows,
            pageNo=1,
            arrange="A",
        )

    def detail_common(self, content_id: str) -> Dict[str, Any]:
        # KorWithService2 v4.3: detailCommon2 request flags such as
        # defaultYN/firstImageYN/areacodeYN/addrinfoYN/mapinfoYN/overviewYN
        # were removed. contentId is the only operation-specific request field.
        items = self._get(
            "detailCommon2",
            contentId=content_id,
        )
        return items[0] if items else {}

    def detail_intro(self, content_id: str, content_type_id: Optional[str]) -> Dict[str, Any]:
        if not content_type_id:
            return {}
        items = self._get(
            "detailIntro2",
            contentId=content_id,
            contentTypeId=content_type_id,
        )
        return items[0] if items else {}

    def detail_with_tour(self, content_id: str, content_type_id: Optional[str]) -> Dict[str, Any]:
        # KorWithService2 v4.3: detailWithTour2 accepts contentId only.
        # contentTypeId is intentionally not sent even though callers may already
        # know it from search/detailCommon2.
        items = self._get("detailWithTour2", contentId=content_id)
        return items[0] if items else {}


class MockTourApiClient:
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path
        self.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.places: List[Dict[str, Any]] = self.fixture.get("places", [])

    def search_keyword(self, keyword: str, num_of_rows: int = 10) -> List[Dict[str, Any]]:
        keyword_compact = re.sub(r"\s+", "", keyword).lower()
        if not keyword_compact:
            return []
        results = []
        for record in self.places:
            item = record.get("search", {})
            haystacks = [
                str(item.get("title", "")),
                str(item.get("addr1", "")),
                str(item.get("addr2", "")),
            ]
            text = re.sub(r"\s+", "", " ".join(haystacks)).lower()
            title_compact = re.sub(r"\s+", "", str(item.get("title", ""))).lower()
            if keyword_compact in text or (title_compact and title_compact in keyword_compact):
                results.append(item)
        return results[:num_of_rows]

    def _record(self, content_id: str) -> Dict[str, Any]:
        for record in self.places:
            if str(record.get("search", {}).get("contentid")) == str(content_id):
                return record
        return {}

    def detail_common(self, content_id: str) -> Dict[str, Any]:
        return self._record(content_id).get("common", {})

    def detail_intro(self, content_id: str, content_type_id: Optional[str]) -> Dict[str, Any]:
        return self._record(content_id).get("intro", {})

    def detail_with_tour(self, content_id: str, content_type_id: Optional[str]) -> Dict[str, Any]:
        return self._record(content_id).get("with_tour", {})


def normalize_place(
    search_item: Dict[str, Any],
    common: Dict[str, Any],
    intro: Dict[str, Any],
    with_tour: Dict[str, Any],
    *,
    mock_source: bool = False,
) -> Dict[str, Any]:
    content_id = str(
        common.get("contentid")
        or common.get("contentId")
        or search_item.get("contentid")
        or search_item.get("contentId")
        or ""
    )
    name = _first_nonempty(common.get("title"), search_item.get("title")) or "이름 미확인"
    addr1 = _first_nonempty(common.get("addr1"), search_item.get("addr1"))
    addr2 = _first_nonempty(common.get("addr2"), search_item.get("addr2"))
    address = " ".join(x for x in [addr1, addr2] if x).strip() or None
    region = _derive_region(address)

    route_text = _clean_text(with_tour.get("route"))
    exit_text = _clean_text(with_tour.get("exit"))
    public_transport_text = _clean_text(with_tour.get("publictransport"))
    elevator_text = _clean_text(with_tour.get("elevator"))
    restroom_text = _clean_text(with_tour.get("restroom"))
    wheelchair_text = _clean_text(with_tour.get("wheelchair"))
    stroller_text = _clean_text(with_tour.get("stroller"))
    lactation_text = _clean_text(with_tour.get("lactationroom"))
    accessible_parking_text = _clean_text(with_tour.get("parking"))
    physical_extra = _clean_text(with_tour.get("handicapetc"))
    baby_extra = _clean_text(with_tour.get("infantsfamilyetc"))

    # The official v4.3 schema can describe physical access across route(접근로),
    # exit(출입통로), and publictransport(대중교통). Do not discard a confirmed
    # ramp/step-free statement merely because route itself is empty.
    # Physical path inference must use only route/entrance information.
    # A public-transport sentence such as "저상버스 이용 가능" is useful context
    # but does not prove that stairs can be avoided inside the destination.
    mobility_text = " ".join(x for x in [route_text, exit_text] if x) or None
    route_compact = (mobility_text or "").replace(" ", "")
    if any(k in route_compact for k in ("접근불가", "휠체어접근불가", "진입불가")):
        accessible_path = False
    elif any(k in route_compact for k in ("무단차", "접근가능", "휠체어접근가능", "경사로")):
        accessible_path = True
    else:
        accessible_path = None

    if mobility_text and "계단" in mobility_text:
        stairs = False if "계단 없음" in mobility_text or "계단없음" in route_compact else True
    else:
        stairs = None

    if mobility_text and "경사로" in mobility_text:
        slope = False if "경사로 없음" in mobility_text or "경사로없음" in route_compact else True
    else:
        slope = None

    elevator = _presence(elevator_text)
    accessible_restroom = _presence(restroom_text)
    wheelchair_rental = _presence(
        wheelchair_text,
        positive=("대여 가능", "대여가능", "대여", "있음", "제공"),
        negative=("대여 불가", "대여불가", "없음", "미제공"),
    )

    intro_stroller_text = _first_nonempty(
        intro.get("chkbabycarriage"),
        intro.get("chkbabycarriageculture"),
        intro.get("chkbabycarriageleports"),
        intro.get("chkbabycarriageshopping"),
    )
    stroller_evidence_parts = [stroller_text, intro_stroller_text]
    if baby_extra and "유모차" in baby_extra:
        stroller_evidence_parts.append(baby_extra)
    stroller_evidence = " ".join(x for x in stroller_evidence_parts if x) or None
    stroller_rental = _presence(
        stroller_evidence,
        positive=("대여 가능", "대여가능", "대여", "보유", "비치", "제공"),
        negative=("대여 불가", "대여불가", "대여 없음", "대여없음", "없음", "미제공"),
    )
    if stroller_text:
        stroller_access = _keyword_presence(stroller_text, "유모차")
        if stroller_access is None and any(k in stroller_text for k in ("입장 가능", "진입 가능", "이용 가능")):
            stroller_access = True
        elif stroller_access is None and any(k in stroller_text for k in ("입장 불가", "진입 불가", "이용 불가")):
            stroller_access = False
    else:
        stroller_access = None

    nursing_room = _presence(
        lactation_text,
        positive=("있음", "운영", "구비", "설치", "이용 가능", "이용가능"),
        negative=("없음", "미운영", "미설치", "이용 불가", "이용불가"),
    )

    diaper_text = " ".join(x for x in [lactation_text, baby_extra] if x)
    if "기저귀" in diaper_text and ("교환" in diaper_text or "갈이" in diaper_text):
        diaper_station = _presence(
            diaper_text,
            positive=("있음", "구비", "설치", "이용 가능", "이용가능"),
            negative=("없음", "미설치", "이용 불가", "이용불가"),
        )
        if diaper_station is None:
            # '기저귀 교환대'가 시설 설명에 명시되어 있으면 존재 확인으로 취급.
            diaper_station = True
    else:
        diaper_station = None

    rest_text = " ".join(x for x in [physical_extra, baby_extra, route_text] if x)
    if rest_text and any(k in rest_text for k in ("휴게", "휴식", "쉼터", "벤치")):
        if any(k in rest_text.replace(" ", "") for k in ("휴게공간없음", "휴식공간없음", "벤치없음")):
            rest_area = False
        else:
            rest_area = True
    else:
        rest_area = None

    general_parking_text = _first_nonempty(
        intro.get("parking"),
        intro.get("parkingculture"),
        intro.get("parkingfood"),
        intro.get("parkingleports"),
        intro.get("parkinglodging"),
        intro.get("parkingshopping"),
    )
    parking_value = _presence(general_parking_text) if general_parking_text else _presence(accessible_parking_text)

    # Keep walking evidence scoped to accessibility/transport/parking fields.
    # A general 관광지 overview can contain unrelated words such as "거리" and
    # pollute the walking section with a long descriptive paragraph. When the
    # dedicated accessibility fields do not support a walking judgment, prefer
    # UNKNOWN rather than mining the general overview heuristically.
    walking_burden, walking_info = _walking_evidence(
        accessible_parking_text,
        general_parking_text,
        route_text,
        exit_text,
        public_transport_text,
        physical_extra,
    )

    opening_hours = _first_nonempty(
        intro.get("usetime"),
        intro.get("usetimeculture"),
        intro.get("opentimefood"),
        intro.get("usetimeleports"),
        intro.get("usetimefestival"),
        intro.get("opentime"),
        intro.get("checkintime"),
    )
    closed_days = _first_nonempty(
        intro.get("restdate"),
        intro.get("restdateculture"),
        intro.get("restdatefood"),
        intro.get("restdateleports"),
        intro.get("restdateshopping"),
    )

    updated_at = _first_nonempty(
        common.get("modifiedtime"),
        search_item.get("modifiedtime"),
        common.get("modifiedTime"),
    )

    source_title = "무장애 여행 정보 (Mock Fixture)" if mock_source else "무장애 여행 정보"

    normalized: Dict[str, Any] = {
        "content_id": content_id,
        "content_type_id": str(
            common.get("contenttypeid")
            or common.get("contentTypeId")
            or search_item.get("contenttypeid")
            or search_item.get("contentTypeId")
            or ""
        ) or None,
        "name": name,
        "region": region,
        "address": address,
        "basic": {
            "opening_hours": opening_hours,
            "closed_days": closed_days,
            "parking": parking_value,
        },
        "accessibility": {
            "accessible_path": accessible_path,
            "stairs": stairs,
            "slope": slope,
            "elevator": elevator,
            "rest_area": rest_area,
            "wheelchair_rental": wheelchair_rental,
            "walking_burden": walking_burden,
            "walking_info": walking_info,
        },
        "baby": {
            "stroller_access": stroller_access,
            "stroller_rental": stroller_rental,
            "nursing_room": nursing_room,
            "diaper_station": diaper_station,
        },
        "restroom": {
            "available": accessible_restroom,
            "accessible_restroom": accessible_restroom,
            "child_facility": diaper_station,
        },
        "source": {
            "organization": "한국관광공사",
            "title": source_title,
            "updated_at": updated_at,
        },
        "overview": _clean_text(common.get("overview")),
        "raw_details": {
            "parking": accessible_parking_text or general_parking_text,
            "route": route_text,
            "exit": exit_text,
            "publictransport": public_transport_text,
            "elevator": elevator_text,
            "restroom": restroom_text,
            "wheelchair": wheelchair_text,
            "stroller": stroller_evidence,
            "lactationroom": lactation_text,
            "handicapetc": physical_extra,
            "infantsfamilyetc": baby_extra,
            "walking": walking_info,
        },
    }
    return normalized


class TravelDataService:
    def __init__(
        self,
        *,
        data_dir: Path,
        service_key: Optional[str] = None,
        base_url: Optional[str] = None,
        use_mock_when_no_key: bool = True,
        fixture_path: Optional[Path] = None,
    ):
        self.data_dir = data_dir
        self.fixture_path = fixture_path or (data_dir / "mock_tour_api.json")
        self.service_key = (service_key or "").strip()
        self.mock_mode = not bool(self.service_key) and use_mock_when_no_key

        # Never let development Mock fixtures contaminate real TourAPI cache.
        # Pytest intentionally boots the app in Mock mode, so using a shared cache
        # directory would allow later REAL runs to reuse fixture content_ids.
        cache_namespace = "mock" if self.mock_mode else ("real" if self.service_key else "disabled")
        self.cache_root = data_dir / "cache" / cache_namespace
        self.cache_dir = self.cache_root / "places"
        self.search_cache_dir = self.cache_root / "search"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.search_cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_hits = 0
        self.cache_misses = 0

        if self.service_key:
            self.client = TourApiClient(
                service_key=self.service_key,
                base_url=base_url or TOUR_API_DEFAULT_BASE_URL,
            )
        elif self.mock_mode:
            self.client = MockTourApiClient(self.fixture_path)
        else:
            self.client = None

    @property
    def api_ready(self) -> bool:
        return bool(self.service_key)

    def _cache_path(self, content_id: str) -> Path:
        safe = re.sub(r"[^0-9A-Za-z_-]", "_", str(content_id))
        return self.cache_dir / f"{safe}.json"

    def _read_cached(self, content_id: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(content_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.cache_hits += 1
            return data
        except Exception:
            return None

    def _write_cached(self, place: Dict[str, Any]) -> None:
        content_id = str(place.get("content_id") or "")
        if not content_id:
            return
        path = self._cache_path(content_id)
        path.write_text(json.dumps(place, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_cached_places(self) -> List[Dict[str, Any]]:
        places: List[Dict[str, Any]] = []
        for path in self.cache_dir.glob("*.json"):
            try:
                places.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return places

    def _search_cache_path(self, keyword: str) -> Path:
        compact = re.sub(r"[^0-9A-Za-z가-힣_-]", "_", keyword.strip().lower())
        compact = compact[:80] or "empty"
        return self.search_cache_dir / f"{compact}.json"

    def search_places(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        # Local keyword cache first. It stores the complete candidate set returned by
        # the upstream search so a cached generic name does not hide ambiguity.
        search_cache = self._search_cache_path(keyword)
        if search_cache.exists():
            try:
                items = json.loads(search_cache.read_text(encoding="utf-8"))
                if isinstance(items, list):
                    return items[:limit]
            except Exception:
                pass

        if self.client is None:
            # If API is intentionally disabled, best-effort search over already
            # normalized local places.
            compact = re.sub(r"\s+", "", keyword).lower()
            cached_candidates: List[Dict[str, Any]] = []
            for place in self.list_cached_places():
                title = str(place.get("name", ""))
                address = str(place.get("address", ""))
                hay = re.sub(r"\s+", "", f"{title} {address}").lower()
                title_compact = re.sub(r"\s+", "", title).lower()
                if compact in hay or (title_compact and title_compact in compact):
                    cached_candidates.append(
                        {
                            "contentid": place.get("content_id"),
                            "contenttypeid": place.get("content_type_id"),
                            "title": place.get("name"),
                            "addr1": place.get("address"),
                            "_cached": True,
                        }
                    )
            if cached_candidates:
                return cached_candidates[:limit]
            raise TourApiError("TOUR_API_SERVICE_KEY is not configured")

        items = self.client.search_keyword(keyword, num_of_rows=limit)
        try:
            search_cache.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return items[:limit]

    def get_place(
        self,
        content_id: str,
        search_item: Optional[Dict[str, Any]] = None,
        *,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        if not force_refresh:
            cached = self._read_cached(content_id)
            if cached:
                return cached

        self.cache_misses += 1
        if self.client is None:
            raise TourApiError("TOUR_API_SERVICE_KEY is not configured")

        search_item = search_item or {"contentid": content_id}
        common = self.client.detail_common(content_id)
        content_type_id = (
            common.get("contenttypeid")
            or common.get("contentTypeId")
            or search_item.get("contenttypeid")
            or search_item.get("contentTypeId")
        )
        intro = self.client.detail_intro(content_id, str(content_type_id) if content_type_id else None)
        with_tour = self.client.detail_with_tour(content_id, str(content_type_id) if content_type_id else None)
        normalized = normalize_place(
            search_item=search_item,
            common=common,
            intro=intro,
            with_tour=with_tour,
            mock_source=self.mock_mode,
        )
        self._write_cached(normalized)
        return normalized
