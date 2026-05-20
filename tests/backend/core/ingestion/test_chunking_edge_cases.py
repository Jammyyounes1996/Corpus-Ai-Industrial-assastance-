"""Tests for chunking edge cases."""
import pytest

from backend.core.ingestion.chunking import chunk_text


def test_chunk_invalid_overlap_negative():
    """Test that negative overlap_fraction raises ValueError."""
    text = " ".join([f"word{i}" for i in range(500)])

    with pytest.raises(ValueError, match="overlap_fraction must be in range"):
        chunk_text(text, overlap_fraction=-0.1)


def test_chunk_valid_overlap_zero():
    """Test that zero overlap_fraction is valid (no overlap)."""
    text = " ".join([f"word{i}" for i in range(500)])

    chunks = chunk_text(text, overlap_fraction=0.0)
    # With zero overlap, chunks should be clean without overlap
    assert len(chunks) > 1


def test_chunk_invalid_overlap_one():
    """Test that overlap_fraction of 1.0 raises ValueError."""
    text = " ".join([f"word{i}" for i in range(500)])

    with pytest.raises(ValueError, match="overlap_fraction must be in range"):
        chunk_text(text, overlap_fraction=1.0)


def test_chunk_invalid_overlap_greater_than_one():
    """Test that overlap_fraction > 1.0 raises ValueError."""
    text = " ".join([f"word{i}" for i in range(500)])

    with pytest.raises(ValueError, match="overlap_fraction must be in range"):
        chunk_text(text, overlap_fraction=1.5)


def test_chunk_valid_overlap_boundary():
    """Test that overlap_fraction just under 1.0 works."""
    text = " ".join([f"word{i}" for i in range(500)])

    chunks = chunk_text(text, overlap_fraction=0.99)
    assert len(chunks) > 1


def test_chunk_valid_overlap_small():
    """Test that small overlap_fraction works."""
    text = " ".join([f"word{i}" for i in range(500)])

    chunks = chunk_text(text, overlap_fraction=0.01)
    assert len(chunks) > 1
