# Code Review Findings: Ingestion Pipeline

**Date**: 2026-05-20
**Reviewer**: Claude Code
**Scope**: All implemented tasks marked [X] in tasks.md

---

## Critical Issues (Must Fix)

### 1. HIGH: chunking.py - Potential Infinite Loop

**File**: `backend/core/ingestion/chunking.py`
**Lines**: 36-39
**Severity**: HIGH

**Issue**: No validation that `stride > 0`. If `overlap_fraction >= 1.0`, loop becomes infinite.

```python
overlap = int(max_tokens * overlap_fraction)
stride = max_tokens - overlap
if stride <= 0:
    stride = max_tokens  # Only handles stride==0, not negative
```

**Edge case**: With `overlap_fraction=1.0`, stride becomes 0 and loop becomes infinite.

**Fix**: Add validation:
```python
if overlap_fraction < 0 or overlap_fraction >= 1.0:
    raise ValueError(f"overlap_fraction must be in range [0, 1), got {overlap_fraction}")
```

---

## Non-Critical Issues

### 2. LOW: Widespread Typo - "ingest" instead of "ingest"

**Files**: Multiple
**Locations**:
- `pdf_ingestor.py`: Method name `ingest_pdf`, log messages with "ingest"
- `audio_ingestor.py`: Method name `ingest_audio`
- `image_processor.py`: Method name `ingest_image`
- Error messages in all three ingestors

**Impact**: Minor - "ingest" looks unprofessional but doesn't affect functionality.

**Fix**: Rename methods to `ingest_pdf`, `ingest_audio`, `ingest_image` and update all references.

---

### 3. LOW: conftest.py - Syntax Error in Mock

**File**: `tests/conftest.py`
**Line**: 49

**Issue**: Extra closing brace in dictionary:
```python
mock.poll_indexing_status = AsyncMock(
    return_value={"status": "complete", "error_message": None}  # Extra brace
)
```

**Impact**: Tests still pass (likely corrected by JSON parsing), but this is sloppy.

---

### 4. INFO: SQLAlchemy Deprecation Warning

**File**: `backend/database/models.py`
**Lines**: Multiple (default=datetime.utcnow)

**Issue**: `datetime.utcnow()` is deprecated in SQLAlchemy 2.0+. Should use timezone-aware datetime.

**Impact**: Warning only - functionality still works.

---

### 5. MEDIUM: files.py - Missing Case-Insensitive Content-Type Check

**File**: `backend/api/routes/ingest.py`
**Lines**: 31-39, 96-104, 158-166

**Issue**: Content type comparison is case-sensitive:
```python
if content_type != "application/pdf":
    raise HTTPException(...)
```

Browsers may send `application/PDF` or `Application/PDF`. The `UploadFile.content_type` may vary.

**Impact**: Some browsers might incorrectly reject valid files.

**Fix**: `if content_type.lower() != "application/pdf":`

---

## Edge Cases & Missing Validations

### 6. Missing: Filename Length Validation

**Files**: `backend/database/crud.py` (create_file)

**Issue**: Uploaded filenames are used directly without length validation before DB insertion.

**Impact**: The database schema uses `String(500)` for `original_name`. Long filenames would fail at DB level with unclear error.

**Fix**: Add length check in ingestors before calling `create_file`:
```python
if len(original_name) > 500:
    raise ValueError("Filename too long (max 500 characters)")
```

---

## Positive Findings

1. **Good**: Database session management is correct - uses `get_session` dependency which handles commit/rollback properly.

2. **Good**: Error handling is comprehensive - catches specific exceptions and re-raises with context.

3. **Good**: All CRUD operations use async sessions correctly.

4. **Good**: Qdrant client lazy initialization is well-implemented.

5. **Good**: All 18 tests passing.

6. **Good**: Settings MB-to-bytes conversion is correct (verified via hex check).

7. **Good**: File deletion uses best-effort atomicity with proper logging.

---

## Recommendations

1. **HIGH**: Add overlap_fraction validation in chunking.py to prevent infinite loops.

2. **MEDIUM**: Add case-insensitive content-type comparison in API routes.

3. **MEDIUM**: Add filename length validation in ingestors.

4. **LOW**: Fix "ingest" typo throughout codebase for professionalism.

5. **LOW**: Fix extra brace in conftest.py mock.

---

## Test Coverage

- Existing tests: 18 tests across 7 test files
- All tests passing
- Missing tests for:
  - Edge case: overlap_fraction >= 1.0 (needs test)
  - Edge case: Filename length validation (needs test)
  - Integration: File deletion rollback scenarios
  - Integration: Case-insensitive content-type handling
