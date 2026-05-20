# Event Contracts: SSE Streaming

**Feature**: Phase 2 - Ingestion Pipeline + Future Phase 3 (Agent)
**Date**: 2026-05-19

## Overview

This document defines Server-Sent Events (SSE) event types for real-time status updates. These events will be used in Phase 3 for the agent chat streaming, but some ingestion progress events are defined here for future use.

## SSE Message Format

All SSE messages follow this structure:

```
event: <event_type>
data: <json_payload>

[blank line]
```

---

## Ingestion Progress Events

These events report progress during long-running ingestion operations.

### Event: `ingestion_progress`

Emitted during PDF indexing or audio transcription to provide real-time feedback.

### Data Payload
```json
{
  "file_id": "550e8400-e29b-41d4-a716-44665544010",
  "file_type": "pdf",
  "filename": "pump_manual.pdf",
  "stage": "uploading" | "processing" | "indexing" | "completed",
  "progress_percent": 0-100,
  "message": "Uploading file to server...",
  "estimated_remaining_seconds": 120
}
```

**stage values**:
| Stage | Description |
|-------|-------------|
| `uploading` | File being received and saved to disk |
| `processing` | External service processing (GroundX) or local processing (Whisper) |
| `indexing` | Chunks being embedded and stored in Qdrant |
| `completed` | All processing finished, file is searchable |

### Progress Rules
- `progress_percent` is 0 when `stage` = "uploading"
- `progress_percent` increments during `processing` and `indexing`
- `estimated_remaining_seconds` is provided when `stage` = "processing"` or `"indexing"`
- `message` is human-readable status text

---

## Indexing Complete Event

Emitted when a file has been fully processed and is searchable.

### Event: `indexing_complete`

Indicates a file is now available for search.

### Data Payload
```json
{
  "file_id": "550e8400-e29b-41d4-a716-44665544010",
  "file_type": "pdf",
  "filename": "pump_manual.pdf",
  "indexing_status": "indexed",
  "chunks_count": 15,
  "processing_time_seconds": 284.5
}
```

**Notes**:
- `chunks_count` is only present for `file_type = "pdf"` or `"audio"` (images don't have chunks)
- `processing_time_seconds` is total time from upload to completion
- Event is always emitted after final `ingestion_progress` event with `stage = "completed"`

---

## File Deleted Event

Emitted when a file is successfully deleted from all storage locations.

### Event: `file_deleted`

Notifies clients that a file has been removed.

### Data Payload
```json
{
  "file_id": "550e8400-e29b-41d4-a716-44665544010",
  "file_type": "pdf",
  "deleted_locations": ["disk", "database", "qdrant", "transcript"]
}
```

**deleted_locations values**:
| Location | When Included |
|----------|---------------|
| `disk` | Always included - file removed from data/ directory |
| `database` | Always included - IngestedFile record deleted |
| `qdrant` | Included only for PDFs and audio (has chunks) |
| `transcript` | Included only for audio files |
| `ocr_result` | Included only for image files |

---

## Future Agent Events (Phase 3 Placeholder)

These events will be used in Phase 3 for the LangGraph agent streaming.

### Event: `thinking_step`

Emitted when LangGraph agent enters or completes a processing node.

### Event: `token`

Emitted when LLM generates a token during streaming response.

### Event: `sources`

Emitted with final response containing relevant source files.

### Event: `done`

Emitted when agent has completed and final answer is ready.

---

## Event Sequences

### PDF Ingestion Sequence
```
1. ingestion_progress (stage: "uploading", progress: 0-20)
2. ingestion_progress (stage: "processing", progress: 20-80) - GroundX
3. ingestion_progress (stage: "indexing", progress: 80-95)
4. indexing_complete
```

### Audio Ingestion Sequence
```
1. ingestion_progress (stage: "uploading", progress: 0-15)
2. ingestion_progress (stage: "processing", progress: 15-70) - Whisper
3. ingestion_progress (stage: "indexing", progress: 70-95)
4. indexing_complete
```

### Image OCR Sequence
```
1. ingestion_progress (stage: "uploading", progress: 0-20)
2. ingestion_progress (stage: "processing", progress: 20-90) - Gemma4 vision
3. ingestion_progress (stage: "completed", progress: 100)
4. indexing_complete
```

### File Deletion Sequence
```
1. file_deleted
```

---

## Client Implementation Notes

### Connection
- Use SSE client library: `httpx-sse`
- Connect to endpoint: `http://localhost:8000/api/ingest/stream`
- Maintain connection until file processing completes

### Event Handling
```python
async with httpx_sse.aio_client() as event_source:
    async for event in event_source:
        if event.event == "ingestion_progress":
            data = json.loads(event.data)
            update_progress_bar(data["progress_percent"])
        elif event.event == "indexing_complete":
            data = json.loads(event.data)
            show_success_notification(data["filename"])
```

### Reconnection
- If connection drops, attempt to reconnect with exponential backoff
- If reconnection fails more than 3 times, show error to user
- Client can request current file status via GET /api/files/{id}

---

## Error Events

### Event: `ingestion_error`

Emitted when ingestion fails at any stage.

### Data Payload
```json
{
  "file_id": "550e8400-e29b-41d4-a716-44665544010",
  "file_type": "pdf",
  "error_type": "PDFProcessingError" | "TranscriptionError" | "OCRError",
  "stage": "processing" | "indexing",
  "message": "GroundX service unavailable",
  "is_retriable": true | false
}
```

**error_type values**:
| Error Type | When Emitted |
|-----------|--------------|
| `PDFProcessingError` | GroundX upload or indexing failed |
| `TranscriptionError` | Whisper transcription failed |
| `OCRError` | Gemma4 vision OCR failed |
| `ChunkingError` | Text chunking failed |
| `EmbeddingError` | nomic-embed-text embedding failed |
| `QdrantError` | Vector store insertion failed |

**is_retriable**:
- `true`: Automatic retry should be attempted
- `false`: User intervention required (e.g., invalid file type)
