# Quickstart: Ingestion Pipeline

**Feature**: Phase 2 - Ingestion Pipeline
**Date**: 2026-05-19

This guide provides step-by-step instructions for testing the ingestion pipeline after implementation.

## Prerequisites

1. **Backend running**:
   ```bash
   cd industrial-ai-assistant
   conda activate industrial-ai
   uvicorn backend.main:app --reload
   ```

2. **Qdrant running**:
   ```bash
   docker-compose up -d qdrant
   ```

3. **Ollama running**:
   ```bash
   ollama serve
   ```

4. **Required models pulled**:
   ```bash
   ollama pull gemma4:e4b
   ollama pull nomic-embed-text
   ```

5. **GroundX API key configured** (for PDF ingestion):
   - Add `GROUNDX_API_KEY` to `.env` file
   - Sign up at [eyelevel.ai](https://eyelevel.ai) for free tier

---

## Testing PDF Ingestion

### Upload a PDF

```bash
# Upload a sample PDF file
curl -X POST http://localhost:8000/api/ingest/pdf \
  -H "accept: application/json" \
  -F "file=@path/to/manual.pdf"
```

### Expected Response (200)
```json
{
  "file_id": "550e8400-e29b-41d4-a716-44665544010",
  "filename": "pump_manual.pdf",
  "status": "processing",
  "size_bytes": 5242880
}
```

### Check Status

After a few seconds, check if file is indexed:

```bash
# List all files
curl http://localhost:8000/api/files | jq '.files[] | select(.filename=="pump_manual.pdf")'
```

Expected status: `"indexed"` (may take 1-5 minutes depending on PDF size)

### Verify in Qdrant

```bash
# Check Qdrant for chunks
curl http://localhost:6333/collections/industrial_assistant/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "with_payload": true, "filter": {"must": [{"key": "file_id", "match": {"any": ["550e8400-e29b-41d4-a716-44665544010"]}}]}}' \
  | jq '.result.points[0].payload'
```

---

## Testing Audio Ingestion

### Upload an Audio File

```bash
# Upload a sample audio file
curl -X POST http://localhost:8000/api/ingest/audio \
  -H "accept: application/json" \
  -F "file=@path/to/recording.mp3"
```

### Expected Response (200)
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

Note: Duration and language are available immediately because transcription happens synchronously.

### Check for Indexed Chunks

```bash
# Get file details
curl http://localhost:8000/api/files | jq '.files[] | select(.filename=="technician_briefing.mp3")'
```

Expected status: `"indexed"` (may take 30 seconds to 5 minutes depending on audio length and GPU availability)

### Verify in Qdrant

```bash
# Check for audio chunks
curl http://localhost:6333/collections/industrial_assistant/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "with_payload": true, "filter": {"must": [{"key": "file_type", "match": {"value": "audio"}}]}}' \
  | jq '.result.points[].payload | {chunk_index, chunk_text}'
```

---

## Testing Image OCR

### Upload an Image

```bash
# Upload a sample image
curl -X POST http://localhost:8000/api/ingest/image \
  -H "accept: application/json" \
  -F "file=@path/to/nameplate.jpg"
```

### Expected Response (200)
```json
{
  "file_id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c",
  "filename": "nameplate_photo.jpg",
  "status": "indexed",
  "extracted_text": "MODEL: X-500\nSERIAL: 12345\nVOLTAGE: 480V\nAMPERAGE: 45A"
}
```

Note: Images are processed synchronously, so status is immediately `"indexed"`.

---

## Testing File Management

### List All Files

```bash
# Get all files
curl http://localhost:8000/api/files
```

### Filter by Type

```bash
# Get only PDF files
curl "http://localhost:8000/api/files?type=pdf"

# Get only audio files
curl "http://localhost:8000/api/files?type=audio"

# Get only image files
curl "http://localhost:8000/api/files?type=image"
```

### Sort Results

```bash
# Sort by newest first
curl "http://localhost:8000/api/files?sort=date_desc"

# Sort by oldest first
curl "http://localhost:8000/api/files?sort=date_asc"

# Sort by name A-Z
curl "http://localhost:8000/api/files?sort=name"
```

### Delete a File

```bash
# Delete by file ID
curl -X DELETE http://localhost:8000/api/files/550e8400-e29b-41d4-a716-44665544010
```

Expected: HTTP 204 No Content

---

## Verification Queries

After ingesting files, verify they are searchable (requires Phase 3 agent):

```bash
# Query ingested content (Phase 3 endpoint)
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"chat_id": null, "message": "What is the pump model?", "attached_files": []}'
```

Expected response should cite the ingested PDF as a source.

---

## Common Issues

### File Size Errors

```bash
# 413 Payload Too Large
{
  "error": "FileSizeExceeded",
  "message": "File size (150 MB) exceeds maximum allowed size (100 MB) for PDF files"
}
```

**Fix**: Reduce file size or adjust limits in `.env`:

```bash
# In .env file
MAX_PDF_SIZE_MB=150
```

### Invalid File Type Errors

```bash
# 415 Unsupported Media Type
{
  "error": "InvalidFileType",
  "message": "Invalid file type for PDF endpoint. Expected: application/pdf"
}
```

**Fix**: Ensure correct endpoint for file type:
- PDF: `/api/ingest/pdf`
- Audio: `/api/ingest/audio`
- Image: `/api/ingest/image`

### External Service Errors

```bash
# GroundX service unavailable
{
  "error": "PDFProcessingError",
  "message": "Failed to process PDF with external service"
}
```

**Fix**: Check GroundX API key in `.env`:
```bash
# In .env file
GROUNDX_API_KEY=your-key-here
```

---

## Sample Test Files

Create sample files for testing:

### Sample PDF
```bash
# Create a simple test PDF (requires reportlab)
python -c "
from reportlab.pdfgen import canvas
c = canvas('test.pdf')
c.drawString(100, 750, 'Test Equipment Manual')
c.save()
"
```

### Sample Audio
```bash
# Create a short test audio (requires pydub)
python -c "
from pydub import AudioGenerator
generator = AudioGenerator()
audio = generator.speech('This is a test audio for transcription', lang='en')
audio.export('test_audio.mp3', format='mp3')
"
```

### Sample Image
```bash
# Create a test image (requires Pillow)
python -c "
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (400, 200), color='white')
d = ImageDraw.Draw(img)
d.text((100, 100), 'Test OCR 12345', fill='black')
img.save('test_image.jpg')
"
```

---

## Performance Benchmarks

Use these commands to measure ingestion times:

```bash
# Time PDF ingestion
time curl -X POST http://localhost:8000/api/ingest/pdf -F "file=@large_manual.pdf"

# Time audio ingestion
time curl -X POST http://localhost:8000/api/ingest/audio -F "file=@long_recording.mp3"

# Time image OCR
time curl -X POST http://localhost:8000/api/ingest/image -F "file=@photo.jpg"
```

**Expected Targets** (from spec):
- PDF (100MB): < 5 minutes
- Audio (10 min): < 3 minutes (GPU) or < 30 minutes (CPU)
- Image: < 10 seconds

---

## Cleanup

Remove all test files:

```bash
# Delete all files
for file_id in $(curl -s http://localhost:8000/api/files | jq -r '.files[].id'); do
    curl -X DELETE http://localhost:8000/api/files/$file_id
done
```

---

## Next Steps

After verifying ingestion pipeline:

1. Run Phase 3: LangGraph Agent (chat + retrieval)
2. Test end-to-end: ingest file → query → get answer with source citation
3. Run `speckit-tasks` to generate implementation tasks
4. Begin implementation following the task list
