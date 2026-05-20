# API Contracts: Ingestion Pipeline

**Feature**: Phase 2 - Ingestion Pipeline
**Date**: 2026-05-19

## Overview

This document defines the API contracts for file ingestion and management endpoints. All endpoints return JSON responses with structured error handling.

## Common Patterns

### Success Response
```json
{
  "file_id": "uuid-v4-string",
  "filename": "original-name.pdf",
  "status": "indexed"
}
```

### Error Response
```json
{
  "error": "ValidationError|IngestionError|PDFProcessingError|...",
  "message": "Human-readable error description",
  "details": {
    "field": "optional_field_name",
    "value": "provided_value",
    "limit": "allowed_limit"
  }
}
```

### HTTP Status Codes
| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Resource created |
| 400 | Bad request (validation error) |
| 404 | Not found (file ID invalid) |
| 413 | Payload too large (file size exceeded) |
| 415 | Unsupported media type (invalid MIME) |
| 500 | Internal server error |

---

## POST /api/ingest/pdf

Upload a PDF document for processing and indexing.

### Request
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (form field)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| file | File | Yes | MIME type: `application/pdf`, Max size: 100 MB |

### Success Response (200)
```json
{
  "file_id": "550e8400-e29b-41d4-a716-44665544010",
  "filename": "pump_manual.pdf",
  "status": "processing",
  "size_bytes": 5242880
}
```

**Status values**:
- `processing`: File uploaded, sent to GroundX for indexing
- `indexed`: Successfully processed and searchable (for immediate completion)

### Error Responses

**413 Payload Too Large**
```json
{
  "error": "FileSizeExceeded",
  "message": "File size (150 MB) exceeds maximum allowed size (100 MB) for PDF files",
  "details": {
    "file_type": "pdf",
    "max_size_mb": 100,
    "actual_size_mb": 150
  }
}
```

**415 Unsupported Media Type**
```json
{
  "error": "InvalidFileType",
  "message": "Invalid file type for PDF endpoint. Expected: application/pdf",
  "details": {
    "expected_type": "application/pdf",
    "actual_type": "image/jpeg"
  }
}
```

**500 Internal Error** (GroundX service unavailable)
```json
{
  "error": "PDFProcessingError",
  "message": "Failed to process PDF with external service",
  "details": {
    "groundx_status_code": 503,
    "groundx_message": "Service temporarily unavailable"
  }
}
```

---

## POST /api/ingest/audio

Upload an audio file for transcription and indexing.

### Request
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (form field)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| file | File | Yes | MIME type: `audio/mpeg`, `audio/wav`, `audio/m4a`, `audio/ogg`, Max size: 100 MB |

### Success Response (200)
```json
{
  "file_id": "6c4a1f70-0e7b-4d8b-8c1d-3a8a6b42c",
  "filename": "technician_briefing.mp3",
  "status": "processing",
  "size_bytes": 12458200,
  "duration_seconds": 320.5,
  "language": "en"
}
```

**Note**: Transcription runs asynchronously. Status can be polled via GET /api/files.

### Error Responses

**413 Payload Too Large**
```json
{
  "error": "FileSizeExceeded",
  "message": "File size (120 MB) exceeds maximum allowed size (100 MB) for audio files",
  "details": {
    "file_type": "audio",
    "max_size_mb": 100,
    "actual_size_mb": 120
  }
}
```

**415 Unsupported Media Type**
```json
{
  "error": "InvalidFileType",
  "message": "Invalid file type for audio endpoint. Allowed types: audio/mpeg, audio/wav, audio/m4a, audio/ogg",
  "details": {
    "allowed_types": ["audio/mpeg", "audio/wav", "audio/m4a", "audio/ogg"],
    "actual_type": "video/mp4"
  }
}
```

**500 Internal Error** (Whisper transcription failed)
```json
{
  "error": "TranscriptionError",
  "message": "Failed to transcribe audio file",
  "details": {
    "file_id": "6c4a1f70-0e7b-4d8b-8c1d-3a8a6b42c",
    "device_used": "cpu",
    "error": "Model loading failed"
  }
}
```

---

## POST /api/ingest/image

Upload an image file for OCR processing.

### Request
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: `file` (form field)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| file | File | Yes | MIME type: `image/jpeg`, `image/png`, `image/webp`, Max size: 25 MB |

### Success Response (200)
```json
{
  "file_id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c",
  "filename": "nameplate_photo.jpg",
  "status": "indexed",
  "extracted_text": "MODEL: X-500\nSERIAL: 12345\nVOLTAGE: 480V"
}
```

**Note**: Image OCR is synchronous and completes within request (target: < 10 seconds).

### Error Responses

**413 Payload Too Large**
```json
{
  "error": "FileSizeExceeded",
  "message": "File size (30 MB) exceeds maximum allowed size (25 MB) for image files",
  "details": {
    "file_type": "image",
    "max_size_mb": 25,
    "actual_size_mb": 30
  }
}
```

**415 Unsupported Media Type**
```json
{
  "error": "InvalidFileType",
  "message": "Invalid file type for image endpoint. Allowed types: image/jpeg, image/png, image/webp",
  "details": {
    "allowed_types": ["image/jpeg", "image/png", "image/webp"],
    "actual_type": "application/pdf"
  }
}
```

**500 Internal Error** (OCR processing failed)
```json
{
  "error": "OCRError",
  "message": "Failed to extract text from image",
  "details": {
    "file_id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c",
    "model_used": "gemma4",
    "error": "Vision model timeout"
  }
}
```

---

## GET /api/files

List all uploaded files with optional filtering and sorting.

### Request
- **Method**: `GET`
- **Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| type | str | No | `"all"` | Filter by file type: `"all"`, `"pdf"`, `"audio"`, `"image"` |
| sort | str | No | `"date_desc"` | Sort order: `"date_desc"` (newest first), `"date_asc"` (oldest first), `"name"` (A-Z) |
| limit | int | No | `100` | Maximum number of results to return |

### Success Response (200)
```json
{
  "files": [
    {
      "id": "550e8400-e29b-41d4-a716-44665544010",
      "original_name": "pump_manual.pdf",
      "file_type": "pdf",
      "size_bytes": 5242880,
      "indexing_status": "indexed",
      "created_at": "2026-05-19T12:34:56.789Z",
      "transcript_summary": {
        "duration_seconds": 320.5,
        "language": "en"
      },
      "ocr_summary": {
        "text_preview": "MODEL: X-500\nSERIAL..."
      }
    },
    {
      "id": "6c4a1f70-0e7b-4d8b-8c1d-3a8a6b42c",
      "original_name": "technician_briefing.mp3",
      "file_type": "audio",
      "size_bytes": 12458200,
      "indexing_status": "indexed",
      "created_at": "2026-05-19T14:22:11.234Z",
      "transcript_summary": {
        "duration_seconds": 320.5,
        "language": "en"
      }
    }
  ],
  "total": 2,
  "page": 1,
  "has_more": false
}
```

**Note**: `transcript_summary` is only present for `file_type = "audio"`. `ocr_summary` is only present for `file_type = "image"`.

**indexing_status values**:
- `pending`: File uploaded, not yet processed
- `processing`: External/async operation in progress
- `indexed`: Successfully processed and searchable
- `failed`: Processing failed with error details

### Error Responses

**400 Bad Request** (invalid filter value)
```json
{
  "error": "ValidationError",
  "message": "Invalid filter type. Allowed values: all, pdf, audio, image",
  "details": {
    "field": "type",
    "value": "video"
  }
}
```

---

## DELETE /api/files/{id}

Delete a file and all associated data from all storage locations.

### Request
- **Method**: `DELETE`
- **Path Parameter**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | str (UUID) | Yes | File identifier to delete |

### Success Response (204)
No response body. HTTP 204 No Content.

### Error Responses

**404 Not Found**
```json
{
  "error": "FileNotFound",
  "message": "File with ID 'xyz' not found",
  "details": {
    "file_id": "xyz"
  }
}
```

**500 Internal Error** (partial deletion failure)
```json
{
  "error": "DeletionError",
  "message": "Failed to delete file from one or more storage locations",
  "details": {
    "file_id": "550e8400-e29b-41d4-a716-44665544010",
    "failed_locations": ["disk", "qdrant"],
    "succeeded_locations": ["database", "transcript"]
  }
}
```

**Note**: On partial failure, the system attempts to rollback any completed deletions to maintain consistency.
