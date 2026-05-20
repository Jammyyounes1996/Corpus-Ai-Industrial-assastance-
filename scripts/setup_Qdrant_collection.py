"""Create the Qdrant collection for the Industrial AI Assistant."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, SparseVectorParams, VectorParams

from backend.config.settings import get_settings
from backend.utils.logging import configure_logging

from loguru import logger


COLLECTION_NAME = "industrial_assistant"
VECTOR_SIZE = 768


def create_collection() -> None:
    """Create the Qdrant collection with dense and sparse vector support."""
    configure_logging()
    settings = get_settings()

    logger.info("Connecting to Qdrant at {}", settings.QDRANT_URL)

    try:
        client = QdrantClient(url=settings.QDRANT_URL)
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME in collection_names:
            logger.info("Collection '{}' already exists, recreating...", COLLECTION_NAME)
            client.delete_collection(collection_name=COLLECTION_NAME)

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(),
            },
        )

        logger.info(
            "Collection '{}' created with {}d dense + sparse vectors",
            COLLECTION_NAME,
            VECTOR_SIZE,
        )

    except Exception as exc:
        logger.error("Failed to create Qdrant collection: {}", exc)
        logger.info("Ensure Qdrant is running: docker-compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    create_collection()
