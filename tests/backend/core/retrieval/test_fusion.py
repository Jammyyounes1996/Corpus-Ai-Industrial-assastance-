import pytest
from unittest.mock import MagicMock, patch

from backend.core.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_basic():
    ranking1 = [
        {"id": "a", "score": 0.9, "payload": {"text": "doc a"}},
        {"id": "b", "score": 0.8, "payload": {"text": "doc b"}},
    ]
    ranking2 = [
        {"id": "b", "score": 0.95, "payload": {"text": "doc b"}},
        {"id": "c", "score": 0.7, "payload": {"text": "doc c"}},
    ]

    result = reciprocal_rank_fusion(ranking1, ranking2, k=60)

    assert len(result) == 3

    ids = [r["id"] for r in result]
    assert "b" in ids
    assert "a" in ids
    assert "c" in ids

    b_item = next(r for r in result if r["id"] == "b")
    assert b_item["score"] > 0
    assert b_item["payload"]["text"] == "doc b"


def test_rrf_single_ranking():
    ranking = [
        {"id": "x", "payload": {"text": "doc x"}},
        {"id": "y", "payload": {"text": "doc y"}},
    ]

    result = reciprocal_rank_fusion(ranking, k=60)

    assert len(result) == 2
    assert result[0]["score"] > result[1]["score"]


def test_rrf_empty():
    result = reciprocal_rank_fusion(k=60)
    assert result == []


def test_rrf_k_parameter():
    ranking = [{"id": "a"}]
    result_k1 = reciprocal_rank_fusion(ranking, k=1)
    result_k100 = reciprocal_rank_fusion(ranking, k=100)

    assert result_k1[0]["score"] > result_k100[0]["score"]
