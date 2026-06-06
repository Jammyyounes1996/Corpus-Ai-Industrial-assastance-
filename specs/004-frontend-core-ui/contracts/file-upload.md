# Contract: File Upload

## Contract status

Compatible with pre-send attachment upload only if the frontend uses the existing type-specific ingestion endpoints. There is no generic upload endpoint and no multi-file upload endpoint.

## Endpoint paths

- PDF: `/api/ingest/pdf`
- Audio: `/api/ingest/audio`
- Image: `/api/ingest/image`

## HTTP method

`POST`

## Request format

`multipart/form-data` with one field:

- `file`: the uploaded file.

Each request accepts exactly one file. Multiple selected files require multiple requests.

## Accepted file types

PDF endpoint accepts:

- `application/pdf`

Audio endpoint accepts:

- `audio/mpeg`
- `audio/wav`
- `audio/x-wav`
- `audio/m4a`
- `audio/x-m4a`
- `audio/ogg`
- `audio/mp4`

Image endpoint accepts:

- `image/jpeg`
- `image/png`
- `image/webp`

## Size limits

Configured in backend settings:

- PDF: `MAX_PDF_SIZE_MB`, default `100` MB.
- Audio: `MAX_AUDIO_SIZE_MB`, default `100` MB.
- Image: `MAX_IMAGE_SIZE_MB`, default `25` MB.

Backend returns `413` when an ingestion validator reports a file exceeds the limit.

## Multiple file behavior

- Backend endpoints accept one `UploadFile` each.
- Frontend must upload files sequentially or concurrently as separate requests.
- Frontend must cap successful attachment references to `MAX_ATTACHED_FILES`, default `10`.
- Failed uploads must not block already successful uploads unless the user chooses to cancel the send.

## Success response schema

Common successful fields confirmed from ingestion services:

```json
{
  "file_id": "string",
  "filename": "string",
  "status": "processing | indexed",
  "size_bytes": 0
}
```

Type-specific fields may be present:

- Audio: `duration_seconds`, `language`.
- Image: `extracted_text`.
- PDF: usually returns `status: "processing"` because GroundX indexing is asynchronous.

## Failed response schema

Unsupported media type:

```json
{
  "detail": {
    "error": "UnsupportedMediaType",
    "message": "Invalid content type: ..."
  }
}
```

Payload too large:

```json
{
  "detail": {
    "error": "PayloadTooLarge",
    "message": "..."
  }
}
```

Validation failure:

```json
{
  "detail": {
    "error": "ValidationError",
    "message": "..."
  }
}
```

Unhandled server errors may use the global error shape:

```json
{
  "error": "ExceptionType",
  "message": "..."
}
```

## Example upload response

```json
{
  "file_id": "4f8d0d9e-7d3d-4d58-9f90-5c14e7e2a001",
  "filename": "startup-procedure.pdf",
  "status": "processing",
  "size_bytes": 2411720
}
```

## Attachment reference shape

The chat stream endpoint accepts attachment references as a list of file ID strings:

```json
{
  "attached_files": ["4f8d0d9e-7d3d-4d58-9f90-5c14e7e2a001"]
}
```

## How attachment references are passed into chat stream

1. Upload each selected file to the matching `/api/ingest/*` endpoint.
2. Collect `file_id` from each successful response.
3. Pass only those `file_id` strings in `attached_files` when calling `POST /api/chat/{chat_id}/stream`.
4. Do not pass browser `File` objects, filenames, local paths, or temporary IDs to chat streaming.

## Partial failure behavior

- If one upload fails and others succeed, keep successful file IDs available.
- Show the failed file with its backend error message.
- Before sending chat, either require the user to remove failed files or retry them.
- Never include failed upload references in `attached_files`.

## Frontend validation rules

- Choose endpoint by MIME type.
- Reject unsupported MIME types before upload when possible.
- Enforce known size limits client-side where available.
- Limit attached files to backend `MAX_ATTACHED_FILES`, default `10`.
- Treat PDF `processing` as a real backend state, not as a completed/indexed state.
