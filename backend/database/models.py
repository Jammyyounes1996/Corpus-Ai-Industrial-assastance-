import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.config.settings import get_settings
from backend.database.database import Base

settings = get_settings()


class Project(Base):
    """Organize chats into projects (folders)."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chats: Mapped[list["Chat"]] = relationship(back_populates="project")


class Chat(Base):
    """Store conversation sessions."""

    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["Project | None"] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )


class Message(Base):
    """Store individual messages in conversations."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thinking_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    attached_files: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat: Mapped["Chat"] = relationship(back_populates="messages")


class File(Base):
    """Track uploaded files (PDF, audio, image)."""

    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    disk_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    groundx_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qdrant_collection: Mapped[str | None] = mapped_column(String(100), nullable=True)
    indexing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ocr_result: Mapped["OCRResult | None"] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class OCRResult(Base):
    """Store OCR results from images."""

    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    file: Mapped["File"] = relationship(back_populates="ocr_result")


class Transcript(Base):
    """Store audio transcription results."""

    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    file: Mapped["File"] = relationship(back_populates="transcript")


class AppSettings(Base):
    """Singleton table for application settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, default=1)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="ollama")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default=settings.DEFAULT_MODEL_NAME)
    gemini_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    grok_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="light")
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class EvaluationResult(Base):
    """Store RAGAS evaluation metrics."""

    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_relevancy: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat: Mapped["Chat"] = relationship(back_populates="evaluation_results")
    message: Mapped["Message"] = relationship()

    __table_args__ = (
        UniqueConstraint("chat_id", "message_id", name="uq_eval_chat_message"),
    )


Index("idx_chats_updated_at", Chat.updated_at.desc())
Index("idx_chat_updated", Chat.updated_at.desc())
Index("idx_chats_project_id", Chat.project_id)
Index("idx_messages_chat_id_created", Message.chat_id, Message.created_at)
Index("idx_message_chat", Message.chat_id, Message.created_at.asc())
Index("idx_files_type", File.file_type)
Index("idx_files_created_at", File.created_at.desc())
Index("idx_files_status", File.indexing_status)
Index("idx_ocr_file_id", OCRResult.file_id)
Index("idx_transcripts_file_id", Transcript.file_id)
Index("idx_eval_chat_id", EvaluationResult.chat_id)
Index("idx_eval_message_id", EvaluationResult.message_id)
