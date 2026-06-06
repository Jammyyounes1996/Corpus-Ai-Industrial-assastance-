"""Evaluation API routes for RAGAS metrics."""

import json
from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import crud
from backend.database.database import get_session
from backend.database.models import Message
from backend.schemas.evaluation import (
    EvaluateRequest,
    EvaluateResponse,
    EvaluationItem,
    EvaluationListResponse,
)

router = APIRouter(prefix="/api", tags=["evaluation"])


@router.post("/evaluate", status_code=201, response_model=EvaluateResponse)
async def evaluate_message(
    payload: EvaluateRequest,
    session: AsyncSession = Depends(get_session),
) -> EvaluateResponse:
    existing = await crud.get_evaluation_by_message(session, payload.message_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": "AlreadyExists", "message": "Evaluation already exists for this message"},
        )

    chat = await crud.get_chat(session, payload.chat_id)
    if chat is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NotFound", "message": "Chat not found"},
        )

    message = None
    for msg in chat.messages:
        if msg.id == payload.message_id:
            message = msg
            break

    if message is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NotFound", "message": "Message not found in chat"},
        )

    if not message.retrieved_context:
        raise HTTPException(
            status_code=400,
            detail={"error": "ValidationError", "message": "Message has no retrieved context"},
        )

    user_question = ""
    for msg in chat.messages:
        if msg.id < payload.message_id and msg.role == "user":
            user_question = msg.content

    if not user_question:
        raise HTTPException(
            status_code=400,
            detail={"error": "ValidationError", "message": "No user question found before this message"},
        )

    try:
        from backend.core.evaluation.ragas_evaluator import run_evaluation

        result = await run_evaluation(
            question=user_question,
            answer=message.content,
            retrieved_context=message.retrieved_context,
            judge_model=payload.judge_model,
        )
    except Exception as exc:
        logger.exception("RAGAS evaluation failed")
        raise HTTPException(
            status_code=500,
            detail={"error": "EvaluationError", "message": f"RAGAS evaluation failed: {exc}"},
        )

    eval_record = await crud.create_evaluation(
        session,
        chat_id=payload.chat_id,
        message_id=payload.message_id,
        faithfulness=result.get("faithfulness"),
        answer_relevancy=result.get("answer_relevancy"),
        model_used=result.get("model_used"),
    )
    await session.commit()
    await session.refresh(eval_record)

    return EvaluateResponse.model_validate(eval_record)


@router.get("/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    chat_id: str | None = Query(None, description="Filter by chat_id"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> EvaluationListResponse:
    evaluations, total = await crud.get_evaluations(
        session,
        chat_id=chat_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for ev in evaluations:
        msg_result = await session.execute(
            select(Message).where(Message.id == ev.message_id)
        )
        msg = msg_result.scalar_one_or_none()
        preview = (msg.content[:100] if msg and msg.content else None)

        items.append(EvaluationItem(
            id=ev.id,
            chat_id=ev.chat_id,
            message_id=ev.message_id,
            faithfulness=ev.faithfulness,
            answer_relevancy=ev.answer_relevancy,
            model_used=ev.model_used,
            message_preview=preview,
            created_at=ev.created_at,
        ))

    return EvaluationListResponse(
        evaluations=items,
        total=total,
        limit=limit,
        offset=offset,
    )
