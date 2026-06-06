# Feature Specification: Ingestion Pipeline

**Feature Branch**: `002-ingestion-pipeline`
**Created**: 2026-05-19
**Status**: Draft
**Input**: User description: "read plan.md file and creat a specification for the phase 2 Ingestion Pipeline"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PDF Document Ingestion (Priority: P1)

An industrial engineer uploads equipment manuals, technical specifications, and maintenance guides as PDF documents. The system processes these documents, extracts their content, and makes them searchable for future queries.

**Why this priority**: PDF manuals are the primary knowledge source for industrial equipment. Without PDF ingestion, the core value proposition of the system (searching technical documentation) cannot be delivered.

**Independent Test**: An engineer can upload a sample equipment manual PDF, verify it appears in the knowledge base with an "indexed" status, and successfully query information from that PDF.

**Acceptance Scenarios**:

1. **Given** the system is running and Qdrant collection exists, **When** an engineer uploads a valid PDF file under the size limit, **Then** the file is saved to disk, uploaded to the document processor, metadata is recorded in the database, and the file appears in the knowledge base with "indexed" status
2. **Given** a PDF is being processed, **When** processing completes successfully, **Then** the file status updates to "indexed" and the document is retrievable via search
3. **Given** the file size limit is 100 MB, **When** an engineer uploads a PDF exceeding 100 MB, **Then** the upload is rejected with a clear error message indicating the size limit
4. **Given** the system is running, **When** an engineer attempts to upload a non-PDF file to the PDF endpoint, **Then** the upload is rejected with a clear error message indicating the invalid file type
5. **Given** an uploaded PDF, **When** the external document processing service is unavailable, **Then** the file status is marked as "failed" and a clear error message is shown to the user

---

### User Story 2 - Audio Transcription and Indexing (Priority: P1)

An industrial engineer uploads audio recordings of technician discussions, maintenance briefings, or equipment operation notes. The system transcribes the audio, chunks the transcript, and indexes the chunks for retrieval.

**Why this priority**: Audio recordings contain valuable tacit knowledge from field technicians that is not documented elsewhere. Enabling audio ingestion captures this knowledge that would otherwise be lost.

**Independent Test**: An engineer can upload an audio recording, verify that the full transcript is stored in the database with duration and language metadata, and successfully query information from the transcript content.

**Acceptance Scenarios**:

1. **Given** the system is running with a transcriber model available, **When** an engineer uploads a supported audio file (MP3, WAV, M4A, OGG), **Then** the file is saved to disk, transcribed, the transcript is chunked, chunks are embedded, and the indexed content appears in the knowledge base
2. **Given** an audio file is uploaded, **When** transcription completes, **Then** the full transcript text, duration in seconds, and detected language are stored in the database
3. **Given** an audio file is uploaded, **When** transcript chunks are created, **Then** each chunk is approximately 500 tokens, embedded using the embedding model, and stored in the vector database with metadata including file ID and chunk index
4. **Given** a system with GPU available, **When** audio transcription is performed, **Then** GPU is automatically detected and used for faster transcription
5. **Given** no GPU is available, **When** audio transcription is performed, **Then** the system falls back to CPU mode with appropriate quantization and logs a warning about slower performance
6. **Given** the file size limit is 100 MB, **When** an engineer uploads an audio file exceeding 100 MB, **Then** the upload is rejected with a clear error message indicating the size limit

---

### User Story 3 - Image OCR and Analysis (Priority: P2)

An industrial engineer uploads photos of equipment nameplates, gauges, schematics, or inspection results. The system extracts text and scene understanding from images using vision capabilities.

**Why this priority**: Images provide visual context that text documents cannot capture. While valuable, this is P2 because text-based queries are the primary use case and image OCR can be a secondary feature.

**Independent Test**: An engineer can upload an equipment nameplate photo, verify that the extracted text contains readable information from the image, and successfully query information from that image.

**Acceptance Scenarios**:

1. **Given** the system is running with a vision model available, **When** an engineer uploads a supported image file (JPEG, PNG, WebP), **Then** the file is saved to disk, processed for OCR, and the extracted text is stored in the database
2. **Given** an image file is uploaded, **When** OCR processing completes, **Then** the extracted text, model used, and timestamp are stored in the database and the image appears in the OCR history gallery
3. **Given** the file size limit is 25 MB, **When** an engineer uploads an image exceeding 25 MB, **Then** the upload is rejected with a clear error message indicating the size limit
4. **Given** an image with no readable text, **When** OCR processing completes, **Then** the system stores an empty or minimal extracted text and marks the operation as completed
5. **Given** the vision model is unavailable, **When** an engineer attempts to upload an image, **Then** the upload is rejected with a clear error message indicating the service is unavailable

---

### User Story 4 - File Management and Deletion (Priority: P2)

An industrial engineer manages their knowledge base by viewing uploaded files, deleting files that are no longer needed, and verifying that deleted files are completely removed from all storage locations.

**Why this priority**: Users need the ability to maintain a clean knowledge base and remove outdated or incorrect files. This is P2 because the core value is ingestion, but file management is necessary for long-term usability.

**Independent Test**: An engineer can view all uploaded files with their metadata, delete a file, and verify it is removed from disk, database, and vector store.

**Acceptance Scenarios**:

1. **Given** multiple files of different types have been uploaded, **When** an engineer views the documents tab, **Then** all files are displayed in a grid with filename, file type, size, upload date, and indexing status
2. **Given** a file is uploaded and indexed, **When** an engineer deletes the file, **Then** the file is removed from disk storage, the file record is removed from the database, and associated chunks are removed from the vector store
3. **Given** a file is being deleted, **When** the deletion operation fails for one storage location, **Then** the user receives a clear error message and the system provides details about which deletion step failed
4. **Given** files are displayed in the documents tab, **When** an engineer filters by file type, **Then** only files of the selected type are displayed
5. **Given** files are displayed in the documents tab, **When** an engineer sorts by date or size, **Then** the files are reordered according to the selected sort criteria

---

### Edge Cases

- What happens when an uploaded file has a filename with special characters or exceeds 255 characters?
- How does the system handle corrupted or password-protected PDF files?
- What happens when an audio file contains no speech (silence or background noise only)?
- How does the system handle an image upload when the vision model times out during processing?
- What happens when the vector database connection fails during chunk insertion?
- How does the system handle concurrent uploads from multiple users?
- What happens when disk space is insufficient for saving uploaded files?
- How does the system handle an incomplete file upload due to network interruption?
- What happens when a previously processed file is re-uploaded with the same filename?
- How does the system handle files that exceed processing time limits?

## Requirements *(mandatory)*

### Functional Requirements

#### PDF Ingestion Requirements

- **FR-001**: System MUST accept PDF files up to 100 MB in size
- **FR-002**: System MUST validate that uploaded files have the MIME type "application/pdf"
- **FR-003**: System MUST save uploaded PDF files to a dedicated uploads directory with a unique identifier
- **FR-004**: System MUST send PDF files to the document processing service for content extraction and indexing
- **FR-005**: System MUST poll the document processing service for indexing status until completion
- **FR-006**: System MUST store PDF metadata in the database including file ID, original filename, file type, disk path, size, processing service ID, and indexing status
- **FR-007**: System MUST update the indexing status to "indexed" when document processing completes successfully
- **FR-008**: System MUST update the indexing status to "failed" when document processing fails and capture the error details
- **FR-009**: System MUST reject PDF uploads exceeding 100 MB with an HTTP 413 error and descriptive message

#### Audio Ingestion Requirements

- **FR-010**: System MUST accept audio files up to 100 MB in size
- **FR-011**: System MUST accept audio files with MIME types: audio/mpeg, audio/wav, audio/m4a, audio/ogg, audio/mp4
- **FR-012**: System MUST save uploaded audio files to a dedicated audio directory with a unique identifier
- **FR-013**: System MUST transcribe audio files using the configured transcriber model
- **FR-014**: System MUST detect available GPU and use it for transcription when available
- **FR-015**: System MUST fall back to CPU mode with appropriate quantization when GPU is unavailable
- **FR-016**: System MUST chunk transcribed text into segments of approximately 500 tokens using semantic chunking
- **FR-017**: System MUST embed each chunk using the configured embedding model
- **FR-018**: System MUST store embedded chunks in the vector database with metadata including file ID, file type, chunk index, and creation timestamp
- **FR-019**: System MUST store the full transcript, duration in seconds, and detected language in the database
- **FR-020**: System MUST log the detected device (GPU or CPU) when transcription begins

#### Image OCR Requirements

- **FR-021**: System MUST accept image files up to 25 MB in size
- **FR-022**: System MUST accept image files with MIME types: image/jpeg, image/png, image/webp
- **FR-023**: System MUST save uploaded image files to a dedicated images directory with a unique identifier
- **FR-024**: System MUST send images to the vision model for text extraction and scene understanding
- **FR-025**: System MUST store extracted text, model used, and timestamp in the database
- **FR-026**: System MUST return the file ID and extracted text upon successful OCR processing
- **FR-027**: System MUST store processed images for display in the OCR history gallery

#### File Management Requirements

- **FR-028**: System MUST provide a list of all uploaded files with filename, file type, size, upload date, and indexing status
- **FR-029**: System MUST support filtering files by type (All, PDF, Audio, Image)
- **FR-030**: System MUST support sorting files by upload date (newest/oldest) and name (A-Z)
- **FR-031**: System MUST delete files from disk storage when requested
- **FR-032**: System MUST delete file records from the database when requested
- **FR-033**: System MUST delete associated chunks from the vector database when a file is deleted
- **FR-034**: System MUST ensure atomic deletion across all storage locations or roll back with clear error messaging
- **FR-035**: System MUST sanitize filenames to prevent path traversal attacks and limit to 255 characters

#### Hybrid Search Requirements

- **FR-036**: System MUST generate dense vectors for text queries using the configured embedding model (768 dimensions)
- **FR-037**: System MUST tokenize queries for sparse BM25 vector generation
- **FR-038**: System MUST query the vector database using both dense and sparse vectors
- **FR-039**: System MUST combine search results using Reciprocal Rank Fusion (RRF)
- **FR-040**: System MUST return the top 5 most relevant chunks from search results
- **FR-041**: System MUST include similarity scores and source metadata in search results

#### API Requirements

- **FR-042**: System MUST provide a POST endpoint for PDF ingestion accepting multipart/form-data
- **FR-043**: System MUST provide a POST endpoint for audio ingestion accepting multipart/form-data
- **FR-044**: System MUST provide a POST endpoint for image ingestion accepting multipart/form-data
- **FR-045**: System MUST return a JSON response with file ID, filename, and status for all ingestion endpoints
- **FR-046**: System MUST provide a GET endpoint to list all files with filtering and sorting support
- **FR-047**: System MUST provide a DELETE endpoint to remove a file by ID
- **FR-048**: System MUST return HTTP 413 (Payload Too Large) when file size limits are exceeded
- **FR-049**: System MUST return HTTP 415 (Unsupported Media Type) when file type is invalid

### Key Entities

- **IngestedFile**: Represents a file uploaded by a user containing metadata (ID, original filename, file type, disk path, size, indexing status, creation timestamp, external service ID for PDFs)
- **Transcript**: Represents the transcribed text from an audio file containing the full transcript, duration in seconds, detected language, and file reference
- **OCRResult**: Represents the text extracted from an image via OCR containing the extracted text, model used, creation timestamp, and file reference
- **Chunk**: Represents a segment of transcribed text that has been embedded and stored in the vector database containing the chunk text, dense vector, sparse vector, chunk index, file ID, file type, and creation timestamp

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 100 MB PDF file can be successfully uploaded and indexed in under 5 minutes
- **SC-002**: A 10-minute audio recording can be transcribed and indexed in under 3 minutes on GPU hardware
- **SC-003**: An image can be processed for OCR with text extraction in under 10 seconds
- **SC-004**: File deletion removes all traces from disk, database, and vector database within 2 seconds
- **SC-005**: Hybrid search returns relevant results from previously ingested PDF, audio, and image content within 500 milliseconds
- **SC-006**: The system can process 10 concurrent file uploads without degradation in processing time
- **SC-007**: 95% of file uploads complete successfully with proper indexing on first attempt
- **SC-008**: Users can filter and sort their knowledge base files within 1 second
- **SC-009**: GPU audio transcription is at least 5 times faster than CPU fallback mode
- **SC-010**: System correctly identifies and uses GPU when available with 100% accuracy

## Assumptions

- The external document processing service (GroundX) provides a free tier suitable for the initial implementation
- The embedding model (nomic-embed-text) produces 768-dimensional vectors compatible with the vector database
- The vision model (Gemma4) provides sufficient OCR capabilities for industrial nameplates and gauges
- Faster-whisper transcription model is available and compatible with the system environment
- Users primarily upload files in the specified supported formats and MIME types
- File uploads occur during active user sessions rather than automated batch processing
- The vector database (Qdrant) maintains connection and availability during ingestion operations
- Disk space for uploaded files is managed by the user and does not require automatic cleanup
- Concurrent uploads are limited to a reasonable number (less than 10 simultaneous uploads)
- Network connectivity to external services is stable during processing operations
- Industrial engineers primarily work with English language content for transcriptions
