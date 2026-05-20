# Data Model: Ingestion Pipeline

**Feature**: Phase 2 - Ingestion Pipeline
**Date**: 2026-05-19

## Entities

### IngestedFile

Represents a file uploaded by a user and tracked across all storage locations.

**Attributes**:
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| id | str (UUID) | Unique identifier for the file | Auto-generated, primary key |
| original_name | str | Original filename from upload | Max 255 characters, sanitized |
| file_type | str | Type: "pdf", "audio", or "image" | Enum constraint |
| disk_path | str | Full path to stored file on disk | Validated to be within data/ directories |
| size_bytes | int | File size in bytes | Must match actual file size |
| groundx_id | Optional[str] | External document ID (GroundX) for PDFs | Null for non-PDF files |
| qdrant_collection | Optional[str] | Vector collection name | Null for unindexed files |
| indexing_status | str | Processing state | Enum: "pending", "processing", "indexed", "failed" |
| error_message | Optional[str] | Error details if indexing failed | Only set when status = "failed" |
| created_at | datetime | Upload timestamp | Auto-generated |

**State Transitions**:
```
pending → processing → indexed (success path)
pending → processing → failed (error path)
```

**Validation Rules**:
- `file_type` must be one of: "pdf", "audio", "image"
- `indexing_status` cannot regress from "indexed" to "failed"
- `groundx_id` is required only when `file_type = "pdf"`
- `size_bytes` must be within limits: PDF ≤ 100MB, Audio ≤ 100MB, Image ≤ 25MB

---

### Transcript

Represents transcribed text from an audio file.

**Attributes**:
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| id | int | Unique identifier | Auto-increment, primary key |
| file_id | str (UUID) | Reference to IngestedFile | Foreign key to IngestedFile.id |
| transcript_text | str (text) | Full transcribed content | No length limit, stored as TEXT |
| duration_seconds | float | Audio duration | Must be >= 0 |
| language | str | Detected language code | ISO 639-1 format (e.g., "en", "es") |
| created_at | datetime | Transcription timestamp | Auto-generated |

**Relationships**:
- `file_id` → `IngestedFile.id` (one-to-many: one file can have one transcript)
- One `Transcript` → Many `Chunk` (chunks contain transcript segments)

**Validation Rules**:
- `duration_seconds` must be >= 0
- `language` must be valid ISO 639-1 code
- `file_id` must reference existing `IngestedFile` with `file_type = "audio"`

---

### OCRResult

Represents text extracted from an image via OCR.

**Attributes**:
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| id | int | Unique identifier | Auto-increment, primary key |
| file_id | str (UUID) | Reference to IngestedFile | Foreign key to IngestedFile.id |
| extracted_text | str (text) | Text extracted from image | Can be empty string |
| model_used | str | Vision model identifier | e.g., "gemma4", "gemma4:e4b" |
| created_at | datetime | OCR processing timestamp | Auto-generated |

**Relationships**:
- `file_id` → `IngestedFile.id` (one-to-many: one file can have one OCR result)

**Validation Rules**:
- `extracted_text` can be empty string (for images with no readable text)
- `file_id` must reference existing `IngestedFile` with `file_type = "image"`
- `model_used` must be configured model name

---

### Chunk

Represents a segment of text that has been embedded and stored in vector database.

**Note**: This is NOT a database table. Chunks live in Qdrant vector store with metadata.

**Attributes**:
| Field | Type | Description | Constraints |
|-------|------|-------------|--------------|
| id | str (UUID) | Unique chunk identifier | Auto-generated |
| chunk_text | str | Text content of the chunk | ~500 tokens, max ~4000 chars |
| dense_vector | list[float] | Dense embedding vector | 768 dimensions (nomic-embed-text) |
| sparse_vector | SparseVector | Sparse BM25 vector | Token indices with weights |
| chunk_index | int | Sequential index within file | Starts at 0 |
| file_id | str (UUID) | Reference to source file | Stored as payload |
| file_type | str | Source file type | "pdf", "audio", or "image" |
| created_at | datetime | Chunk creation timestamp | Stored as payload |

**Qdrant Payload Schema**:
```json
{
  "file_id": "uuid",
  "file_type": "audio",
  "chunk_index": 0,
  "chunk_text": "...",
  "created_at": "2026-05-19T12:00:00Z"
}
```

**Relationships**:
- `file_id` → `IngestedFile.id` (one-to-many: one file can have many chunks)
- Derived from: `Transcript` (for audio) or directly from `IngestedFile` (for PDFs indexed via GroundX)
- Images do NOT produce chunks (OCR text is stored in database only)

**Validation Rules**:
- `chunk_text` must be <= 4000 characters (~500 tokens)
- `dense_vector` must have exactly 768 dimensions
- `sparse_vector` must contain only valid token indices and weights
- `chunk_index` must be unique per `file_id`
- `file_type` must match the source `IngestedFile.file_type`

---

## Entity Relationships Diagram

```
IngestedFile (1) ────── (1) Transcript
         │
         ├───── (1) OCRResult  [only for image files]
         │
         └───── (N) Chunk        [via Qdrant, for PDF + audio]
                                       │
                                       └───── (0..N) file references in Qdrant
```

---

## Data Flow

### PDF Ingestion Flow
```
1. User uploads PDF → /api/ingest/pdf
2. Save to data/uploads/<uuid>.pdf
3. Create IngestedFile record (status: "pending")
4. Upload to GroundX → receive search_id + document_id
5. Update IngestedFile (status: "processing", groundx_id: document_id)
6. Poll GroundX for indexing status
7. When complete → Update IngestedFile (status: "indexed")
8. GroundX handles chunking + embedding → stored in Qdrant
```

### Audio Ingestion Flow
```
1. User uploads audio → /api/ingest/audio
2. Save to data/audio/<uuid>.<ext>
3. Create IngestedFile record (status: "pending")
4. Transcribe with Faster-Whisper
5. Create Transcript record
6. Chunk transcript (~500 tokens each)
7. Embed chunks with nomic-embed-text
8. Insert chunks into Qdrant with metadata
9. Update IngestedFile (status: "indexed")
```

### Image OCR Flow
```
1. User uploads image → /api/ingest/image
2. Save to data/images/<uuid>.<ext>
3. Create IngestedFile record (status: "pending")
4. Send to Gemma4 vision for OCR
5. Create OCRResult record
6. Update IngestedFile (status: "indexed")
```

### File Deletion Flow
```
1. User requests delete → DELETE /api/files/{id}
2. Start transaction
3. Delete file from disk
4. Delete IngestedFile record from database
5. Delete Transcript record (if audio)
6. Delete OCRResult record (if image)
7. Delete all Chunks from Qdrant with payload filter {file_id: id}
8. Commit transaction
9. If any step fails → rollback with error
```

---

## Constraints

### File Size Limits
| File Type | Max Size | Enforcement Point |
|-----------|----------|------------------|
| PDF | 100 MB | API boundary + python-magic validation |
| Audio | 100 MB | API boundary + python-magic validation |
| Image | 25 MB | API boundary + python-magic validation |

### Indexing Status Lifecycle
```
pending     → Initial state after file upload, before processing
processing  → External/async operation in progress
indexed     → Successfully processed and searchable
failed      → Processing failed, error_message populated
```

### Filename Sanitization Rules
- Max 255 characters
- No path traversal (no "../", "..\\")
- Remove: null bytes, control characters, leading/trailing spaces
- Replace: any character not in [a-zA-Z0-9._-] with "_"
