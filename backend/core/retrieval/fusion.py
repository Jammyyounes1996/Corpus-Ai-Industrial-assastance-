"""Compatibility wrapper for reciprocal rank fusion."""

from typing import Any

from backend.agent.utils.rrf_fusion import rrf_fusion


def reciprocal_rank_fusion(*rankings: list[dict[str, Any]], k: int = 60) -> list[dict[str, Any]]:
    """Fuse zero or more ranking lists into a single ranked list."""
    if not rankings:
        return []
    return rrf_fusion(list(rankings), k=k)


__all__ = ["reciprocal_rank_fusion"]
