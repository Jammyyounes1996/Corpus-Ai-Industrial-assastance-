def normalize_groundx_result(result: dict) -> dict:
    return {
        "item_id": f"groundx_{result['chunk_id']}",
        "source_type": "groundx",
        "content": result.get("content", ""),
        "score": result.get("score", 0.0),
        "file_name": result.get("file_name", ""),
        "file_id": None,
        "chunk_id": str(result.get("chunk_id", "")),
    }


def normalize_qdrant_result(result: dict) -> dict:
    payload = result.get("payload", {})
    return {
        "item_id": f"qdrant_{result['id']}",
        "source_type": "qdrant",
        "content": payload.get("content", ""),
        "score": result.get("score", 0.0),
        "file_name": payload.get("file_name", ""),
        "file_id": payload.get("file_id"),
        "chunk_id": str(result.get("id", "")),
    }


def normalize_ocr_result(result: dict) -> dict:
    """OCR results are already normalized - pass through unchanged."""
    return result
