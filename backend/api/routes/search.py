from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from backend.core.retrieval.qdrant_client import qdrant_retriever

router = APIRouter(prefix="/api", tags=["Search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    file_type: str | None = Field(default=None)


class SearchResult(BaseModel):
    chunk_text: str
    file_id: str
    file_type: str
    chunk_index: int
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]


@router.post("/search", response_model=SearchResponse)
async def hybrid_search(request: SearchRequest) -> SearchResponse:
    try:
        logger.info("Search query='{}'", request.query)

        raw_results = await qdrant_retriever.hybrid_query(
            query_text=request.query,
            limit=request.top_k,
            file_type_filter=request.file_type,
        )

        results = []
        for r in raw_results:
            payload = r.get("payload", {})
            results.append(SearchResult(
                chunk_text=payload.get("chunk_text", ""),
                file_id=str(payload.get("file_id", "")),
                file_type=payload.get("file_type", "unknown"),
                chunk_index=int(payload.get("chunk_index", 0)),
                score=round(r.get("score", 0.0), 4),
            ))

        return SearchResponse(query=request.query, total=len(results), results=results)

    except Exception as exc:
        logger.exception("Search failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc))