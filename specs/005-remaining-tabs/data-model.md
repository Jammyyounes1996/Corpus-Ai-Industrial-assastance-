# Data Model: Remaining Workspace Tabs

**Date**: 2026-06-06 | **Feature**: [spec.md](spec.md)

## Existing Entities (no changes needed)

### File

| Field | Type | Notes |
|-------|------|-------|
| id | String(36) PK | UUID |
| original_name | String(500) | Original filename |
| file_type | String(20) | "pdf", "audio", "image" |
| disk_path | String(1000) | Full path on disk |
| size_bytes | Integer | File size |
| groundx_id | String(100) nullable | GroundX document ID |
| qdrant_collection | String(100) nullable | Qdrant collection name |
| indexing_status | String(20) | "pending", "processing", "indexed", "failed" |
| error_message | Text nullable | Error details if failed |
| created_at | DateTime | Upload timestamp |

**Relationships**: Has one `OCRResult`, has one `Transcript` (both cascade delete).

### OCRResult

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-increment |
| file_id | String(36) FK → files.id | Unique constraint |
| extracted_text | Text | Full OCR output |
| model_used | String(50) | Model that performed OCR |
| created_at | DateTime | Processing timestamp |

### Transcript

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-increment |
| file_id | String(36) FK → files.id | Unique constraint |
| transcript_text | Text | Full transcription |
| duration_seconds | Float | Audio duration |
| language | String(10) | Detected language code |
| created_at | DateTime | Processing timestamp |

### EvaluationResult

| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-increment |
| chat_id | String(36) FK → chats.id | CASCADE delete |
| message_id | Integer FK → messages.id | CASCADE delete |
| faithfulness | Float nullable | 0.0-1.0 score |
| answer_relevancy | Float nullable | 0.0-1.0 score |
| context_precision | Float nullable | Unused (requires ground truth) |
| context_recall | Float nullable | Unused (requires ground truth) |
| created_at | DateTime | Evaluation timestamp |

**Constraints**: UniqueConstraint on (chat_id, message_id) — one evaluation per message.

### Message (relevant fields for Analysis tab)

| Field | Type | Notes |
|-------|------|-------|
| thinking_steps | Text nullable | JSON array of thinking step objects |
| retrieved_context | Text nullable | JSON array of source chunk objects |

**thinking_steps JSON structure** (persisted from SSE stream):
```json
[
  {
    "type": "routing",
    "content": "Classifying query as technical documentation lookup",
    "metadata": {
      "node": "router_node",
      "status": "completed",
      "duration_ms": 45,
      "category": "technical",
      "routes": ["groundx", "qdrant"]
    },
    "timestamp": "2026-06-06T10:30:00Z"
  }
]
```

**retrieved_context JSON structure** (persisted from SSE stream):
```json
[
  {
    "file_id": "abc-123",
    "filename": "manual.pdf",
    "file_type": "pdf",
    "chunk_index": 3,
    "score": 0.87,
    "excerpt": "The hydraulic pressure should be maintained at..."
  }
]
```

## New CRUD Functions Needed

### Evaluation CRUD (`backend/database/crud.py`)

```python
async def create_evaluation(session, *, chat_id, message_id, faithfulness, answer_relevancy) -> EvaluationResult
async def get_evaluations(session, *, chat_id=None, limit=50, offset=0) -> tuple[list[EvaluationResult], int]
async def get_evaluation_by_message(session, *, chat_id, message_id) -> EvaluationResult | None
```

## Frontend Type Mappings

### FileListResponse (from GET /api/files)

```typescript
interface FileItem {
  id: string
  original_name: string
  file_type: 'pdf' | 'audio' | 'image'
  size_bytes: number
  indexing_status: 'pending' | 'processing' | 'indexed' | 'failed'
  error_message: string | null
  created_at: string  // ISO datetime
  transcript_summary?: { duration_seconds: number; language: string }
  ocr_summary?: { text_preview: string; model_used: string }
}

interface FileListResponse {
  files: FileItem[]
  total: number
  limit: number
  offset: number
}
```

### EvaluationResponse (from POST /api/evaluate)

```typescript
interface EvaluationResponse {
  id: number
  chat_id: string
  message_id: number
  faithfulness: number | null
  answer_relevancy: number | null
  model_used: string
  created_at: string  // ISO datetime
}
```

### Analysis Tab Data (from GET /api/chat/{chat_id} messages)

```typescript
interface ThinkingStepPersisted {
  type: string
  content: string
  metadata: {
    node: string
    status: 'completed' | 'failed' | 'skipped'
    duration_ms: number
    [key: string]: unknown
  }
  timestamp: string
}

interface RetrievedChunk {
  file_id: string
  filename: string
  file_type: string
  chunk_index: number
  score: number
  excerpt: string
}
```
