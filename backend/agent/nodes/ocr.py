from __future__ import annotations

import re
import time
from collections import Counter
from typing import Any
from pathlib import Path
import mimetypes

from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.state import AgentState
from backend.core.ingestion.image_processor import image_processor
from backend.database import crud


NO_READABLE_TEXT_MESSAGE = "No readable text was found in the image."

_BAD_OCR_SENTINELS = frozenset({
    "[NO TEXT DETECTED]",
    "[OCR FAILED - TEXT UNAVAILABLE]",
})

_BAD_OCR_SUBSTRINGS = (
    "please upload",
    "please provide",
    "upload an image",
    "provide an image",
    "i can't see",
    "i cannot see",
    "i cannot read",
    "no image attached",
    "no image provided",
    "image not found",
    "unable to process",
    "mostly composed of single",
    "very short words",
    "single characters",
    "composed of single",
    "no readable text",
    "no text could be",
    "does not contain",
    "i'm unable to",
    "i am unable to",
    "cannot determine",
    "unable to extract",
    "no meaningful text",
    "no legible text",
    "no visible text",
    "text is not clear",
    "text is unclear",
    "could not detect",
)

_PROMPT_ECHO_PHRASES = (
    "extract all text",
    "extract all visible",
    "extract text from this image",
    "ocr the following",
    "perform ocr",
)

_MAX_WORD_REPEAT_RATIO = 0.6
_MIN_UNIQUE_RATIO = 0.15
_MIN_VALID_WORDS = 4
_MIN_ALPHA_RATIO = 0.25


def _normalize_ocr_text(text: str | None) -> str:
    cleaned = (text or "").strip()
    if not cleaned or cleaned in _BAD_OCR_SENTINELS:
        return ""
    cleaned = re.sub(r"^```+\s*", "", cleaned)
    cleaned = re.sub(r"\s*```+\s*$", "", cleaned)
    return cleaned.strip()


def _is_bad_ocr(text: str, *, expected_model: str | None = None, cached_model: str | None = None) -> bool:
    if not text or len(text) < 10:
        return True

    if expected_model and cached_model and cached_model != expected_model:
        return True

    lower = text.lower()
    for substr in _BAD_OCR_SUBSTRINGS:
        if substr in lower:
            return True

    for phrase in _PROMPT_ECHO_PHRASES:
        if phrase in lower:
            return True

    alpha_chars = sum(1 for c in text if c.isalpha())
    total_chars = len(text.replace(" ", "").replace("\n", ""))
    if total_chars > 0 and alpha_chars / total_chars < _MIN_ALPHA_RATIO:
        return True

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) >= 3:
        symbol_lines = sum(1 for ln in lines if not re.search(r"[a-zA-Z\u0600-\u06FF]{3,}", ln))
        if symbol_lines / len(lines) >= 0.6:
            return True

    words = re.findall(r"[a-zA-Z\u0600-\u06FF]+", text)
    if len(words) < _MIN_VALID_WORDS:
        return True
    counts = Counter(words)
    top_count = counts.most_common(1)[0][1]
    if top_count / len(words) > _MAX_WORD_REPEAT_RATIO:
        return True
    if len(counts) / len(words) < _MIN_UNIQUE_RATIO:
        return True
    return False


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

    try:
        attached_files = state.get("attached_files", [])

        if not attached_files:
            return {"ocr_results": [], "ocr_called": False}

        ocr_results: list[dict[str, Any]] = []
        for file_id in attached_files:
            file = await crud.get_file(session, file_id)
            if file is None or not crud.is_image_file(file):
                continue

            ocr_result = await crud.get_ocr_result_by_file_id(session, file_id)
            normalized_cache = _normalize_ocr_text(
                ocr_result.extracted_text if ocr_result else None
            )

            ocr_model = image_processor._settings.OCR_MODEL_NAME
            cached_model = ocr_result.model_used if ocr_result else None

            cache_hit = bool(normalized_cache)
            cache_text_valid = not _is_bad_ocr(normalized_cache) if cache_hit else False
            cache_model_valid = cached_model == ocr_model if cache_hit else True
            cache_valid = cache_hit and cache_text_valid and cache_model_valid
            extracted_text = normalized_cache if cache_valid else ""
            reprocess_attempted = False

            if not cache_valid:
                if cache_hit:
                    logger.warning(
                        "OCR cache rejected for file_id={} filename='{}' "
                        "cached_model='{}' expected_model='{}' cache_model_valid={} "
                        "cache_text_valid={} cached_text_preview='{}'",
                        file_id,
                        file.original_name,
                        cached_model,
                        ocr_model,
                        cache_model_valid,
                        cache_text_valid,
                        normalized_cache[:80],
                    )

                reprocess_attempted = True
                try:
                    image_path = Path(file.disk_path)
                    image_bytes = image_path.read_bytes()
                    content_type = (
                        mimetypes.guess_type(file.original_name)[0]
                        or mimetypes.guess_type(file.disk_path)[0]
                        or "application/octet-stream"
                    )
                    logger.info(
                        "OCR reprocess file_id={} filename='{}' ocr_model={}",
                        file_id,
                        file.original_name,
                        ocr_model,
                    )
                    raw_text = await image_processor._extract_text(image_bytes, content_type)
                    extracted_text = _normalize_ocr_text(raw_text)

                    if _is_bad_ocr(extracted_text):
                        logger.warning(
                            "Bad OCR reprocess result for file_id={} filename='{}' "
                            "reprocess_text_preview='{}'",
                            file_id,
                            file.original_name,
                            extracted_text[:80],
                        )
                        extracted_text = ""
                    else:
                        if ocr_result is None:
                            await crud.create_ocr_result(
                                session,
                                file_id=file_id,
                                extracted_text=raw_text,
                                model_used=ocr_model,
                            )
                        else:
                            ocr_result.extracted_text = raw_text
                            ocr_result.model_used = ocr_model
                            await session.flush()
                except Exception as exc:
                    logger.warning("On-demand OCR failed for file '{}': {}", file_id, exc)

            final_text_valid = bool(extracted_text)
            logger.info(
                "OCR result file_id={} filename='{}' cache_hit={} cache_valid={} "
                "reprocess_attempted={} ocr_model_name={} final_text_valid={}",
                file_id,
                file.original_name,
                cache_hit,
                cache_valid,
                reprocess_attempted,
                image_processor._settings.OCR_MODEL_NAME,
                final_text_valid,
            )

            ocr_results.append(
                {
                    "item_id": f"ocr_{file_id}",
                    "source_type": "ocr",
                    "content": extracted_text or NO_READABLE_TEXT_MESSAGE,
                    "file_id": file_id,
                    "file_name": file.original_name,
                    "chunk_id": f"ocr_{file_id}",
                    "score": 1.0,
                }
            )

        return {"ocr_results": ocr_results, "ocr_called": True}
    except Exception as exc:
        logger.error(f"ocr_node failed: {exc}")
        raise
