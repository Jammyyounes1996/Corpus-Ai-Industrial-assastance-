"""Reciprocal Rank Fusion for multi-source retrieval."""

from typing import Any


def reciprocal_rank_fusion(
    *results: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Combine ranked retrieval result sets using Reciprocal Rank Fusion.

    Each input list is treated as an ordered ranking where rank starts at 1.
    Items are merged by ``item_id`` and accumulate score = ``1 / (k + rank)``
    across all lists.
    """
    scores: dict[str, float] = {}
    items: dict[str, dict[str, Any]] = {}

    for result_list in results:
        for rank, item in enumerate(result_list, start=1):
            item_id = str(item.get("item_id") or item.get("id") or "")
            if not item_id:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank))
            if item_id not in items:
                items[item_id] = item.copy()

    fused: list[dict[str, Any]] = []
    for item_id, score in sorted(scores.items(), key=lambda pair: pair[1], reverse=True):
        merged = items[item_id].copy()
        merged["score"] = score
        merged["rrf_score"] = score
        fused.append(merged)
    return fused


def rrf_fusion(
    result_lists: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Combine a list of rankings using Reciprocal Rank Fusion.

    Signature intentionally matches legacy usage in retrieval tests.
    """
    normalized: list[list[dict[str, Any]]] = []
    for result_list in result_lists:
        normalized_list: list[dict[str, Any]] = []
        for item in result_list:
            normalized_item = item.copy()
            normalized_item["item_id"] = str(item.get("item_id") or item.get("id") or item.get("doc_id") or "")
            normalized_list.append(normalized_item)
        normalized.append(normalized_list)

    return reciprocal_rank_fusion(*normalized, k=k)
