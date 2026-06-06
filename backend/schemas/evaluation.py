"""Pydantic schemas for evaluation API validation and serialization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    chat_id: str
    message_id: int
    judge_model: Optional[str] = None


class EvaluateResponse(BaseModel):
    id: int
    chat_id: str
    message_id: int
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    model_used: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationItem(BaseModel):
    id: int
    chat_id: str
    message_id: int
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    model_used: Optional[str] = None
    message_preview: Optional[str] = None
    created_at: datetime


class EvaluationListResponse(BaseModel):
    evaluations: list[EvaluationItem]
    total: int
    limit: int
    offset: int
