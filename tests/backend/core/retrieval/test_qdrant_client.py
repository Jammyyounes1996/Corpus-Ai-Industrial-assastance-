from unittest.mock import MagicMock, patch

from backend.core.retrieval.qdrant_client import QdrantRetriever


def test_tokenize_for_bm25():
    retriever = QdrantRetriever()
    sparse = retriever.tokenize_for_bm25("hello world hello")

    assert len(sparse) == 2
    assert sparse[hash("hello") & 0xFFFFFFFF] == 2.0
    assert sparse[hash("world") & 0xFFFFFFFF] == 1.0


def test_tokenize_empty():
    retriever = QdrantRetriever()
    sparse = retriever.tokenize_for_bm25("")
    assert len(sparse) == 0


def test_ensure_collection_exists():
    retriever = QdrantRetriever()

    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = "industrial_assistant"
    mock_client.get_collections.return_value = MagicMock(collections=[mock_collection])

    retriever._client = mock_client
    retriever.ensure_collection()

    mock_client.create_collection.assert_not_called()


def test_ensure_collection_creates():
    retriever = QdrantRetriever()

    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])

    retriever._client = mock_client
    retriever.ensure_collection()

    mock_client.create_collection.assert_called_once()
