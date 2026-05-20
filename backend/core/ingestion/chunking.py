from __future__ import annotations

import tiktoken


def _get_encoder() -> tiktoken.Encoding:
    """Get the cl100k_base tokenizer (used by nomic-embed-text)."""
    return tiktoken.get_encoding("cl100k_base")


def chunk_text(
    text: str,
    *,
    max_tokens: int = 500,
    overlap_fraction: float = 0.1,
) -> list[str]:
    """Split text into overlapping token-based chunks.

    Args:
        text: The full text to chunk.
        max_tokens: Target tokens per chunk.
        overlap_fraction: Fraction of max_tokens to overlap between chunks.

    Returns:
        List of text chunks.

    Raises:
        ValueError: If overlap_fraction is not in valid range [0, 1).
    """
    if overlap_fraction < 0 or overlap_fraction >= 1.0:
        raise ValueError(
            f"overlap_fraction must be in range [0, 1), got {overlap_fraction}"
        )

    if not text.strip():
        return []

    enc = _get_encoder()
    tokens = enc.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    overlap = int(max_tokens * overlap_fraction)
    stride = max_tokens - overlap

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        start += stride

    return chunks
