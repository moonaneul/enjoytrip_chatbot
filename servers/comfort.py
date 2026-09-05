from __future__ import annotations

from typing import Any, Dict, Iterable, List

from schemas import (
    ComfortItem,
    ComfortLevel,
    ComfortResult,
    ComfortStatus,
    NeedType,
)


LEVEL_LABELS = {
    ComfortLevel.BURDEN_POSSIBLE: "이용 부담이 있을 수 있어요",
    ComfortLevel.INSUFFICIENT_DATA: "판단할 공식 정보가 부족해요",
    ComfortLevel.CHECK_NEEDED: "방문 전 확인할 정보가 있어요",
    ComfortLevel.COMFORTABLE: "선택한 조건은 공식 정보에서 확인돼요",
}


def _get(place: Dict[str, Any], *path: str):
    cur: Any = place
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _item(need: NeedType, status: ComfortStatus, reason: str) -> ComfortItem:
    return ComfortItem(need=need, status=status, reason=reason)


def evaluate_need(place: Dict[str, Any], need: NeedType) -> ComfortItem:
    if need == NeedType.walking_difficult:
        burden = _get(place, "accessibility", "walking_burden")
        info = _get(place, "accessibility", "walking_info")
        if burden is False:
            return _item(
                need,
                ComfortStatus.SATISFIED,
                "공식 정보에서 걷기 부담을 줄일 수 있는 가까운 접근 또는 차량 접근 근거가 확인됩니다.",
            )
        if burden is True:
            return _item(
                need,
                ComfortStatus.CONFLICT,
                "공식 정보에서 장거리 도보 등 걷기 부담이 될 수 있는 이동 조건이 명시되어 있습니다.",
            )
        if info:
            return _item(
                need,
                ComfortStatus.UNKNOWN,
                "공식 보행 관련 정보는 있으나 걷기 부담을 판단할 만큼 명확한 근거는 없습니다.",
            )
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 보행거리나 걷기 부담 정보를 확인할 수 없습니다.")

    if need == NeedType.need_nursing_room:
        value = _get(place, "baby", "nursing_room")
        if value is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 수유실이 확인됩니다.")
        if value is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 수유실이 없다고 명시되어 있습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 수유실 정보를 확인할 수 없습니다.")

    if need == NeedType.need_diaper_station:
        value = _get(place, "baby", "diaper_station")
        if value is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 기저귀 교환 시설이 확인됩니다.")
        if value is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 기저귀 교환 시설이 없다고 명시되어 있습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 기저귀 교환 시설 정보를 확인할 수 없습니다.")

    if need == NeedType.need_elevator:
        value = _get(place, "accessibility", "elevator")
        if value is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 엘리베이터가 확인됩니다.")
        if value is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 엘리베이터가 없다고 명시되어 있습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 엘리베이터 정보를 확인할 수 없습니다.")

    if need == NeedType.restroom_important:
        available = _get(place, "restroom", "available")
        accessible = _get(place, "restroom", "accessible_restroom")
        value = accessible if accessible is not None else available
        if value is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 이용 가능한 화장실 정보가 확인됩니다.")
        if value is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 필요한 화장실을 이용하기 어렵다고 명시되어 있습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 화장실 정보를 확인할 수 없습니다.")

    if need == NeedType.need_rest_area:
        value = _get(place, "accessibility", "rest_area")
        if value is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 휴식 공간이 확인됩니다.")
        if value is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 휴식 공간이 없다고 명시되어 있습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 휴식 공간 정보를 확인할 수 없습니다.")

    if need == NeedType.stroller:
        access = _get(place, "baby", "stroller_access")
        rental = _get(place, "baby", "stroller_rental")
        # Rental availability is useful facility information, but it does not prove
        # that the visitor can move through the destination with a stroller.
        if access is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 유모차로 이용 가능한 접근 정보가 확인됩니다.")
        if access is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 유모차 이용이 어렵다고 명시되어 있습니다.")
        if rental is True:
            return _item(need, ComfortStatus.UNKNOWN, "유모차 대여 정보는 확인되지만 유모차 이동 가능 여부는 충분히 확인되지 않습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 유모차 이동 가능 여부를 충분히 확인할 수 없습니다.")

    if need == NeedType.wheelchair_needed:
        accessible_path = _get(place, "accessibility", "accessible_path")
        elevator = _get(place, "accessibility", "elevator")
        wheelchair_rental = _get(place, "accessibility", "wheelchair_rental")
        if accessible_path is True or elevator is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 휠체어 이동에 도움이 되는 접근로 또는 엘리베이터가 확인됩니다.")
        if accessible_path is False and elevator is False:
            return _item(need, ComfortStatus.CONFLICT, "공식 정보에서 휠체어 이동을 위한 대체 접근수단이 없다고 확인됩니다.")
        if wheelchair_rental is True:
            return _item(need, ComfortStatus.UNKNOWN, "휠체어 대여는 확인되지만 이동 경로 정보가 충분하지 않습니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 휠체어 이동 가능 여부를 판단할 정보가 부족합니다.")

    if need == NeedType.stairs_difficult:
        accessible_path = _get(place, "accessibility", "accessible_path")
        stairs = _get(place, "accessibility", "stairs")
        slope = _get(place, "accessibility", "slope")
        elevator = _get(place, "accessibility", "elevator")
        if accessible_path is True or slope is True or elevator is True:
            return _item(need, ComfortStatus.SATISFIED, "공식 정보에서 계단을 피할 수 있는 접근로·경사로·엘리베이터 중 하나가 확인됩니다.")
        if stairs is True and accessible_path is False and elevator is False and slope is False:
            return _item(need, ComfortStatus.CONFLICT, "계단 이용이 필요하고 공식 정보에서 대체 접근수단이 없다고 확인됩니다.")
        return _item(need, ComfortStatus.UNKNOWN, "공식 자료에서 계단 우회 가능 여부를 판단할 정보가 부족합니다.")

    return _item(need, ComfortStatus.UNKNOWN, "해당 조건을 판단할 공식 정보가 없습니다.")


def evaluate_comfort(place: Dict[str, Any], needs: Iterable[NeedType]) -> ComfortResult:
    items: List[ComfortItem] = [evaluate_need(place, need) for need in needs]

    if not items:
        level = ComfortLevel.INSUFFICIENT_DATA
    elif any(item.status == ComfortStatus.CONFLICT for item in items):
        level = ComfortLevel.BURDEN_POSSIBLE
    elif all(item.status == ComfortStatus.UNKNOWN for item in items):
        level = ComfortLevel.INSUFFICIENT_DATA
    elif any(item.status == ComfortStatus.UNKNOWN for item in items):
        level = ComfortLevel.CHECK_NEEDED
    else:
        level = ComfortLevel.COMFORTABLE

    return ComfortResult(level=level, label=LEVEL_LABELS[level], items=items)
