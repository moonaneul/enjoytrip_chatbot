from __future__ import annotations

import os
import re
import shutil
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
LANGCHAIN_AVAILABLE = True
try:
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
    from langchain_core.documents import Document
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langgraph.graph import END, START, StateGraph
except ImportError:
    # Degraded mode is only for contract/rule/mock tests in environments where
    # optional AI dependencies cannot be installed. Production requirements still
    # include LangGraph + Chroma + LangChain.
    LANGCHAIN_AVAILABLE = False

    class Document:  # minimal compatibility for structured fallback context
        def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
            self.page_content = page_content
            self.metadata = metadata or {}

from comfort import evaluate_comfort
from schemas import (
    AnswerSection,
    ChatRequest,
    ChatResponse,
    ComfortLevel,
    Facility,
    NeedType,
    PlaceCandidate,
    PlaceInfo,
    SectionItem,
    SourceInfo,
    TravelerType,
)
from travel_data import (
    TOUR_API_DEFAULT_BASE_URL,
    TourApiError,
    TravelDataService,
    make_map_search_text,
)


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Backward-compatible aliases are intentionally supported because the sample ZIP
# used base_url / EMBEDDING_MODEL while the handoff contract standardizes names.
OPENAI_API_KEY = os.getenv("API_KEY", "").strip()
BASE_URL = (os.getenv("BASE_URL") or os.getenv("base_url") or "").strip() or None
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-5-mini").strip()
EMBEDDING_MODEL_NAME = (
    os.getenv("EMBEDDING_MODEL_NAME")
    or os.getenv("EMBEDDING_MODEL")
    or "text-embedding-3-small"
).strip()

TOUR_API_SERVICE_KEY = os.getenv("TOUR_API_SERVICE_KEY", "").strip()
TOUR_API_BASE_URL = (
    os.getenv("TOUR_API_BASE_URL", "").strip() or TOUR_API_DEFAULT_BASE_URL
)
TOUR_API_USE_MOCK_WHEN_NO_KEY = os.getenv(
    "TOUR_API_USE_MOCK_WHEN_NO_KEY", "true"
).lower() in {"1", "true", "yes", "y"}
DISABLE_LLM = os.getenv("DISABLE_LLM", "false").lower() in {"1", "true", "yes", "y"}

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_PATH = str(BASE_DIR / "chroma_data")
CHROMA_COLLECTION = "family_travel_docs"

# Generic upload endpoint remains a developer-only utility. Normalized tourism
# documents use semantic sections, not this fallback fixed-size chunking path.
CHUNK_SIZE = 500
OVERLAP = 50

llm: Optional[ChatOpenAI] = None
embeddings: Optional[OpenAIEmbeddings] = None
vectorstore: Optional[Chroma] = None
prompt_template: Optional[ChatPromptTemplate] = None
rag_workflow = None
travel_service: Optional[TravelDataService] = None


class RAGState(TypedDict, total=False):
    question: str
    content_id: str
    place_name: str
    structured_context: str
    context: str
    source: str
    comfort_summary: str
    fallback_answer: str
    answer: str
    allow_llm: bool


def _has_llm_key() -> bool:
    return bool(
        OPENAI_API_KEY
        and OPENAI_API_KEY not in {"키를 입력하세요.", "YOUR_API_KEY", "changeme"}
    )


def init_prompt_templates() -> Optional[ChatPromptTemplate]:
    if not LANGCHAIN_AVAILABLE:
        return None
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "당신은 '가족과 함께하는 편안한 여행' 서비스의 설명 담당 AI입니다.\n"
                    "사실정보는 반드시 아래 [정규화된 공식 사실]을 최우선 근거로 사용하세요.\n"
                    "[RAG 검색 문맥]은 관련 설명을 고르는 보조 근거이며, 둘이 다르게 보이면 [정규화된 공식 사실]을 따르세요.\n"
                    "정규화된 공식 사실에서 '있음'인 항목을 '확인되지 않음'이라고 쓰거나, '확인되지 않음'인 항목을 있다고 단정하지 마세요.\n"
                    "자료에 없는 시설, 위치, 접근성 정보를 추측하지 마세요.\n"
                    "'없음'과 '현재 자료에서 확인되지 않음'을 구분하세요.\n"
                    "부모님 조건이면 질문과 관련된 이동·보행거리·걷기 부담·계단·경사·엘리베이터·휴식·화장실 정보를 우선 설명하세요.\n"
                    "영유아 조건이면 질문과 관련된 유모차·수유실·기저귀 교환·엘리베이터를 우선 설명하세요.\n"
                    "가족 모두 조건이면 두 조건을 통합하세요. 질문과 무관한 시설을 억지로 나열하지 마세요.\n"
                    "Comfort 판정은 [Rule Engine 결과]를 그대로 설명하고 절대 변경하지 마세요.\n"
                    "COMFORTABLE은 사용자가 이번 요청에서 선택한 조건이 충족됐다는 뜻일 뿐, 관광지 전체가 전반적으로 편하다거나 이동이 쉽다고 일반화하지 마세요.\n"
                    "주소와 시설명을 임의로 변형하지 마세요.\n"
                    "서로 별개로 확인된 시설 사실을 합쳐 공식 자료에 없는 이용방법·인과관계·동선을 새로 만들지 마세요.\n"
                    "장애인 전용 주차구역·장애인 탑승차량처럼 이용 자격이 제한될 수 있는 시설은 일반 고령자에게 바로 이용하라고 권장하지 마세요. 질문에 해당 자격이 명시되지 않았다면 '해당 이용 자격이 있는 경우'처럼 조건을 붙여 사실만 설명하세요.\n"
                    "안전이나 의료적 이용 가능성을 보장하는 표현을 하지 마세요.\n"
                    "지도 검색어를 답변 본문에서 새로 만들지 마세요. 또한 '지도 검색어는 생성 불가/제공 불가'라고 말하지 마세요. 시설별 지도 검색어는 Backend의 map_search_text 구조화 필드에서 별도로 제공됩니다.\n"
                    "정보 기준일이 자료에 있으면 짧게 알리세요.\n"
                    "답변은 프런트 상단 요약에 바로 들어가므로 핵심 결론과 가장 중요한 근거만 1~2문장으로 작성하세요. Rule Engine, Comfort 판정, enum 값, 영문 need key, 목록형 보고서, 제목형 요약을 출력하지 마세요. 상세 시설 목록은 구조화 필드에서 별도로 보여주므로 본문에서 반복 나열하지 마세요.\n\n"
                    "[정규화된 공식 사실]\n{structured_context}\n\n"
                    "[RAG 검색 문맥]\n{context}\n\n"
                    "[Rule Engine 결과]\n{comfort_summary}"
                ),
            ),
            ("user", "{question}"),
        ]
    )


def init_vectorstore() -> Optional[Chroma]:
    global vectorstore
    if not LANGCHAIN_AVAILABLE or embeddings is None:
        vectorstore = None
        return None
    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )
    return vectorstore


def extract_documents(file_path: Path) -> List[Document]:
    if not LANGCHAIN_AVAILABLE:
        raise RuntimeError("Document upload requires LangChain dependencies from requirements.txt.")
    try:
        if file_path.suffix.lower() == ".pdf":
            loader = PyMuPDFLoader(str(file_path))
        else:
            loader = TextLoader(str(file_path), encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = file_path.name
        return docs
    except Exception as exc:
        print(f"[upload] document extraction error: {exc}")
        return []


def chunk_documents(
    documents: List[Document],
    size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> List[Document]:
    if not documents:
        return []
    if not LANGCHAIN_AVAILABLE:
        raise RuntimeError("Document chunking requires LangChain dependencies.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " "],
        length_function=len,
    )
    return splitter.split_documents(documents)


def add_to_db(documents: List[Document]) -> int:
    if not documents:
        return 0
    if vectorstore is None:
        raise RuntimeError("ChromaDB is unavailable because embeddings are not configured.")
    vectorstore.add_documents(documents)
    return len(documents)


def _value_text(value: Any) -> str:
    if value is True:
        return "있음"
    if value is False:
        return "없음"
    if value is None or value == "":
        return "확인되지 않음"
    return str(value)


def build_place_documents(place: Dict[str, Any]) -> List[Document]:
    """Store one place as semantic sections so facility facts stay with the place name."""
    common_meta = {
        "content_id": str(place.get("content_id", "")),
        "place_name": str(place.get("name", "")),
        "region": str(place.get("region") or ""),
        "source": str(place.get("source", {}).get("title") or "무장애 여행 정보"),
        "updated_at": str(place.get("source", {}).get("updated_at") or ""),
    }

    basic = place.get("basic", {})
    accessibility = place.get("accessibility", {})
    baby = place.get("baby", {})
    restroom = place.get("restroom", {})
    raw = place.get("raw_details", {})

    docs = [
        Document(
            page_content=(
                f"{place.get('name')} 기본정보\n"
                f"주소: {_value_text(place.get('address'))}\n"
                f"지역: {_value_text(place.get('region'))}\n"
                f"운영시간: {_value_text(basic.get('opening_hours'))}\n"
                f"휴무: {_value_text(basic.get('closed_days'))}\n"
                f"주차: {_value_text(basic.get('parking'))}\n"
                f"개요: {_value_text(place.get('overview'))}"
            ),
            metadata={**common_meta, "section": "basic", "facility_type": ""},
        ),
        Document(
            page_content=(
                f"{place.get('name')} 접근성·고령자 정보\n"
                f"접근로: {_value_text(accessibility.get('accessible_path'))}\n"
                f"계단: {_value_text(accessibility.get('stairs'))}\n"
                f"경사로: {_value_text(accessibility.get('slope'))}\n"
                f"엘리베이터: {_value_text(accessibility.get('elevator'))}\n"
                f"휴식공간: {_value_text(accessibility.get('rest_area'))}\n"
                f"보행 관련 정보: {_value_text(accessibility.get('walking_info'))}\n"
                f"휠체어 대여: {_value_text(accessibility.get('wheelchair_rental'))}\n"
                f"원문 접근로: {_value_text(raw.get('route'))}\n"
                f"원문 출입통로: {_value_text(raw.get('exit'))}\n"
                f"원문 대중교통 접근: {_value_text(raw.get('publictransport'))}\n"
                f"원문 엘리베이터: {_value_text(raw.get('elevator'))}\n"
                f"원문 기타: {_value_text(raw.get('handicapetc'))}"
            ),
            metadata={**common_meta, "section": "mobility", "facility_type": "accessibility"},
        ),
        Document(
            page_content=(
                f"{place.get('name')} 영유아·시설 정보\n"
                f"유모차 접근: {_value_text(baby.get('stroller_access'))}\n"
                f"유모차 대여: {_value_text(baby.get('stroller_rental'))}\n"
                f"수유실: {_value_text(baby.get('nursing_room'))}\n"
                f"기저귀 교환: {_value_text(baby.get('diaper_station'))}\n"
                f"화장실: {_value_text(restroom.get('available'))}\n"
                f"장애인 화장실: {_value_text(restroom.get('accessible_restroom'))}\n"
                f"원문 수유실: {_value_text(raw.get('lactationroom'))}\n"
                f"원문 유모차: {_value_text(raw.get('stroller'))}\n"
                f"원문 영유아 기타: {_value_text(raw.get('infantsfamilyetc'))}"
            ),
            metadata={**common_meta, "section": "baby", "facility_type": "family_facility"},
        ),
    ]
    return docs


def index_place_documents(place: Dict[str, Any]) -> bool:
    if vectorstore is None:
        return False
    docs = build_place_documents(place)
    content_id = str(place.get("content_id", ""))
    ids = [f"{content_id}:basic", f"{content_id}:mobility", f"{content_id}:baby"]
    try:
        try:
            existing = vectorstore.get(where={"content_id": content_id})
            existing_ids = existing.get("ids", []) if existing else []
            if existing_ids:
                vectorstore.delete(ids=existing_ids)
        except Exception:
            pass
        vectorstore.add_documents(docs, ids=ids)
        return True
    except Exception as exc:
        # Network/provider failures in embeddings must not turn unknown facts into guesses.
        print(f"[rag] indexing skipped/fallback used: {exc}")
        return False


def _structured_context(place: Dict[str, Any]) -> str:
    return "\n\n".join(doc.page_content for doc in build_place_documents(place))


def retrieve_node(state: RAGState) -> RAGState:
    content_id = state.get("content_id", "")
    question = state.get("question", "")
    docs_with_scores = []

    if vectorstore is not None and content_id:
        try:
            docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
                question,
                k=5,
                filter={"content_id": content_id},
                score_threshold=0.20,
            )
        except Exception as exc:
            print(f"[rag] retrieval fallback: {exc}")

    if docs_with_scores:
        docs = [doc for doc, _score in docs_with_scores]
        context = "\n\n".join(doc.page_content for doc in docs)
        source = ", ".join(
            sorted({str(doc.metadata.get("source") or "무장애 여행 정보") for doc in docs})
        )
    else:
        context = state.get("structured_context", "")
        source = "한국관광공사 무장애 여행 정보"

    return {"context": context, "source": source}


def generate_node(state: RAGState) -> RAGState:
    fallback_answer = state.get(
        "fallback_answer",
        "현재 보유한 공식 자료에서는 해당 정보를 확인할 수 없습니다.",
    )

    if (
        not state.get("allow_llm", True)
        or llm is None
        or prompt_template is None
        or not state.get("context")
    ):
        return {"answer": fallback_answer}

    try:
        response = (prompt_template | llm).invoke(
            {
                "structured_context": state.get("structured_context", ""),
                "context": state.get("context", ""),
                "comfort_summary": state.get("comfort_summary", ""),
                "question": state.get("question", ""),
            }
        )
        answer = str(response.content).strip()
        return {"answer": answer or fallback_answer}
    except Exception as exc:
        print(f"[llm] generation fallback: {exc}")
        return {"answer": fallback_answer}


def _restricted_facility_facts(place: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """Return disability-only facility facts actually present for this place.

    These flags are used only to ground the generated prose.  They do not imply
    that a generic senior traveler is eligible to use the facility.
    """
    if not place:
        return {"disabled_parking": False, "disabled_vehicle": False}

    raw = place.get("raw_details", {}) or {}
    pieces: List[str] = []
    for value in raw.values():
        if value:
            pieces.append(str(value))
    access = place.get("accessibility", {}) or {}
    if access.get("walking_info"):
        pieces.append(str(access.get("walking_info")))
    blob = " ".join(pieces)

    return {
        "disabled_parking": bool(
            re.search(r"장애인\s*(?:전용\s*)?주차|장애인\s*주차구역", blob)
        ),
        "disabled_vehicle": "장애인 탑승차량" in blob,
    }


def _sanitize_answer_policy(
    answer: str,
    question: str,
    place: Optional[Dict[str, Any]] = None,
) -> str:
    """Apply deterministic grounding/policy guardrails after LLM generation.

    1) Never let the prose claim a disability-only facility that is absent from
       the normalized official facts for the current place.
    2) For a generic senior request, facilities that *are* present but may require
       eligibility are stated conditionally rather than recommended as directly
       usable.
    3) Prevent false claims that map-search text cannot be provided; the backend
       exposes it structurally via ``facilities[].map_search_text``.
    """
    text = str(answer or "").strip()
    if not text:
        return text

    text = re.sub(
        r"[^\n]*(?:지도\s*검색어)[^\n]*(?:생성|제공)[^\n]*(?:불가|못)[^\n]*",
        "",
        text,
        flags=re.I,
    )

    facts = _restricted_facility_facts(place)
    explicit_restricted_context = bool(
        re.search(r"장애인|장애 등록|장애등록|교통약자|장애인\s*주차", question or "")
    )
    recommendation = re.compile(r"고려|이용(?:하세요|을|해|하여|하면|할)|활용|권장|추천|검토")

    out: List[str] = []
    for line in text.splitlines():
        mentions_parking = bool(
            re.search(r"장애인\s*(?:전용\s*)?주차|장애인\s*주차구역", line)
        )
        mentions_vehicle = "장애인 탑승차량" in line

        # Grounding comes first: unsupported restricted facilities must not survive
        # even when the question explicitly mentions disability context.
        if mentions_vehicle and not facts["disabled_vehicle"]:
            # Mixed parking+vehicle recommendation lines can be safely rebuilt from
            # the parking fact if it is actually present; otherwise drop the line.
            if mentions_parking and facts["disabled_parking"]:
                line = "- 장애인 전용 주차구역 정보는 확인되며, 해당 이용 자격이 있는 경우에만 실제 이용 가능 여부를 확인하세요."
                mentions_vehicle = False
            else:
                continue

        if mentions_parking and not facts["disabled_parking"]:
            if mentions_vehicle and facts["disabled_vehicle"]:
                line = "- 장애인 탑승차량 정보는 확인되며, 해당 이용 자격이 있는 경우에만 실제 이용 가능 여부를 확인하세요."
                mentions_parking = False
            else:
                continue

        # If both facts are present but the LLM recommends them directly to a
        # generic senior, replace that recommendation with a fact-grounded,
        # eligibility-qualified sentence containing only facts that exist here.
        if not explicit_restricted_context and recommendation.search(line):
            names: List[str] = []
            if mentions_parking and facts["disabled_parking"]:
                names.append("장애인 전용 주차구역")
            if mentions_vehicle and facts["disabled_vehicle"]:
                names.append("장애인 탑승차량")
            if names:
                joined = "·".join(names)
                line = f"- {joined} 정보는 확인되지만, 해당 이용 자격이 있는 경우에만 실제 이용 가능 여부를 확인하세요."

        out.append(line)

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


class _FallbackRAGWorkflow:
    def invoke(self, state: RAGState) -> RAGState:
        merged: RAGState = dict(state)
        merged.update(retrieve_node(merged))
        merged.update(generate_node(merged))
        return merged


def build_rag_graph():
    if not LANGCHAIN_AVAILABLE:
        return _FallbackRAGWorkflow()
    workflow = StateGraph(RAGState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()


ENTITY_SUFFIXES = (
    "국립공원",
    "박물관",
    "미술관",
    "수목원",
    "동물원",
    "아쿠아리움",
    "테마파크",
    "해수욕장",
    "자연휴양림",
    "둘레길",
    "전망대",
    "관광지",
    "공원",
    "궁",
    "사찰",
    "시장",
    "마을",
    "광장",
    "타워",
    "폭포",
    "계곡",
    "호수",
    "등대",
    "일출봉",
    "봉",
    "섬",
)


def _strip_family_prefixes(text: str) -> str:
    return re.sub(
        r"(엄마|아빠|부모님|어머니|아버지|아기|아이|애기|가족)(랑|이랑|과|와|하고|이|가|은|는)?\s*",
        " ",
        text,
    )


def _extract_travel_target_prefix(message: str) -> Optional[str]:
    """Extract the place named before a travel/visit intent phrase.

    This is intentionally conservative and runs before the generic suffix matcher.
    It prevents queries such as "불국사 가려고 하는데 계단이 힘들어" from
    becoming the broad keyword "불국사 이 힘들어" and prevents "궁금해" from
    being mistaken for a place ending in "궁".
    """
    text = re.sub(r"[?!,.~]", " ", message)
    text = _strip_family_prefixes(text)
    text = re.sub(r"^(같이|이번에|주말에|내일|오늘)\s+", "", text.strip())
    markers = (
        "가려고", "가는데", "가볼", "가기", "가고", "방문하려", "방문할", "방문", "여행하려", "여행할"
    )
    positions = [text.find(marker) for marker in markers if text.find(marker) > 0]
    if not positions:
        return None
    candidate = text[: min(positions)].strip()
    candidate = re.sub(r"\s+", " ", candidate)
    if 2 <= len(candidate) <= 40 and not re.search(r"(알려|궁금|필요|힘들|괜찮|편하)", candidate):
        return candidate
    return None


def _extract_explicit_place_phrase(message: str) -> Optional[str]:
    quoted = re.findall(r"[\"'“”‘’]([^\"'“”‘’]{2,40})[\"'“”‘’]", message)
    if quoted:
        return quoted[0].strip()

    normalized = re.sub(r"[?!,.]", " ", message)
    normalized = _strip_family_prefixes(normalized)
    suffix = "|".join(sorted((re.escape(x) for x in ENTITY_SUFFIXES), key=len, reverse=True))
    # A suffix must finish the token. Without this guard, the "궁" in "궁금해"
    # could make the whole preceding sentence look like a palace name.
    matches = re.findall(
        rf"([가-힣A-Za-z0-9·\- ]{{1,35}}?(?:{suffix}))(?![가-힣A-Za-z0-9])",
        normalized,
    )
    if not matches:
        return None
    candidate = matches[0].strip()
    candidate = re.sub(r"^(같이|이번에|주말에|내일|오늘)\s+", "", candidate)
    return candidate or None


def _clean_place_query(message: str) -> str:
    text = re.sub(r"[?!,.~]", " ", message)
    patterns = [
        r"(엄마|아빠|부모님|어머니|아버지|아기|아이|애기|가족)(랑|이랑|과|와|하고)?",
        r"가려고\s*하는데",
        r"가려고",
        r"가볼까",
        r"가도\s*될까",
        r"가기\s*괜찮아",
        r"괜찮을까",
        r"괜찮아",
        r"어때",
        r"알려줘",
        r"알려\s*줘",
        r"있어",
        r"있는지",
        r"위치는",
        r"위치",
        r"많이\s*걸어야\s*하는지",
        r"많이\s*걸어야",
        r"계단이나\s*경사\s*정보",
        r"계단",
        r"경사",
        r"엘리베이터",
        r"수유실",
        r"기저귀\s*교환(대|할\s*곳)?",
        r"화장실",
        r"주차장",
        r"주차",
        r"유모차",
        r"휠체어",
        r"쉴\s*곳",
        r"휴식",
        r"편할까",
        r"편해",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(으로|에서|에는|은|는|이|가|을|를|에)$", "", text).strip()
    return text


def extract_search_terms(message: str) -> List[str]:
    terms: List[str] = []

    travel_target = _extract_travel_target_prefix(message)
    if travel_target:
        terms.append(travel_target)

    explicit = _extract_explicit_place_phrase(message)
    if explicit and explicit not in terms:
        terms.append(explicit)

    cleaned = _clean_place_query(message)
    # Prefer compact noun-like token fallbacks before a long cleaned sentence.
    # The old order stopped at the first broad API hit even when a later token was
    # the exact place name (e.g. "불국사").
    tokens = re.findall(r"[가-힣A-Za-z0-9·\-]{2,30}", cleaned)
    stop_tokens = {"힘들어", "힘들고", "필요해", "궁금해", "이용하고", "찾기", "중간에"}
    for token in tokens:
        if token not in stop_tokens and token not in terms:
            terms.append(token)

    if len(cleaned) >= 2 and cleaned not in terms:
        terms.append(cleaned)
    return terms[:5]


def _is_facility_followup(message: str) -> bool:
    signals = (
        "수유실",
        "화장실",
        "주차",
        "엘리베이터",
        "유모차",
        "휠체어",
        "계단",
        "경사",
        "쉴",
        "휴식",
        "기저귀",
        "많이 걸",
        "편할까",
        "선택한 장소",
    )
    return any(signal in message for signal in signals)


def _candidate_from_item(item: Dict[str, Any]) -> PlaceCandidate:
    address = " ".join(
        part for part in [str(item.get("addr1") or "").strip(), str(item.get("addr2") or "").strip()] if part
    ).strip() or None
    region = " ".join(address.split()[:2]) if address else None
    return PlaceCandidate(
        content_id=str(item.get("contentid") or item.get("contentId") or ""),
        name=str(item.get("title") or "이름 미확인"),
        address=address,
        region=region,
    )


def _dedupe_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        cid = str(item.get("contentid") or item.get("contentId") or "")
        if cid and cid not in seen:
            seen.add(cid)
            result.append(item)
    return result


def _compact_place_text(value: Any) -> str:
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", str(value or ""))
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text).lower()


def _region_title_variants(item: Dict[str, Any]) -> List[str]:
    """Return normalized title variants with a leading region token removed.

    TourAPI titles often prefix a destination with its city (e.g. ``경주 불국사``).
    This lets a direct ``불국사`` query treat that title as an exact place-name
    match without also treating unrelated records merely located in Gyeongju as
    relevant.
    """
    title = _compact_place_text(item.get("title"))
    variants = [title] if title else []
    address = str(item.get("addr1") or "")
    aliases = set()
    for token in address.split()[:3]:
        compact = _compact_place_text(token)
        if not compact:
            continue
        aliases.add(compact)
        for suffix in ("특별자치도", "특별자치시", "특별시", "광역시", "자치구", "도", "시", "군", "구"):
            if compact.endswith(suffix) and len(compact) > len(suffix):
                aliases.add(compact[: -len(suffix)])
                break
    for alias in sorted(aliases, key=len, reverse=True):
        if title.startswith(alias) and len(title) > len(alias):
            variants.append(title[len(alias):])
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(v for v in variants if v))


def _rank_place_candidates(items: List[Dict[str, Any]], term: str) -> List[Dict[str, Any]]:
    """Return only title-relevant place candidates, ordered by match quality.

    ``searchKeyword2`` can return records that are related only by region or broad
    search relevance. Those records must never become AMBIGUOUS_PLACE candidates
    for a destination-name query. If no returned title actually matches the term,
    an empty list is returned so the resolver can try another term or report
    PLACE_NOT_FOUND instead of presenting unrelated businesses/attractions.
    """
    key = _compact_place_text(term)
    if not key:
        return []

    destination_suffix_priority = {
        "해수욕장": 0,
        "관광특구": 1,
        "관광지": 2,
        "공원": 3,
        "섬": 4,
        "수목원": 5,
        "박물관": 5,
        "과학관": 5,
        "미술관": 5,
        "시장": 7,
        "도서관": 8,
        "호텔": 9,
        "리조트": 9,
    }
    content_type_priority = {
        "12": 0,  # 관광지
        "14": 1,  # 문화시설
        "28": 2,  # 레포츠
        "25": 3,  # 여행코스
        "38": 6,  # 쇼핑
        "32": 8,  # 숙박
        "39": 9,  # 음식점
    }

    def _destination_priority(title: str) -> int:
        compact = _compact_place_text(title)
        for suffix, priority in destination_suffix_priority.items():
            if compact.endswith(_compact_place_text(suffix)):
                return priority
        return 6

    def score(item: Dict[str, Any]):
        variants = _region_title_variants(item)
        best = 9
        best_title = variants[0] if variants else ""
        for title in variants:
            if title == key:
                tier = 0
            elif title.startswith(key):
                tier = 1
            elif key in title:
                # A long title merely ending in the keyword (e.g. a hotel name
                # ending in "해운대") is weaker than a destination whose name
                # begins with the requested term.
                tier = 2
            else:
                tier = 9
            if tier < best:
                best = tier
                best_title = title
        content_type = str(item.get("contenttypeid") or item.get("contentTypeId") or "")
        return (
            best,
            _destination_priority(best_title),
            content_type_priority.get(content_type, 5),
            abs(len(best_title) - len(key)),
            best_title,
        )

    ranked = sorted(items, key=score)
    relevant = [item for item in ranked if score(item)[0] < 9]
    if not relevant:
        return []

    # If exact (including region-prefixed exact) or prefix matches exist, suppress
    # weaker substring matches such as nearby hotels/farmstays containing the same
    # keyword. This keeps ambiguity prompts concise and destination-focused.
    best_tier = score(relevant[0])[0]
    if best_tier <= 1:
        relevant = [item for item in relevant if score(item)[0] == best_tier]
    return relevant


def _resolve_place(req: ChatRequest) -> Dict[str, Any]:
    assert travel_service is not None

    explicit = _extract_explicit_place_phrase(req.message)
    if req.current_place_id and _is_facility_followup(req.message) and not explicit:
        return {
            "status": "ok",
            "place": travel_service.get_place(req.current_place_id),
            "search_item": None,
        }

    all_items: List[Dict[str, Any]] = []
    used_term = None
    for term in extract_search_terms(req.message):
        try:
            items = travel_service.search_places(term, limit=100)
        except TourApiError:
            raise
        if items:
            all_items = _rank_place_candidates(_dedupe_candidates(items), term)
            used_term = term
            break

    if not all_items and req.current_place_id and not explicit:
        return {
            "status": "ok",
            "place": travel_service.get_place(req.current_place_id),
            "search_item": None,
        }

    if not all_items:
        return {"status": "not_found", "term": used_term or req.message}

    term_compact = re.sub(r"\s+", "", used_term or "").lower()
    exact = [
        item
        for item in all_items
        if re.sub(r"\s+", "", str(item.get("title") or "")).lower() == term_compact
    ]
    if len(exact) == 1:
        all_items = exact
    elif len(exact) > 1:
        all_items = exact

    if len(all_items) > 1:
        return {
            "status": "ambiguous",
            "candidates": [_candidate_from_item(item) for item in all_items[:5]],
        }

    item = all_items[0]
    content_id = str(item.get("contentid") or item.get("contentId") or "")
    if not content_id:
        return {"status": "not_found", "term": used_term or req.message}
    place = travel_service.get_place(content_id, search_item=item)
    return {"status": "ok", "place": place, "search_item": item}


def build_sections(place: Dict[str, Any], traveler_type: TravelerType) -> List[AnswerSection]:
    basic = place.get("basic", {})
    access = place.get("accessibility", {})
    baby = place.get("baby", {})
    restroom = place.get("restroom", {})

    sections: List[AnswerSection] = [
        AnswerSection(
            key="basic",
            title="기본 정보",
            items=[
                SectionItem(label="운영시간", value=_value_text(basic.get("opening_hours"))),
                SectionItem(label="휴무", value=_value_text(basic.get("closed_days"))),
                SectionItem(label="주차", value=_value_text(basic.get("parking"))),
            ],
        )
    ]

    if traveler_type in {TravelerType.senior, TravelerType.both}:
        sections.append(
            AnswerSection(
                key="mobility",
                title="이동",
                items=[
                    SectionItem(label="접근로", value=_value_text(access.get("accessible_path"))),
                    SectionItem(label="계단", value=_value_text(access.get("stairs"))),
                    SectionItem(label="경사로", value=_value_text(access.get("slope"))),
                    SectionItem(label="엘리베이터", value=_value_text(access.get("elevator"))),
                    SectionItem(label="휴식 공간", value=_value_text(access.get("rest_area"))),
                    SectionItem(label="보행 관련 정보", value=_value_text(access.get("walking_info"))),
                    SectionItem(label="휠체어 대여", value=_value_text(access.get("wheelchair_rental"))),
                    SectionItem(label="화장실", value=_value_text(restroom.get("available"))),
                ],
            )
        )

    if traveler_type in {TravelerType.baby, TravelerType.both}:
        sections.append(
            AnswerSection(
                key="baby",
                title="아이 동반",
                items=[
                    SectionItem(label="유모차 접근", value=_value_text(baby.get("stroller_access"))),
                    SectionItem(label="유모차 대여", value=_value_text(baby.get("stroller_rental"))),
                    SectionItem(label="수유실", value=_value_text(baby.get("nursing_room"))),
                    SectionItem(label="기저귀 교환", value=_value_text(baby.get("diaper_station"))),
                    SectionItem(label="엘리베이터", value=_value_text(access.get("elevator"))),
                ],
            )
        )
    return sections


def build_facilities(place: Dict[str, Any]) -> List[Facility]:
    facilities: List[Facility] = []
    name = str(place.get("name") or "")
    address = place.get("address")
    region = place.get("region")
    access = place.get("accessibility", {})
    baby = place.get("baby", {})
    restroom = place.get("restroom", {})
    basic = place.get("basic", {})
    raw = place.get("raw_details", {})

    def add(
        facility_type: str,
        facility_name: str,
        exists: Optional[bool],
        detail: Optional[str],
    ) -> None:
        if exists is not True:
            return
        facilities.append(
            Facility(
                type=facility_type,
                name=facility_name,
                parent_place=name,
                address=address,
                location_detail=detail,
                map_search_text=make_map_search_text(
                    facility_name=facility_name,
                    parent_place=name,
                    road_address=address,
                    region=region,
                    internal_facility=True,
                ),
            )
        )

    add("nursing_room", "수유실", baby.get("nursing_room"), raw.get("lactationroom"))
    add("restroom", "화장실", restroom.get("available"), raw.get("restroom"))
    add("parking", "주차장", basic.get("parking"), raw.get("parking"))
    add(
        "wheelchair_rental",
        "휠체어 대여",
        access.get("wheelchair_rental"),
        raw.get("wheelchair"),
    )
    add("stroller_rental", "유모차 대여", baby.get("stroller_rental"), raw.get("stroller"))
    add("rest_area", "휴식 공간", access.get("rest_area"), raw.get("handicapetc"))
    return facilities


NEED_FIELD_LABELS = {
    NeedType.stairs_difficult: "계단 우회",
    NeedType.walking_difficult: "걷기 부담",
    NeedType.need_nursing_room: "수유실",
    NeedType.need_diaper_station: "기저귀 교환",
    NeedType.need_elevator: "엘리베이터",
    NeedType.wheelchair_needed: "휠체어 이동",
    NeedType.restroom_important: "화장실",
    NeedType.need_rest_area: "휴식 공간",
    NeedType.stroller: "유모차",
}


def build_unknown_fields(comfort) -> List[str]:
    return [
        NEED_FIELD_LABELS[item.need]
        for item in comfort.items
        if item.status.value == "UNKNOWN"
    ]


def build_suggested_questions(
    traveler_type: TravelerType,
    place: Dict[str, Any],
) -> List[str]:
    access = place.get("accessibility", {})
    baby = place.get("baby", {})
    restroom = place.get("restroom", {})

    if traveler_type == TravelerType.senior:
        base = [
            "많이 걸어야 하는지 알려줘",
            "계단이나 경사 정보 알려줘",
            "쉴 곳 있어?",
            "화장실 위치 알려줘",
        ]
    elif traveler_type == TravelerType.baby:
        base = [
            "유모차 정보 알려줘",
            "수유실 위치 알려줘",
            "기저귀 교환할 곳 있어?",
            "엘리베이터 있어?",
        ]
    else:
        base = [
            "우리 가족 모두 이용하기 편할까?",
            "쉬는 곳과 아이 돌볼 시설 알려줘",
            "화장실 위치 알려줘",
            "엘리베이터 있어?",
        ]

    priority = []
    if traveler_type in (TravelerType.baby, TravelerType.both):
        if baby.get("nursing_room") is True:
            priority.append("수유실 위치 알려줘")
        if baby.get("diaper_station") is True:
            priority.append("기저귀 교환할 곳 있어?")
    if traveler_type in (TravelerType.senior, TravelerType.both):
        if restroom.get("available") is True:
            priority.append("화장실 위치 알려줘")
        if access.get("rest_area") is True:
            priority.append("쉴 곳 있어?")

    result = []
    for q in priority + base:
        if q not in result:
            result.append(q)
    return result[:3]


USER_NEED_LABELS = {
    NeedType.stairs_difficult: "계단·경사",
    NeedType.walking_difficult: "걷기 부담",
    NeedType.need_nursing_room: "수유실",
    NeedType.need_diaper_station: "기저귀 교환시설",
    NeedType.need_elevator: "엘리베이터",
    NeedType.wheelchair_needed: "휠체어 이동",
    NeedType.restroom_important: "화장실",
    NeedType.need_rest_area: "쉴 곳",
    NeedType.stroller: "유모차 이동",
}

ANSWER_FACILITY_KEYWORDS = (
    ("수유", "nursing_room", "수유실"),
    ("기저귀", "diaper_station", "기저귀 교환시설"),
    ("화장실", "restroom", "화장실"),
    ("휠체어", "wheelchair_rental", "휠체어 대여"),
    ("유모차", "stroller_rental", "유모차 대여"),
    ("주차", "parking", "주차장"),
    ("쉬", "rest_area", "휴식 공간"),
    ("휴식", "rest_area", "휴식 공간"),
)

ANSWER_INTERNAL_PATTERN = re.compile(
    r"Rule\s*Engine|Comfort\s*판정|최종\s*등급|SATISFIED|CONFLICT|UNKNOWN|"
    r"CHECK_NEEDED|BURDEN_POSSIBLE|INSUFFICIENT_DATA|COMFORTABLE|"
    r"need_[A-Za-z_]+|stairs_difficult|walking_difficult|stroller\s*:",
    re.I,
)
ANSWER_REPORT_PATTERN = re.compile(r"(^|\n)\s*(요약|공식 자료 기반|권장 조치|판정 결과|확인된 사실)\s*[:(]", re.I)


def _concise_structured_answer(req: ChatRequest, comfort, facilities: List[Facility]) -> str:
    """Build a deterministic 1~2 sentence user-facing summary from structured facts.

    The detailed evidence remains in comfort/sections/facilities.  This field is
    deliberately short so every client has a safe fallback and never needs to
    expose Rule Engine enums or a verbose RAG report.
    """
    question = req.message or ""
    for keyword, facility_type, label in ANSWER_FACILITY_KEYWORDS:
        if keyword in question and any(f.type == facility_type for f in facilities):
            return f"{label} 정보가 확인돼요. 자세한 위치와 이용 정보는 시설 카드에서 확인해 주세요."

    groups = {"CONFLICT": [], "UNKNOWN": [], "SATISFIED": []}
    for item in comfort.items:
        label = USER_NEED_LABELS.get(item.need, item.need.value)
        groups.setdefault(item.status.value, []).append(label)

    sentences: List[str] = []
    if groups["CONFLICT"]:
        sentences.append(f"{'·'.join(groups['CONFLICT'][:2])}은 현재 조건에서 이용이 불편할 수 있어요.")
    if groups["UNKNOWN"]:
        sentences.append(f"{'·'.join(groups['UNKNOWN'][:2])}은 공식 자료에서 아직 확인되지 않았어요.")
    if groups["SATISFIED"] and len(sentences) < 2:
        sentences.append(f"{'·'.join(groups['SATISFIED'][:2])}은 공식 정보에서 확인됐어요.")
    if not sentences:
        sentences.append("공식 여행 정보를 확인했어요.")
    return " ".join(sentences[:2])


def _finalize_user_answer(generated: str, req: ChatRequest, comfort, facilities: List[Facility]) -> str:
    """Return the deterministic user-facing summary.

    The RAG/LLM result is still produced upstream for the existing architecture,
    but the public ``answer`` field is intentionally derived from normalized
    structured facts so UI length and terminology cannot drift between runs.
    """
    return _concise_structured_answer(req, comfort, facilities)


def build_fallback_answer(place: Dict[str, Any], comfort) -> str:
    prefix = ""
    if "Mock Fixture" in str(place.get("source", {}).get("title", "")):
        prefix = "[개발용 Mock 데이터] "

    if comfort.level == ComfortLevel.BURDEN_POSSIBLE:
        body = "선택한 조건 중 이용 부담이 될 수 있는 항목이 확인됩니다."
    elif comfort.level == ComfortLevel.INSUFFICIENT_DATA:
        body = "선택한 조건을 판단할 공식 정보가 충분하지 않습니다."
    elif comfort.level == ComfortLevel.CHECK_NEEDED:
        body = "확인된 정보와 확인되지 않은 정보가 함께 있어 방문 전 추가 확인이 필요합니다."
    else:
        body = "선택한 조건은 현재 확보한 공식 정보에서 확인됩니다."
    return prefix + body


def _comfort_summary(comfort) -> str:
    lines = [f"최종 등급: {comfort.level.value} / {comfort.label}"]
    for item in comfort.items:
        lines.append(f"- {item.need.value}: {item.status.value} / {item.reason}")
    return "\n".join(lines)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm, embeddings, vectorstore, prompt_template, rag_workflow, travel_service

    print("[startup] family travel backend initializing")
    travel_service = TravelDataService(
        data_dir=DATA_DIR,
        service_key=TOUR_API_SERVICE_KEY,
        base_url=TOUR_API_BASE_URL,
        use_mock_when_no_key=TOUR_API_USE_MOCK_WHEN_NO_KEY,
    )

    if LANGCHAIN_AVAILABLE and _has_llm_key() and not DISABLE_LLM:
        llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=BASE_URL,
        )
        embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            api_key=OPENAI_API_KEY,
            base_url=BASE_URL,
        )
    else:
        llm = None
        embeddings = None

    init_vectorstore()
    prompt_template = init_prompt_templates()
    rag_workflow = build_rag_graph()

    mode = "REAL TourAPI" if travel_service.api_ready else (
        "MOCK TourAPI" if travel_service.mock_mode else "NO TourAPI"
    )
    print(f"[startup] ready - {mode}, collection={CHROMA_COLLECTION}")
    yield

    print("[shutdown] closing clients; persistent cache is retained")
    if vectorstore is not None and hasattr(vectorstore, "_client"):
        try:
            vectorstore._client.close()
        except Exception:
            pass


app = FastAPI(title="Family Comfort Travel Chatbot Backend", lifespan=lifespan)


def setup_cors(app_: FastAPI):
    app_.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )


setup_cors(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    payload = ChatResponse(
        success=False,
        answer="요청 형식을 확인해 주세요.",
        error={"code": "INVALID_REQUEST", "message": str(exc.errors())},
    )
    return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))


@app.get("/health")
def health():
    mode = "uninitialized"
    if travel_service is not None:
        mode = "real" if travel_service.api_ready else ("mock" if travel_service.mock_mode else "disabled")
    return {
        "success": True,
        "tour_api_mode": mode,
        "rag_collection": CHROMA_COLLECTION,
        "llm_configured": llm is not None,
        "langchain_available": LANGCHAIN_AVAILABLE,
    }


# Kept only for the original CORS exercise / developer verification.
@app.post("/simpleparam")
def simple_param(message: str = Form(...)):
    return {
        "type": "simple_request",
        "message": f"받은 메시지: {message}",
        "preflight": "불필요 (application/x-www-form-urlencoded)",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if travel_service is None or rag_workflow is None:
        return ChatResponse(
            success=False,
            answer="서버 초기화가 완료되지 않았습니다.",
            error={"code": "INTERNAL_ERROR", "message": "Backend is not initialized."},
        )

    try:
        resolved = _resolve_place(req)
    except TourApiError as exc:
        return ChatResponse(
            success=False,
            answer="관광정보 API를 호출하는 중 문제가 발생했습니다.",
            error={"code": "TOUR_API_ERROR", "message": str(exc)},
        )
    except Exception as exc:
        return ChatResponse(
            success=False,
            answer="관광지 정보를 처리하는 중 문제가 발생했습니다.",
            error={"code": "INTERNAL_ERROR", "message": str(exc)},
        )

    if resolved["status"] == "not_found":
        return ChatResponse(
            success=False,
            answer="현재 공식 관광정보에서 해당 장소를 찾지 못했습니다. 관광지명과 지역을 함께 입력해 주세요.",
            error={
                "code": "PLACE_NOT_FOUND",
                "message": f"No place matched: {resolved.get('term')}",
            },
        )

    if resolved["status"] == "ambiguous":
        return ChatResponse(
            success=False,
            answer="검색된 관련 장소가 여러 곳 있어 정확한 장소를 확인해야 해요.",
            error={
                "code": "AMBIGUOUS_PLACE",
                "message": "Multiple places matched the supplied name.",
            },
            candidates=resolved["candidates"],
        )

    place = resolved["place"]
    if not place or not place.get("content_id"):
        return ChatResponse(
            success=False,
            answer="관광지는 찾았지만 현재 보유한 공식 상세자료를 확인할 수 없습니다.",
            error={
                "code": "NO_OFFICIAL_DATA",
                "message": "Normalized official data is empty.",
            },
        )

    comfort = evaluate_comfort(place, req.needs)
    sections = build_sections(place, req.traveler_type)
    facilities = build_facilities(place)
    fallback_answer = build_fallback_answer(place, comfort)

    # On-demand indexing. Mock fixture mode intentionally avoids external embedding
    # calls so development data cannot consume provider quota or look verified.
    indexed = False if travel_service.mock_mode else index_place_documents(place)
    structured_context = _structured_context(place)

    initial_state: RAGState = {
        "question": req.message,
        "content_id": str(place["content_id"]),
        "place_name": str(place.get("name") or ""),
        "structured_context": structured_context,
        "comfort_summary": _comfort_summary(comfort),
        "fallback_answer": fallback_answer,
        # Mock fixture must never be presented as if it were verified public data.
        "allow_llm": bool(
            llm is not None
            and not travel_service.mock_mode
            and indexed
        ),
    }
    try:
        final_state = rag_workflow.invoke(initial_state)
        answer = final_state.get("answer") or fallback_answer
    except Exception as exc:
        print(f"[rag] graph fallback: {exc}")
        answer = fallback_answer

    answer = _sanitize_answer_policy(answer, req.message, place)
    answer = _finalize_user_answer(answer, req, comfort, facilities)

    source = place.get("source", {})
    source_info = SourceInfo(
        organization=str(source.get("organization") or "한국관광공사"),
        title=str(source.get("title") or "무장애 여행 정보"),
        updated_at=source.get("updated_at"),
    )

    return ChatResponse(
        success=True,
        answer=answer,
        place=PlaceInfo(
            content_id=str(place["content_id"]),
            name=str(place.get("name") or ""),
            address=place.get("address"),
            region=place.get("region"),
        ),
        comfort=comfort,
        sections=sections,
        facilities=facilities,
        unknown_fields=build_unknown_fields(comfort),
        sources=[source_info],
        suggested_questions=build_suggested_questions(req.traveler_type, place),
    )


# Developer/assignment verification endpoint. Front-End should not expose it.
@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    allowed_extensions = {".txt", ".md", ".pdf"}
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in allowed_extensions:
        return {
            "success": False,
            "message": f"지원하지 않는 파일 형식입니다. ({', '.join(sorted(allowed_extensions))} 만 허용)",
        }
    try:
        safe_name = Path(file.filename or "upload.txt").name
        save_path = DATA_DIR / safe_name
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        docs = extract_documents(save_path)
        if not docs:
            return {"success": False, "message": "파일 내용이 없거나 읽을 수 없습니다."}
        chunks = chunk_documents(docs)
        chunks_added = add_to_db(chunks)
        return {
            "success": True,
            "message": f"'{safe_name}' 업로드 완료! ({chunks_added}개 청크 추가)",
            "chunks_added": chunks_added,
        }
    except Exception as exc:
        return {"success": False, "message": f"파일 처리 중 오류 발생: {exc}"}


# Explicit developer reset: only the vector collection is cleared.
# TourAPI normalized/search cache under data/cache is intentionally retained.
@app.post("/reset-db")
def reset_db():
    try:
        if vectorstore is not None:
            all_ids = vectorstore.get().get("ids", [])
            if all_ids:
                vectorstore.delete(ids=all_ids)
        return {
            "success": True,
            "message": "family_travel_docs 벡터 데이터가 초기화되었습니다. TourAPI 로컬 캐시는 유지됩니다.",
        }
    except Exception as exc:
        return {"success": False, "message": f"DB 초기화 중 오류 발생: {exc}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
