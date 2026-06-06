# Research: Ingestion Pipeline

**Feature**: Phase 2 - Ingestion Pipeline
**Date**: 2026-05-19

## Decisions & Findings

### GroundX API Integration

**Decision**: Use groundx-python-sdk for PDF processing with polling for indexing status.

**Rationale**:
- GroundX provides a free tier suitable for initial implementation
- SDK handles authentication and connection management
- Polling is the recommended pattern for asynchronous indexing operations
- Official SDK ensures compatibility with API changes

**Alternatives considered**:
- Direct REST API integration: Requires manual token management, more complexity
- Other PDF parsers (pdfplumber, PyPDF2): Better for local processing but spec requires external service for complex PDF handling

**Implementation Notes**:
- Upload PDF, receive `search_id` and `document_id` from response
- Poll `/documents/{document_id}` endpoint every 2 seconds
- Status transitions: `PROCESSING` → `COMPLETED` → `INDEXED`
- Timeout after 5 minutes (300 seconds) - mark as failed
- Use `tenacity` for retry on transient network errors

---

### Faster-Whisper GPU/CPU Detection

**Decision**: Use torch.cuda.is_available() for GPU detection with graceful CPU fallback.

**Rationale**:
- PyTorch provides reliable CUDA detection across platforms
- Local-first approach avoids external GPU management tools
- CPU fallback ensures functionality without GPU hardware
- Faster-Whisper supports both GPU (CUDA) and CPU inference

**Alternatives considered**:
- Always use CPU: Too slow for production (10x slower)
- Require GPU (fail without): Excludes users without NVIDIA hardware
- Use separate GPU detection library: Adds unnecessary dependency

**Implementation Notes**:
```python
def get_whisper_device() -> tuple[str, str]:
    """Detect available device with safe fallback to CPU."""
    if settings.WHISPER_DEVICE != "auto":
        return (settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE)

    try:
        import torch
        if torch.cuda.is_available():
            return ("cuda", "float16")
    except ImportError:
        pass

    return ("cpu", "int8")
```
- GPU mode: `cuda`, `float16` - for ~5-10x faster transcription
- CPU mode: `cpu`, `int8` - quantization for better speed
- Log device choice on startup

---

### Semantic Chunking Strategy

**Decision**: Token-based chunking with ~10% overlap using tiktoken tokenizer.

**Rationale**:
- Token count is more consistent than character count for LLMs
- ~500 tokens aligns with context window of most embedding models
- 10% overlap preserves context across chunk boundaries
- tiktoken is reliable and widely used for token counting

**Alternatives considered**:
- Sentence-based chunking: Can break mid-sentence at boundaries, less context flow
- Fixed character chunks: Variable token count, harder to tune
- Recursive chunking: More complex, overkill for this use case

**Implementation Notes**:
```python
def chunk_text(text: str, chunk_size: int = 500, overlap: float = 0.1) -> list[str]:
    """Split text into overlapping chunks by token count."""
    tokens = tokenizer.encode(text)
    chunk_size = int(chunk_size * (1 + overlap))
    chunks = []
    for i in range(0, len(tokens), chunk_size):
        chunk_tokens = tokens[i:i + int(chunk_size * (1 - overlap))]
        chunks.append(tokenizer.decode(chunk_tokens))
    return chunks
```
- Target: ~500 tokens per chunk (~400-600 words)
- Overlap: 10% (50 tokens)
- Minimum chunk size: 100 tokens to avoid tiny fragments

---

### Hybrid Search Implementation

**Decision**: Use Qdrant's native hybrid query API with dense (768d) and sparse (BM25) vectors.

**Rationale**:
- Qdrant v1.12+ supports native hybrid search
- Native implementation is more efficient than separate queries + merge
- Reciprocal Rank Fusion (RRF) is industry standard for result combination
- k=60 is empirically validated per Cormack et al. 2009

**Alternatives considered**:
- Dense-only search: Loses keyword matching capability
- Sparse-only search: Loses semantic similarity
- Separate queries + merge: Slower, more complex to implement
- ColBERT: Specified as non-goal, would require different infrastructure

**Implementation Notes**:

**Reciprocal Rank Fusion (RRF) formula**:
```
score(d) = 1 / (k + rank(dense, d))
score(s) = 1 / (k + rank(sparse, s))
final_score = score(dense) + score(sparse)
```

Where:
- `k` = 60 (constant)
- `rank()` returns 1-indexed position (best result = 1)
- Lower rank = higher score

**Qdrant query parameters**:
```python
query_response = qdrant_client.query_points(
    collection_name=settings.QDRANT_COLLECTION,
    query_vector=dense_vector,  # 768 dimensions
    query_limit=5,
    using=models.Distance.COSINE,
    with_payload=True,
    search_params=models.SearchParams(
        hnsw_ef=128,
        exact=False
    )
)
```

---

### MIME Type Validation

**Decision**: Use python-magic library for server-side validation with Content-Type header fallback.

**Rationale**:
- python-magic is cross-platform and reliable
- Server-side validation cannot be bypassed
- Content-Type header provides fast pre-check
- Combined approach: fast header check + thorough file check

**Alternatives considered**:
- Trust Content-Type header only: Can be spoofed
- python-magic only: Requires reading file, slower for large files
- filename extension only: Too unreliable, easily spoofed

**Implementation Notes**:

```python
import magic

def validate_file_type(file_path: str, allowed_types: list[str]) -> bool:
    """Validate file MIME type."""
    # Fast header check (if available)
    content_type = getattr(file, 'content_type', None)
    if content_type and content_type not in allowed_types:
        return False

    # Thorough check with python-magic
    mime_type = magic.from_file(file_path, mime=True)
    return mime_type in allowed_types
```

**Allowed MIME types**:
- PDF: `application/pdf`
- Audio: `audio/mpeg`, `audio/wav`, `audio/m4a`, `audio/ogg`, `audio/mp4`
- Image: `image/jpeg`, `image/png`, `image/webp`

---

### Summary Table

| Area | Decision | Rationale |
|-------|-----------|----------|
| PDF Processing | GroundX SDK with polling | Free tier available, SDK simplifies integration |
| GPU Detection | torch.cuda.is_available() | Reliable, cross-platform, no extra deps |
| Chunking Strategy | Token-based with 10% overlap | Consistent token count, preserves context |
| Hybrid Search | Qdrant native hybrid + RRF | Efficient, industry standard, k=60 validated |
| MIME Validation | python-magic + Content-Type header | Fast + thorough, cross-platform |

---

**No NEEDS CLARIFICATION items remain.**
