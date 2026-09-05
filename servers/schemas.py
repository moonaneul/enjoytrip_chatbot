from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class TravelerType(str, Enum):
    senior = "senior"
    baby = "baby"
    both = "both"


class NeedType(str, Enum):
    stairs_difficult = "stairs_difficult"
    walking_difficult = "walking_difficult"
    need_nursing_room = "need_nursing_room"
    need_diaper_station = "need_diaper_station"
    need_elevator = "need_elevator"
    wheelchair_needed = "wheelchair_needed"
    restroom_important = "restroom_important"
    need_rest_area = "need_rest_area"
    stroller = "stroller"


class ErrorCode(str, Enum):
    PLACE_NOT_FOUND = "PLACE_NOT_FOUND"
    AMBIGUOUS_PLACE = "AMBIGUOUS_PLACE"
    TOUR_API_ERROR = "TOUR_API_ERROR"
    RAG_ERROR = "RAG_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    NO_OFFICIAL_DATA = "NO_OFFICIAL_DATA"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ComfortStatus(str, Enum):
    SATISFIED = "SATISFIED"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


class ComfortLevel(str, Enum):
    BURDEN_POSSIBLE = "BURDEN_POSSIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CHECK_NEEDED = "CHECK_NEEDED"
    COMFORTABLE = "COMFORTABLE"


class ComfortItem(BaseModel):
    need: NeedType
    status: ComfortStatus
    reason: str


class ComfortResult(BaseModel):
    level: ComfortLevel
    label: str
    items: List[ComfortItem] = Field(default_factory=list)


class PlaceInfo(BaseModel):
    content_id: str
    name: str
    address: Optional[str] = None
    region: Optional[str] = None


class SectionItem(BaseModel):
    label: str
    value: str


class AnswerSection(BaseModel):
    key: str
    title: str
    items: List[SectionItem] = Field(default_factory=list)


class Facility(BaseModel):
    type: str
    name: str
    parent_place: str
    address: Optional[str] = None
    location_detail: Optional[str] = None
    map_search_text: Optional[str] = None


class SourceInfo(BaseModel):
    organization: str
    title: str
    updated_at: Optional[str] = None


class PlaceCandidate(BaseModel):
    content_id: str
    name: str
    address: Optional[str] = None
    region: Optional[str] = None


class ErrorInfo(BaseModel):
    code: ErrorCode
    message: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    traveler_type: TravelerType
    needs: List[NeedType] = Field(default_factory=list)
    current_place_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    success: bool
    answer: str
    place: Optional[PlaceInfo] = None
    comfort: Optional[ComfortResult] = None
    sections: List[AnswerSection] = Field(default_factory=list)
    facilities: List[Facility] = Field(default_factory=list)
    unknown_fields: List[str] = Field(default_factory=list)
    sources: List[SourceInfo] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    candidates: List[PlaceCandidate] = Field(default_factory=list)
