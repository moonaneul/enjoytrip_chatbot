from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi.testclient import TestClient

import main


BASE_DIR = Path(__file__).resolve().parent
TEST_CASES = json.loads((BASE_DIR / "test_cases.json").read_text(encoding="utf-8"))


def _find_facility(payload: Dict[str, Any], facility_type: str) -> Dict[str, Any] | None:
    for facility in payload.get("facilities", []):
        if facility.get("type") == facility_type:
            return facility
    return None


def run_manual_checks() -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    previous_place_id = None

    with TestClient(main.app) as client:
        for case in TEST_CASES:
            request = dict(case["request"])
            if case["id"] == "facility_location" and previous_place_id:
                request["current_place_id"] = previous_place_id

            response = client.post("/chat", json=request)
            payload = response.json()
            expected = case.get("expected", {})

            checks: Dict[str, bool] = {}
            checks["http_contract"] = response.status_code in {200, 422}
            checks["success"] = payload.get("success") == expected.get("success")

            if expected.get("place_name"):
                checks["place_name"] = (
                    (payload.get("place") or {}).get("name") == expected["place_name"]
                )

            if expected.get("comfort_level"):
                checks["comfort_level"] = (
                    (payload.get("comfort") or {}).get("level")
                    == expected["comfort_level"]
                )

            if expected.get("error_code"):
                checks["error_code"] = (
                    (payload.get("error") or {}).get("code") == expected["error_code"]
                )

            # Additional domain-specific regression checks.
            if case["id"] == "unknown_nursing":
                nursing = None
                for item in (payload.get("comfort") or {}).get("items", []):
                    if item.get("need") == "need_nursing_room":
                        nursing = item
                        break
                checks["unknown_not_false"] = (
                    nursing is not None and nursing.get("status") == "UNKNOWN"
                )
                checks["no_hallucinated_facility"] = (
                    _find_facility(payload, "nursing_room") is None
                )

            if case["id"] == "ambiguous":
                checks["candidate_returned"] = len(payload.get("candidates", [])) >= 2

            if case["id"] == "baby_facility":
                facility = _find_facility(payload, "nursing_room")
                checks["facility_structured"] = facility is not None
                checks["map_search_text"] = bool(
                    facility and facility.get("map_search_text")
                )
                if payload.get("place"):
                    previous_place_id = payload["place"]["content_id"]

            if case["id"] == "facility_location":
                facility = _find_facility(payload, "nursing_room")
                checks["followup_same_place"] = (
                    (payload.get("place") or {}).get("content_id")
                    == request.get("current_place_id")
                )
                checks["facility_structured"] = facility is not None

            rows.append(
                {
                    "id": case["id"],
                    "persona": case["persona"],
                    "passed": all(checks.values()),
                    "checks": json.dumps(checks, ensure_ascii=False),
                    "answer": payload.get("answer"),
                    "error_code": (payload.get("error") or {}).get("code"),
                }
            )

    df = pd.DataFrame(rows)
    out = BASE_DIR / "manual_eval_results.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    return df


def run_ragas() -> pd.DataFrame:
    """
    Run only when a real LLM/embedding provider is configured and outbound network is available.
    The mock TourAPI fixture is acceptable as a retrieval fixture, but RAGAS itself still needs
    evaluator LLM/embeddings.
    """
    if not main.LANGCHAIN_AVAILABLE:
        raise RuntimeError(
            "LangChain/RAGAS runtime dependencies are unavailable. "
            "Create a fresh .venv and install requirements.txt before running --ragas."
        )
    if not main.OPENAI_API_KEY:
        raise RuntimeError("API_KEY is not configured; RAGAS evaluator cannot run.")

    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import AnswerRelevancy, ContextPrecision, Faithfulness, LLMContextRecall

    evaluator_llm = ChatOpenAI(
        model=main.GPT_MODEL,
        api_key=main.OPENAI_API_KEY,
        base_url=main.BASE_URL,
    )
    evaluator_embeddings = OpenAIEmbeddings(
        model=main.EMBEDDING_MODEL_NAME,
        api_key=main.OPENAI_API_KEY,
        base_url=main.BASE_URL,
    )

    rows = []
    with TestClient(main.app) as client:
        for case in TEST_CASES:
            if case["id"] in {"ambiguous", "not_found"}:
                continue
            response = client.post("/chat", json=case["request"])
            payload = response.json()
            if not payload.get("success") or not payload.get("place"):
                continue
            content_id = payload["place"]["content_id"]
            place = main.travel_service.get_place(content_id)
            rows.append(
                {
                    "user_input": case["request"]["message"],
                    "response": payload["answer"],
                    "retrieved_contexts": [main._structured_context(place)],
                    "reference": case["ground_truth"],
                }
            )

    if not rows:
        raise RuntimeError("No successful cases available for RAGAS.")

    dataset = EvaluationDataset.from_list(rows)
    metrics = [
        Faithfulness(llm=evaluator_llm),
        AnswerRelevancy(llm=evaluator_llm),
        LLMContextRecall(llm=evaluator_llm),
        ContextPrecision(llm=evaluator_llm),
    ]
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    df = result.to_pandas()
    df.to_csv(BASE_DIR / "ragas_eval_results.csv", index=False, encoding="utf-8-sig")
    return df


def main_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ragas",
        action="store_true",
        help="Run LLM-based RAGAS after deterministic manual checks.",
    )
    args = parser.parse_args()

    manual = run_manual_checks()
    print("=== Manual travel-domain checks ===")
    print(manual[["id", "persona", "passed", "error_code"]].to_string(index=False))
    print(f"manual pass: {int(manual['passed'].sum())}/{len(manual)}")

    if args.ragas:
        print("\n=== RAGAS ===")
        ragas_df = run_ragas()
        cols = [
            c
            for c in [
                "user_input",
                "faithfulness",
                "answer_relevancy",
                "context_recall",
                "context_precision",
            ]
            if c in ragas_df.columns
        ]
        print(ragas_df[cols].to_string(index=False))


if __name__ == "__main__":
    main_cli()
