from __future__ import annotations

import time
from typing import Any
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.state import AgentState
from backend.database.crud import get_ocr_result_by_file_id


async def ocr_node(state: AgentState, session: AsyncSession) -> AgentState:
    """Retrieve OCR text for attached files from database storage.

    Args:
        state: Current agent state.
        session: Active async database session.

    Returns:
        AgentState: Updated state including `ocr_results`.

    Raises:
        AgentError: If state is invalid for OCR retrieval.
        RetrievalError: If OCR data retrieval fails.
    """
    start_time = time.perf_counter()
    logger.info(f"Executing ocr_node for query: {state.get('query', '')[:50]}")

    answer_mode = state.get("answer_mode")
    if answer_mode is not None and answer_mode in ("groundx", "audio", "general"):
        return {"ocr_results": [], "ocr_called": False}

    try:
        attached_files = state.get("attached_files", [])

        if not attached_files:
            return {"ocr_results": [], "ocr_called": False}

        ocr_results: list[dict[str, Any]] = []
        for file_id in attached_files:
            ocr_result = await get_ocr_result_by_file_id(session, file_id)
            if ocr_result:
                ocr_results.append(
                    {
                        "item_id": f"ocr_{file_id}",
                        "source_type": "ocr",
                        "content": ocr_result.extracted_text,
                        "file_id": file_id,
                        "file_name": "",
                        "chunk_id": f"ocr_{file_id}",
                        "score": 1.0,
                    }
                )

        return {"ocr_results": ocr_results, "ocr_called": True}
    except Exception as exc:
        logger.error(f"ocr_node failed: {exc}")
        raise
