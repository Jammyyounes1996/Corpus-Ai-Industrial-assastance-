"""RAGAS evaluation service for computing faithfulness and answer_relevancy."""

import json
from typing import Any

from loguru import logger

from backend.config.settings import get_settings


async def run_evaluation(
    question: str,
    answer: str,
    retrieved_context: str,
    judge_model: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()

    from ragas import evaluate
    from ragas.dataset_schema import SingleTurnSample
    from ragas.metrics import Faithfulness, ResponseRelevancy
    from langchain_ollama import ChatOllama, OllamaEmbeddings

    contexts = _parse_contexts(retrieved_context)
    if not contexts:
        contexts = [retrieved_context] if retrieved_context else [""]

    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=contexts,
    )

    model_name = judge_model or settings.DEFAULT_MODEL_NAME
    llm = ChatOllama(
        model=model_name,
        base_url=settings.OLLAMA_BASE_URL,
        timeout=120,
    )
    embeddings = OllamaEmbeddings(
        model=settings.OLLAMA_EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )

    result = await evaluate(
        dataset=[sample],
        metrics=[Faithfulness(), ResponseRelevancy()],
        llm=llm,
        embeddings=embeddings,
    )

    scores = {}
    if hasattr(result, "scores") and result.scores:
        row = result.scores[0] if result.scores else {}
        scores = {
            "faithfulness": row.get("faithfulness"),
            "answer_relevancy": row.get("answer_relevancy"),
        }
    elif hasattr(result, "_scores_dict"):
        d = result._scores_dict
        scores = {
            "faithfulness": d.get("faithfulness", {}).get(0),
            "answer_relevancy": d.get("answer_relevancy", {}).get(0),
        }

    logger.info(
        "RAGAS evaluation complete faithfulness={} answer_relevancy={}",
        scores.get("faithfulness"),
        scores.get("answer_relevancy"),
    )

    return {
        "faithfulness": scores.get("faithfulness"),
        "answer_relevancy": scores.get("answer_relevancy"),
        "model_used": model_name,
    }


def _parse_contexts(retrieved_context: str) -> list[str]:
    if not retrieved_context:
        return []

    try:
        data = json.loads(retrieved_context)
    except (json.JSONDecodeError, TypeError):
        return [retrieved_context]

    if isinstance(data, list):
        contexts = []
        for item in data:
            if isinstance(item, dict):
                text = item.get("excerpt") or item.get("text") or item.get("content") or json.dumps(item)
                contexts.append(text)
            elif isinstance(item, str):
                contexts.append(item)
        return contexts if contexts else [retrieved_context]

    if isinstance(data, str):
        return [data]

    return [retrieved_context]
