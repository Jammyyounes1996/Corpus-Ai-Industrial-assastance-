# Quickstart: LangGraph Agent

**Phase**: 1 | **Date**: 2026-05-22 | **Status**: Complete

---

## Prerequisites

Before using the LangGraph Agent, ensure the following are complete:

1. **Phase 2 Complete**: Ingestion pipeline functional with PDFs, audio, and images indexed
2. **Backend Running**:
   ```bash
   cd industrial-ai-assistant
   conda activate industrial-ai
   uvicorn backend.main:app --reload
   ```
3. **Required Services**:
   - **Qdrant**: `docker-compose up -d qdrant`
   - **Ollama**: `ollama serve` with `gemma4:latest` model pulled
   - **GroundX**: API key configured in `.env`

---

## Testing Chat with RAG

### Step 1: Upload Test Document (if needed)

First, ensure you have content in the knowledge base. Upload a PDF:

```bash
# Upload a PDF (from Phase 2 quickstart)
curl -X POST http://localhost:8000/api/ingest/pdf \
  -H "accept: application/json" \
  -F "file=@pump_manual.pdf"
```

Expected response:
```json
{
  "file_id": "abc-123-def",
  "filename": "pump_manual.pdf",
  "file_type": "pdf",
  "status": "success",
  "chunks_created": 42
}
```

### Step 2: Ask a Question

Start a new chat session and ask a question:

```bash
# Start a new chat (chat_id: null) and ask a question
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": null,
    "message": "What is the recommended maintenance interval for the bearings?",
    "attached_files": []
  }'
```

### Step 3: Expected SSE Stream

You should see the following events stream in order:

```
event: thinking_step
data: {"step":"Analyzing your query...","status":"in_progress","node":"router_node","duration_ms":null}

event: thinking_step
data: {"step":"Analyzing your query...","status":"completed","node":"router_node","duration_ms":320}

event: thinking_step
data: {"step":"Reading PDF documents...","status":"in_progress","node":"groundx_retrieve_node","duration_ms":null}

event: thinking_step
data: {"step":"Reading PDF documents...","status":"completed","node":"groundx_retrieve_node","duration_ms":2450}

event: thinking_step
data: {"step":"Searching memory (RAG)...","status":"in_progress","node":"qdrant_retrieve_node","duration_ms":null}

event: thinking_step
data: {"step":"Searching memory (RAG)...","status":"completed","node":"qdrant_retrieve_node","duration_ms":890}

event: thinking_step
data: {"step":"Analyzing information...","status":"in_progress","node":"context_synthesis_node","duration_ms":null}

event: thinking_step
data: {"step":"Analyzing information...","status":"completed","node":"context_synthesis_node","duration_ms":210}

event: thinking_step
data: {"step":"Generating answer...","status":"in_progress","node":"answer_node","duration_ms":null}

event: token
data: {"content":"The"}

event: token
data: {"content":" recommended"}

event: token
data: {"content":" maintenance"}

event: token
data: {"content":" interval"}

event: token
data: {"content":" for"}

event: token
data: {"content":" bearings"}

event: token
data: {"content":" is"}

event: token
data: {"content":" every"}

event: token
data: {"content":" 6"}

event: token
data: {"content":" months"}

event: token
data: {"content":"."}

event: sources
data: {"sources":[{"file_id":"abc-123-def","filename":"pump_manual.pdf","file_type":"pdf","chunk_index":12,"score":0.94,"excerpt":"The bearings should be lubricated every 6 months..."}]}

event: thinking_step
data: {"step":"Generating answer...","status":"completed","node":"answer_node","duration_ms":3400}

event: done
data: {"chat_id":"550e8400-e29b-41d4-a716-44665544010","message_id":1}
```

Save the `chat_id` from the `done` event for multi-turn testing.

---

## Testing Multi-Turn Context

### Step 1: Follow-up Question

Use the `chat_id` from the previous response to ask a follow-up:

```bash
# Use chat_id from previous response
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "550e8400-e29b-41d4-a716-44665544010",
    "message": "What about the flow rate?",
    "attached_files": []
  }'
```

**Expected Behavior**:
- System maintains context about the "pump" mentioned earlier
- Answer should reference pump specifications from the same document
- Source citations should include relevant sections

---

## Testing with Attached Files

### Step 1: Upload an Image

```bash
# Upload an image (from Phase 2)
curl -X POST http://localhost:8000/api/ingest/image \
  -H "accept: application/json" \
  -F "file=@equipment_photo.jpg"
```

### Step 2: Ask About the Image

```bash
# Use the returned file_id in attached_files
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": null,
    "message": "Tell me about this equipment",
    "attached_files": ["xyz-456-ghi"]
  }'
```

**Expected Behavior**:
- OCR text from image is retrieved
- Agent incorporates OCR results into the answer
- Source citation includes the image filename

---

## Listing Chat Sessions

```bash
# Get all chat sessions
curl http://localhost:8000/api/chats | jq
```

Expected response:
```json
{
  "chats": [
    {
      "id": "550e8400-e29b-41d4-a716-44665544010",
      "title": "Pump maintenance questions",
      "model_provider": "ollama",
      "model_name": "gemma4:latest",
      "created_at": "2026-05-20T12:34:56.789Z",
      "updated_at": "2026-05-20T14:22:11.234Z",
      "message_count": 4
    }
  ],
  "total": 1
}
```

### Pagination

```bash
# Get chats with pagination
curl "http://localhost:8000/api/chats?limit=10&offset=0" | jq
```

---

## Viewing a Chat Session

```bash
# Get full chat with all messages
curl http://localhost:8000/api/chat/550e8400-e29b-41d4-a716-44665544010 | jq
```

This returns the complete conversation history with:
- All messages in chronological order
- Thinking steps for each assistant response
- Source citations for each response
- Attached files for user messages

---

## Deleting a Chat Session

```bash
# Delete a chat session
curl -X DELETE http://localhost:8000/api/chat/550e8400-e29b-41d4-a716-44665544010
```

Expected response: `204 No Content` (empty body)

After deletion, trying to access the chat returns:
```json
{
  "error": "NotFoundError",
  "message": "Chat not found: 550e8400-e29b-41d4-a716-44665544010"
}
```

---

## Testing Edge Cases

### Empty Knowledge Base

```bash
# Ask a question when no documents are ingested
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": null,
    "message": "Tell me about something random",
    "attached_files": []
  }'
```

**Expected**: Agent should indicate no relevant information found.

### Service Unavailable

```bash
# Stop Qdrant and test
docker-compose stop qdrant

curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": null,
    "message": "Test query",
    "attached_files": []
  }'
```

**Expected**: Error shown in thinking steps, graceful failure message.

### Invalid Chat ID

```bash
# Use non-existent chat_id
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "00000000-0000-0000-0000-000000000000",
    "message": "Test",
    "attached_files": []
  }'
```

**Expected**: `404 NotFound` error response.

---

## Performance Validation

### First Thinking Step Latency

Time from request to first `thinking_step` event:
- **Target**: < 3 seconds
- **How to measure**: Capture timestamp before request and after first event

### Full Answer Latency

Time from request to `done` event:
- **Target**: < 30 seconds for typical queries
- **How to measure**: Capture timestamp before request and at `done` event

### Token Streaming Latency

Time between consecutive `token` events:
- **Target**: Average < 200ms
- **How to measure**: Calculate differences between consecutive token timestamps

---

## Troubleshooting

### SSE Stream Closes Immediately

- Check backend is running: `curl http://localhost:8000/health`
- Verify no CORS errors in browser console
- Check network tab for connection status

### No Sources Returned

- Ensure documents are ingested: `curl http://localhost:8000/api/files`
- Verify Qdrant has data: `curl http://localhost:6333/collections`
- Check GroundX API key in `.env`

### Agent Takes Too Long

- Check Ollama status: `ollama list`
- Verify Qdrant responsiveness: `curl http://localhost:6333/health`
- Review timeout settings in config

---

## Next Steps

After validating basic functionality:

1. Test multi-file queries (attach multiple file UUIDs)
2. Test with audio transcripts (from Phase 2 ingestion)
3. Verify conversation summarization after 50+ turns
4. Test with different LLM providers (if configured)
5. Run the success criteria validation tests

---

**Status**: Quickstart guide complete, ready for user testing.