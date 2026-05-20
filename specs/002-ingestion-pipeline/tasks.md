# Tasks: Ingestion Pipeline

**Input**: Design documents from `specs/002-ingestion-pipeline/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md

**Tests**: Tests are OPTIONAL for Phase 2 - focus on getting ingestion infrastructure running first.

**Organization**: Tasks organized by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project structure initialization for ingestion modules

- [X] T001 Create backend/core/ingestion/ directory structure with __init__.py files
- [X] T002 Create backend/core/retrieval/ directory structure with __init__.py files
- [X] T003 [P] Create tests/fixtures/sample_files/ directory for test files

**Checkpoint**: Ingestion module structure created - ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Add groundx-python-sdk dependency to requirements.txt
- [X] T005 [P] Add faster-whisper dependency to requirements.txt
- [X] T006 [P] Add python-magic dependency to requirements.txt
- [X] T007 [P] Create backend/core/retrieval/__init__.py
- [X] T008 [P] Create backend/core/ingestion/__init__.py
- [X] T009 [P] Create backend/core/models/ollama_client.py with embedding support
- [X] T010 [P] Create backend/database/crud.py with File, Transcript, OCRResult CRUD functions
- [X] T011 [P] Create backend/schemas/ingest.py with Pydantic request/response models

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - PDF Document Ingestion (Priority: P1) 🎯 MVP

**Goal**: Industrial engineers can upload PDF documents which are processed via GroundX and made searchable.

**Independent Test**: An engineer can upload a sample equipment manual PDF, verify it appears in the knowledge base with "indexed" status, and successfully query information from that PDF.

### Implementation for User Story 1

- [X] T012 [US1] Create backend/core/retrieval/groundx_client.py with GroundX SDK integration, PDF upload, and status polling
- [X] T013 [US1] Create backend/core/ingestion/pdf_ingestor.py with PDF upload to GroundX, indexing status polling, and database persistence
- [X] T014 [US1] Create backend/api/routes/ingest.py with POST /api/ingest/pdf endpoint accepting multipart/form-data, file validation (100 MB limit, application/pdf MIME), and error handling (413, 415, 500)
- [X] T015 [US1] Implement PDF file creation in backend/database/crud.py (create_file with file_type="pdf", indexing_status="pending", groundx_id tracking)
- [X] T016 [US1] Implement PDF status update in backend/database/crud.py (update_file_indexing_status to handle "processing", "indexed", "failed" states with error_message)
- [X] T017 [US1] Create frontend/components/file_uploader.py with PDF file upload widget, progress bar, and error toast notifications
- [X] T018 [US1] Create frontend/components/file_card.py with file display card showing filename, type, size, date, and indexing status badge
- [X] T019 [US1] Create frontend/components/status_badge.py with visual status indicator (indexed, processing, failed with color coding)
- [X] T020 [US1] Create frontend/tabs/documents_tab.py with file grid view, filtering by file type, and sorting by date/name
- [X] T021 [US1] Create frontend/utils/file_helpers.py with file size formatting helper and type icon mapping

**Checkpoint**: PDF ingestion fully functional and independently testable

---

## Phase 4: User Story 2 - Audio Transcription and Indexing (Priority: P1) 🎯 MVP

**Goal**: Industrial engineers can upload audio recordings which are transcribed, chunked, embedded, and indexed in Qdrant.

**Independent Test**: An engineer can upload an audio recording, verify that the full transcript is stored in the database with duration and language metadata, and successfully query information from that transcript.

### Implementation for User Story 2

- [X] T022 [US2] Create backend/core/ingestion/audio_ingestor.py with Whisper GPU/CPU detection function (torch.cuda.is_available() with CPU fallback and "int8" quantization)
- [X] T023 [US2] Create backend/core/ingestion/chunking.py with token-based semantic chunking (~500 tokens, 10% overlap) using tiktoken tokenizer, and implement transcript chunking in backend/core/ingestion/audio_ingestor.py using this module
- [X] T024 [US2] Implement audio transcription in backend/core/ingestion/audio_ingestor.py using Faster-Whisper with detected device, duration calculation, and language detection
- [X] T025 [US2] Implement chunk embedding in backend/core/ingestion/audio_ingestor.py using nomic-embed-text via Ollama (768 dimensions) - Covers FR-036 (chunk storage with metadata including file_id reference)
- [X] T026 [US2] Implement Qdrant chunk insertion in backend/core/ingestion/audio_ingestor.py with metadata (file_id, file_type="audio", chunk_index, chunk_text, created_at)
- [X] T027 [US2] Create backend/api/routes/ingest.py with POST /api/ingest/audio endpoint accepting multipart/form-data, file validation (100 MB limit, audio MIME types: audio/mpeg, audio/wav, audio/m4a, audio/ogg), and error handling
- [X] T028 [US2] Implement Transcript creation in backend/database/crud.py (create_transcript with file_id, transcript_text, duration_seconds, language)
- [X] T029 [US2] Update frontend/components/file_uploader.py to support audio file uploads with type icons
- [X] T030 [US2] Update frontend/components/file_card.py to display transcript summary (duration, language) for audio files
- [X] T031 [US2] Update backend/core/models/ollama_client.py to include embed_text function for chunk embedding

**Checkpoint**: Audio transcription and indexing fully functional and independently testable

---

## Phase 5: User Story 3 - Image OCR and Analysis (Priority: P2)

**Goal**: Industrial engineers can upload images which are processed via Gemma4 vision for OCR, with extracted text stored for retrieval.

**Independent Test**: An engineer can upload an equipment nameplate photo, verify that extracted text contains readable information from the image, and successfully query information from that image.

### Implementation for User Story 3

- [X] T032 [US3] Create backend/core/ingestion/image_processor.py with Gemma4 vision integration for OCR processing
- [X] T033 [US3] Implement image OCR in backend/core/ingestion/image_processor.py sending image to Gemma4 vision with text extraction prompt
- [X] T034 [US3] Implement OCR result storage in backend/core/ingestion/image_processor.py (extracted_text, model_used="gemma4", creation timestamp)
- [X] T035 [US3] Create backend/api/routes/ingest.py with POST /api/ingest/image endpoint accepting multipart/form-data, file validation (25 MB limit, image MIME types: image/jpeg, image/png, image/webp), and error handling
- [X] T036 [US3] Implement OCRResult creation in backend/database/crud.py (create_ocr_result with file_id, extracted_text, model_used)
- [X] T037 [US3] Update frontend/components/file_uploader.py to support image file uploads with type icons
- [X] T038 [US3] Update frontend/components/file_card.py to display OCR summary (extracted text preview) for image files

**Checkpoint**: Image OCR fully functional and independently testable

---

## Phase 6: User Story 4 - File Management and Deletion (Priority: P2)

**Goal**: Industrial engineers can manage their knowledge base by viewing uploaded files with filtering and sorting, and deleting files which removes data from all storage locations.

**Independent Test**: An engineer can view all uploaded files with their metadata, delete a file, and verify it is removed from disk, database, and vector store.

### Implementation for User Story 4

**Note**: Deletion tasks (T041-T045) are distributed to handle atomic deletion across all storage layers (disk, SQLite database, Qdrant vector store, and related entities like Transcripts/OCRResult). This ensures transactional consistency - if any deletion fails, all completed deletions are rolled back.

- [X] T039 [US4] Create backend/api/routes/files.py with GET /api/files endpoint supporting query parameters (type for filtering: all/pdf/audio/image, sort: date_desc/date_asc/name, limit for pagination)
- [X] T040 [US4] Implement file listing in backend/api/routes/files.py with file type filtering and sorting logic
- [X] T041 [US4] Implement file metadata enrichment in backend/api/routes/files.py to include transcript_summary for audio files and ocr_summary for image files
- [X] T042 [US4] Create DELETE /api/files/{id} endpoint in backend/api/routes/files.py with file deletion logic
- [X] T043 [US4] Implement atomic file deletion in backend/database/crud.py (delete_file) with transaction handling across disk storage, database (IngestedFile, Transcript, OCRResult), and Qdrant (chunk deletion by file_id filter)
- [X] T044 [US4] Implement Qdrant chunk deletion in backend/core/retrieval/qdrant_client.py (delete_by_file_id function) with scroll API
- [X] T045 [US4] Create frontend/components/delete_confirmation.py with modal for delete confirmation
- [X] T046 [US4] Update frontend/tabs/documents_tab.py with delete button integration and confirmation modal trigger
- [X] T047 [US4] Implement file deletion rollback in backend/database/crud.py (attempt to restore database records if Qdrant deletion succeeds but disk deletion fails)

**Checkpoint**: File management fully functional with atomic deletion across all storage locations

---

## Phase 7: Hybrid Search Infrastructure (Cross-Cutting)

**Purpose**: Implement hybrid dense + sparse search with RRF fusion for cross-file-type retrieval (needed for US1 and US2).

- [X] T049 [P] Create backend/core/retrieval/qdrant_client.py with Qdrant async client setup, collection initialization, and connection handling
- [X] T050 [P] Implement dense vector generation in backend/core/retrieval/qdrant_client.py using nomic-embed-text via Ollama (768 dimensions)
- [X] T051 [P] Implement sparse BM25 tokenization in backend/core/retrieval/qdrant_client.py for query terms
- [X] T052 [P] Implement hybrid query in backend/core/retrieval/qdrant_client.py using both dense and sparse vectors via Qdrant query_points API
- [X] T053 [P] Implement RRF (Reciprocal Rank Fusion) in backend/core/retrieval/fusion.py with k=60 constant, score combination logic
- [X] T054 [P] Integrate RRF results in backend/core/retrieval/qdrant_client.py (combine dense and sparse search results using fusion.py)

**Checkpoint**: Hybrid search infrastructure ready for cross-file-type retrieval

---

## Phase 8: Validation

**Purpose**: Verify everything works and meets acceptance criteria

- [X] T048 Test PDF ingestion endpoint with valid 100 MB PDF file and verify GroundX upload, status polling, and final "indexed" status
- [X] T049 Test PDF ingestion with invalid file type (image/jpeg) and verify HTTP 415 error response
- [X] T050 Test PDF ingestion with oversized file (150 MB) and verify HTTP 413 error with size details
- [X] T051 Test audio ingestion endpoint with valid 10 MB MP3 file and verify transcription, chunking, embedding, and Qdrant insertion
- [X] T052 Test audio ingestion with invalid file type (video/mp4) and verify HTTP 415 error response
- [X] T053 Test audio ingestion with oversized file (120 MB) and verify HTTP 413 error with size details
- [X] T054 Verify GPU detection logs correct device (torch.cuda.is_available() returns "cuda" or "cpu")
- [X] T055 Verify audio chunks are approximately 500 tokens with 10% overlap
- [X] T056 Test image ingestion endpoint with valid 10 MB JPEG file and verify OCR text extraction and storage
- [X] T057 Test image ingestion with invalid file type (application/pdf) and verify HTTP 415 error response
- [X] T058 Test image ingestion with oversized file (30 MB) and verify HTTP 413 error with size details
- [X] T059 Test file listing endpoint with default parameters (all files, date_desc sort)
- [X] T060 Test file listing with type filter (only PDF files)
- [X] T061 Test file listing with sort parameters (date_asc for oldest first, name for A-Z)
- [X] T062 Test file deletion with valid file ID and verify removal from disk, database, and Qdrant chunks
- [X] T063 Test file deletion with invalid file ID and verify HTTP 404 error response
- [X] T064 Test hybrid search with ingested PDF, audio, and image content and verify cross-file-type retrieval using RRF
- [X] T065 Verify file deletion is atomic (all or nothing - if any storage location fails, rollback occurs)
- [X] T066 Verify frontend displays correct file type icons and status badges
- [X] T067 Verify frontend file card shows correct metadata for each file type (transcript summary for audio, OCR preview for images)

**Checkpoint**: All validation tests pass - ingestion pipeline is complete and ready for Phase 3 (LangGraph Agent)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
- **Hybrid Search (Phase 7)**: Depends on Foundational phase - Enables US1 and US2 retrieval
- **Validation (Phase 8)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P2)**: Depends on Foundational (Phase 2) and US1/US2/US3 (needs files to manage)

### Within Each User Story

- Tests (if present) must be written and failing before implementation
- Models and services before API endpoints
- Core implementation before integration
- Story complete before moving to next story

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 can run in parallel (different directories, no dependencies)
- **Phase 2**: T004, T005, T006 can run in parallel (different dependencies), T007, T008, T009, T010, T011 can run in parallel (different files)
- **Phase 3 (US1)**: T014, T015, T016 can run in parallel (different files), T017, T018, T019, T020 can run in parallel (different components), T021 depends on T020
- **Phase 4 (US2)**: T022, T023 can run in parallel (different modules), T024, T025, T026 can run in sequence (T023→T024→T025→T026), T027, T028, T029, T030, T031 can run in parallel with core modules, T031 depends on T030
- **Phase 5 (US3)**: T032, T033, T034 can run in sequence (T032→T033→T034), T035, T036, T037 can run in parallel (different files), T038 can run in parallel with T037
- **Phase 6 (US4)**: T039, T040, T041, T042 can run in sequence (T039→T040→T041→T042), T043, T044, T045 can run in parallel (different files), T046, T047 can run in parallel with T045, T039, T040, T041, T042
- **Phase 7 (Cross-Cutting)**: T048, T049, T050 can run in sequence (T048→T049→T050), T051, T052 can run in parallel (different files), T053 depends on T051 and T052
- **Phase 8 (Validation)**: All tasks sequential validation steps

---

## Parallel Example: Phase 2 Foundational Tasks

```bash
# Launch all dependency addition tasks in parallel:
Task: "Add groundx-python-sdk dependency to requirements.txt"
Task: "Add faster-whisper dependency to requirements.txt"
Task: "Add python-magic dependency to requirements.txt"

# Launch all module initialization tasks in parallel:
Task: "Create backend/core/retrieval/__init__.py"
Task: "Create backend/core/ingestion/__init__.py"

# Launch all core implementation tasks in parallel:
Task: "Create backend/core/models/ollama_client.py with embedding support"
Task: "Create backend/database/crud.py"
Task: "Create backend/schemas/ingest.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-2 Only - P1 Priority)

1. Complete Phase 1: Setup (project structure)
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (PDF Ingestion)
4. Complete Phase 4: User Story 2 (Audio Transcription)
5. Complete Phase 7: Hybrid Search (needed for US1 and US2 retrieval)
6. Complete Phase 8: Validation for US1 and US2
7. **STOP and VALIDATE**: User Stories 1 and 2 are fully functional with cross-file-type search

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready for ingestion
2. Add User Stories 1-2 (P1) → Test independently → Validate
3. Add User Stories 3-4 (P2) → Test independently → Validate
4. Add Hybrid Search → Validate cross-file-type retrieval
5. Each story adds ingestion capability without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (PDF) + Hybrid Search integration
   - Developer B: User Story 2 (Audio) + Hybrid Search integration
   - Developer C: User Story 3 (Image OCR)
   - Developer D: User Story 4 (File Management)
3. Stories complete and integrate independently
4. Team completes Validation together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Stories 1-2 are P1 (critical for MVP)
- User Stories 3-4 are P2 (important but can follow MVP)
- Tests are optional for Phase 2 - focus on infrastructure first
- Validation requires all services running (Qdrant, GroundX, Ollama)
- Database CRUD operations must use SQLAlchemy async API (aiosqlite)
- File ID generation uses UUID for all file types
- Chunking produces ~500 token segments with 10% overlap for context preservation
- Hybrid search uses RRF with k=60 for dense + sparse fusion
