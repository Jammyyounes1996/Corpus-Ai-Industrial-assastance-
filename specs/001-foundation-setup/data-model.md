# Data Model: Industrial AI Assistant

**Feature**: 001-foundation-setup
**Date**: 2026-05-18
**Status**: Phase 1 Ready

---

## Overview

This document defines the complete data model for the Industrial AI Assistant. All tables are implemented in SQLite via SQLAlchemy 2.0 async patterns.

---

## ERD

```
┌─────────────┐         ┌─────────────┐         ┌──────────────────┐
│   Project   │1       N│    Chat     │1       N│     Message      │
├─────────────┤─────────┼─────────────┤─────────┼──────────────────┤
│ id (PK)     │         │ id (PK)     │         │ id (PK)          │
│ name        │         │ title       │         │ chat_id (FK)     │
│ created_at  │         │ project_id  │         │ role             │
└─────────────┘         │ model_...   │         │ content          │
                        │ created_at  │         │ thinking_steps   │
                        │ updated_at  │         │ retrieved_context│
                        └─────────────┘         │ attached_files   │
                                                 │ created_at       │
                                                 └──────────────────┘

┌──────────────────┐         ┌──────────────────┐
│      File        │1     1 │    Transcript    │
├──────────────────┤─────────┼──────────────────┤
│ id (PK)          │         │ id (PK)          │
│ original_name    │         │ file_id (FK)     │
│ file_type        │         │ transcript_text  │
│ disk_path        │         │ duration_seconds │
│ size_bytes       │         │ language         │
│ groundx_id       │         │ created_at       │
│ qdrant_collection│         └──────────────────┘
│ indexing_status  │
│ created_at       │         ┌──────────────────┐
└──────────────────┘         │    OCRResult     │
                        1   1 ├──────────────────┤
                             │ id (PK)          │
                             │ file_id (FK)     │
                             │ extracted_text   │
                             │ model_used       │
                             │ created_at       │
                             └──────────────────┘

┌──────────────────┐         ┌──────────────────────┐
│   AppSettings    │1     N │  EvaluationResult    │
├──────────────────┤─────────┼──────────────────────┤
│ id (PK, =1)      │         │ id (PK)              │
│ model_provider   │         │ chat_id (FK)         │
│ model_name       │         │ message_id (FK)      │
│ gemini_api_...   │         │ faithfulness         │
│ grok_api_...     │         │ answer_relevancy     │
│ theme            │         │ context_precision    │
│ updated_at       │         │ context_recall       │
└──────────────────┘         │ created_at           │
                             └──────────────────────┘
```

---

## Table Definitions

### 1. Project

**Purpose**: Organize chats into projects (folders).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| name | VARCHAR(255) | UNIQUE, NOT NULL | Project name (e.g., "Pump Maintenance") |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Validation**: Names must be non-empty, max 255 characters.
**State transitions**: N/A (no status field).

---

### 2. Chat

**Purpose**: Store conversation sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID v4 string |
| title | VARCHAR(500) | NOT NULL | Auto-generated from first message |
| project_id | INTEGER | FK → Project.id, NULLABLE | Parent project (or null for "unsorted") |
| model_provider | VARCHAR(50) | NOT NULL | "ollama", "gemini", or "grok" |
| model_name | VARCHAR(100) | NOT NULL | Model name (e.g., "gemma2:latest") |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Chat creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last message time |

**Validation**: title must be non-empty, max 500 characters.
**Indexes**: `(project_id, updated_at DESC)` for sidebar queries.

---

### 3. Message

**Purpose**: Store individual messages in conversations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| chat_id | VARCHAR(36) | FK → Chat.id, NOT NULL | Parent chat |
| role | VARCHAR(20) | NOT NULL | "user" or "assistant" |
| content | TEXT | NOT NULL | Message content (Markdown) |
| thinking_steps | JSON | NULLABLE | List of step objects with status/duration |
| retrieved_context | JSON | NULLABLE | List of retrieved chunks with scores |
| attached_files | JSON | NULLABLE | List of attached file UUIDs |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Message timestamp |

**Validation**: role must be "user" or "assistant".
**Indexes**: `(chat_id, id)` for chronological retrieval.

**JSON Schema for thinking_steps**:
```json
[
  {
    "step": "Reading PDF documents...",
    "status": "completed",
    "duration_ms": 1240,
    "node": "groundx_retrieve"
  }
]
```

**JSON Schema for retrieved_context**:
```json
[
  {
    "file_id": "uuid",
    "filename": "manual.pdf",
    "chunk": "...",
    "score": 0.92
  }
]
```

---

### 4. File

**Purpose**: Track uploaded files (PDF, audio, image).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID v4 string |
| original_name | VARCHAR(500) | NOT NULL | Original filename |
| file_type | VARCHAR(20) | NOT NULL | "pdf", "audio", or "image" |
| disk_path | VARCHAR(1000) | NOT NULL | Absolute path on disk |
| size_bytes | INTEGER | NOT NULL | File size in bytes |
| groundx_id | VARCHAR(100) | NULLABLE | GroundX document ID (PDFs only) |
| qdrant_collection | VARCHAR(100) | NULLABLE | Qdrant collection name |
| indexing_status | VARCHAR(20) | NOT NULL | "pending", "processing", "indexed", "failed" |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Upload timestamp |

**Validation**: file_type must be one of "pdf", "audio", "image".
**Validation**: indexing_status must be one of valid status values.
**Indexes**: `(indexing_status)` for filtering.

**State transitions**:
```
pending → processing → indexed
                      ↘ failed
```

---

### 5. Transcript

**Purpose**: Store audio transcription results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| file_id | VARCHAR(36) | FK → File.id, UNIQUE, NOT NULL | Parent audio file |
| transcript_text | TEXT | NOT NULL | Full transcription |
| duration_seconds | FLOAT | NOT NULL | Audio duration in seconds |
| language | VARCHAR(10) | NOT NULL | Detected language (e.g., "en", "es") |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Transcription timestamp |

**Validation**: file_id must reference an audio file (file_type = "audio").
**Validation**: language must be a valid ISO 639-1 code.

---

### 6. OCRResult

**Purpose**: Store OCR results from images.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| file_id | VARCHAR(36) | FK → File.id, UNIQUE, NOT NULL | Parent image file |
| extracted_text | TEXT | NOT NULL | OCR extracted text |
| model_used | VARCHAR(50) | NOT NULL | Model used (e.g., "gemma2:9b-vision") |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | OCR timestamp |

**Validation**: file_id must reference an image file (file_type = "image").

---

### 7. AppSettings

**Purpose**: Singleton table for application settings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, DEFAULT 1 | Always 1 (singleton) |
| model_provider | VARCHAR(50) | NOT NULL | Default: "ollama" |
| model_name | VARCHAR(100) | NOT NULL | Default: "gemma2:latest" |
| gemini_api_key_encrypted | TEXT | NULLABLE | Fernet-encrypted API key |
| grok_api_key_encrypted | TEXT | NULLABLE | Fernet-encrypted API key |
| theme | VARCHAR(10) | NOT NULL | "light" or "dark" |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Validation**: id must always be 1. Only one row exists.

---

### 8. EvaluationResult

**Purpose**: Store RAGAS evaluation metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| chat_id | VARCHAR(36) | FK → Chat.id, NOT NULL | Parent chat |
| message_id | INTEGER | FK → Message.id, NOT NULL | Evaluated message |
| faithfulness | FLOAT | NULLABLE | Score 0-1 |
| answer_relevancy | FLOAT | NULLABLE | Score 0-1 |
| context_precision | FLOAT | NULLABLE | Score 0-1 |
| context_recall | FLOAT | NULLABLE | Score 0-1 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Evaluation timestamp |

**Validation**: All metric scores must be between 0 and 1, or NULL if evaluation failed.
**Indexes**: `(chat_id, message_id)` unique constraint.

---

## Validation Rules Summary

### File Type Enum
```python
FileType = Literal["pdf", "audio", "image"]
```

### Indexing Status Enum
```python
IndexingStatus = Literal["pending", "processing", "indexed", "failed"]
```

### Role Enum
```python
MessageRole = Literal["user", "assistant"]
```

### Model Provider Enum
```python
ModelProvider = Literal["ollama", "gemini", "grok"]
```

### Theme Enum
```python
Theme = Literal["light", "dark"]
```

---

## Foreign Key Constraints

| Table | FK Column | References | On Delete |
|-------|-----------|------------|-----------|
| Chat | project_id | Project.id | SET NULL |
| Message | chat_id | Chat.id | CASCADE |
| Transcript | file_id | File.id | CASCADE |
| OCRResult | file_id | File.id | CASCADE |
| EvaluationResult | chat_id | Chat.id | CASCADE |
| EvaluationResult | message_id | Message.id | CASCADE |

---

## Database Initialization

**File**: `scripts/init_db.py`

Creates the database file and runs Alembic migrations:

```python
import asyncio
from backend.database.database import engine, Base
from backend.database.models import *

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**File**: `scripts/setup_qdrant_collection.py`

Creates the Qdrant collection:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams

client = QdrantClient(url="http://localhost:6333")

client.recreate_collection(
    collection_name="industrial_assistant",
    vectors_config={
        "dense": VectorParams(size=768, distance=Distance.COSINE)
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams()
    }
)
```

---

## Migration Strategy

**Tool**: Alembic

- All schema changes via migrations
- Migration files in `backend/database/migrations/versions/`
- Naming convention: `{timestamp}_{description}.py`
- Async migrations supported

Example migration:
```python
def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

---

## Access Patterns

### Common Queries

1. **Get all chats in sidebar**:
   ```python
   SELECT * FROM Chat ORDER BY updated_at DESC
   ```

2. **Get messages for a chat**:
   ```python
   SELECT * FROM Message WHERE chat_id = ? ORDER BY created_at
   ```

3. **Get unindexed files**:
   ```python
   SELECT * FROM File WHERE indexing_status IN ('pending', 'processing')
   ```

4. **Get OCR history**:
   ```python
   SELECT f.*, o.extracted_text FROM File f
   JOIN OCRResult o ON f.id = o.file_id
   WHERE f.file_type = 'image'
   ORDER BY f.created_at DESC
   ```

5. **Get chats in a project**:
   ```python
   SELECT * FROM Chat WHERE project_id = ? ORDER BY updated_at DESC
   ```

---

**End of Data Model**