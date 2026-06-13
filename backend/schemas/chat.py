"""Pydantic schemas for chat API validation and serialization."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from backend.config.settings import get_settings

settings = get_settings()


class ThinkingStep(BaseModel):
    step: str
    status: str
    node: str
    duration_ms: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"pending", "in_progress", "completed", "failed"}
        if value not in allowed:
            raise ValueError(f"Invalid status: {value}")
        return value


class Source(BaseModel):
    file_id: str
    filename: str
    file_type: str
    chunk_index: int
    score: float
    excerpt: str


class ChatRequest(BaseModel):
    chat_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=settings.MAX_MESSAGE_LENGTH)
    attached_files: list[str] = Field(default_factory=list)

    @field_validator("attached_files")
    @classmethod
    def validate_files(cls, value: list[str]) -> list[str]:
        return value[: settings.MAX_ATTACHED_FILES]


class ChatSummary(BaseModel):
    id: str
    title: str
    model_provider: str
    model_name: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ChatListResponse(BaseModel):
    chats: list[ChatSummary]
    total: int


class MessageSchema(BaseModel):
    id: int
    role: str
    content: str
    thinking_steps: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_context: list[Source] = Field(default_factory=list)
    attached_files: list[str] = Field(default_factory=list)
    created_at: datetime


class ChatDetailResponse(BaseModel):
    id: str
    title: str
    model_provider: str
    model_name: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageSchema]


class ChatCreate(BaseModel):
    """Schema for creating a new chat."""

    title: Optional[str] = None
    model_provider: str = "ollama"
    model_name: Optional[str] = None  # If None, use default from settings


class ChatResponse(BaseModel):
    """Schema for returning chat metadata."""

    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    """Schema for creating a chat message."""

    role: str
    content: str = Field(..., min_length=1, max_length=settings.MAX_MESSAGE_LENGTH)
    retrieved_context: Optional[str] = None
    attached_files: Optional[list[str]] = []

    @field_validator("attached_files")
    @classmethod
    def validate_attached_files(cls, value: Optional[list[str]]) -> list[str]:
        return (value or [])[: settings.MAX_ATTACHED_FILES]


class MessageResponse(BaseModel):
    """Schema for returning a persisted message."""

    id: str
    chat_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StreamRequest(BaseModel):
    """Schema for chat streaming requests."""

    query: str = Field(..., min_length=1, max_length=settings.MAX_MESSAGE_LENGTH)
    model_provider: str = settings.DEFAULT_MODEL_PROVIDER
    model_name: str = settings.DEFAULT_MODEL_NAME
    attached_files: Optional[list[str]] = []
    answer_mode: Literal["groundx", "audio", "general"] = "general"
    task_type: Optional[str] = None

    @field_validator("attached_files")
    @classmethod
    def validate_stream_files(cls, value: Optional[list[str]]) -> list[str]:
        return (value or [])[: settings.MAX_ATTACHED_FILES]
