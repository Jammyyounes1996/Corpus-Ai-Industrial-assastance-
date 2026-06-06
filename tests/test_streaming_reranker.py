import asyncio

from backend.agent.streaming import deduplicate_sources
from backend.core.retrieval.reranker import reranker


def test_deduplicate_sources_by_source_type():
    sources = [
        {"source": "doc-a", "type": "groundx", "score": 0.9},
        {"source": "doc-a", "type": "groundx", "score": 0.8},
        {"source": "doc-b", "type": "qdrant", "score": 0.7},
        {"source": "doc-b", "type": "qdrant", "score": 0.6},
        {"source": "doc-c", "type": "ocr", "score": 0.5},
    ]

    result = deduplicate_sources(sources)

    assert len(result) == 3


def test_deduplicate_sources_max_display():
    sources = [
        {"source": "doc-1", "type": "groundx"},
        {"source": "doc-2", "type": "groundx"},
        {"source": "doc-3", "type": "qdrant"},
        {"source": "doc-4", "type": "qdrant"},
        {"source": "doc-5", "type": "ocr"},
        {"source": "doc-6", "type": "ocr"},
    ]

    result = deduplicate_sources(sources, max_display=3)

    assert len(result) == 3


def test_deduplicate_sources_no_file_id_key():
    sources = [
        {"source": "a", "type": "groundx"},
        {"source": "a", "type": "groundx"},
        {"source": "b", "type": "qdrant"},
    ]

    result = deduplicate_sources(sources)

    assert len(result) == 2


def test_reranker_is_async():
    assert asyncio.iscoroutinefunction(reranker.rerank) is True
