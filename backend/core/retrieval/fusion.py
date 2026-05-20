from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    *rankings: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Combine multiple ranked result lists using Reciprocal Rank Fusion.

    Each ranking item must have an "id" key and optionally a "payload" key.

    Args:
        *rankings: Variable number of ranked result lists.
        k: RRF constant (default 60). Higher k dampens the impact of top ranks.

    Returns:
        Single fused ranking sorted by combined RRF score (descending).
    """
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}

    for ranking in rankings:
        for rank, item in enumerate(ranking):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
            if item_id not in payloads and "payload" in item:
                payloads[item_id] = item["payload"]

    fused = [
        {
            "id": item_id,
            "score": score,
            "payload": payloads.get(item_id, {}),
        }
        for item_id, score in scores.items()
    ]
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused
