# Contract: Status

## Endpoint path

`/health`

## HTTP method

`GET`

## Success response schema

```json
{
  "status": "ok | degraded",
  "version": "string",
  "database": "connected | disconnected",
  "qdrant": "connected | disconnected | collection_missing",
  "ollama": "connected | disconnected"
}
```

The endpoint always attempts to return HTTP `200` with `status` set to `ok` or `degraded`. Unhandled exceptions may still be returned by the global exception handler.

## Disconnected/unavailable behavior

- Network failure: frontend shows backend `Unavailable` or `Disconnected`.
- Non-2xx response: frontend shows backend `Unavailable` and exposes a concise error state.
- `status: degraded`: frontend shows backend reachable but degraded.
- Individual dependency fields with disconnected values should render as disconnected/unavailable without fake recovery states.

## Fields available for backend

Available from `/health`:

- `status`
- `version`

Frontend mapping:

- `status: ok` means backend reachable and dependencies checked as connected.
- `status: degraded` means backend reachable but at least one dependency is unavailable.

## Fields available for model

Available from `/health`:

- `ollama`: connection status only.

Available from optional `GET /api/models`:

- `models`: list of local Ollama models.
- `total`: model count.
- Per model: `name`, `size_bytes`, `modified_at`, `family`, `parameter_size`.

Missing:

- Active chat model is not reported by `/health`.
- Default model is not reported by `/health`.

Frontend fallback:

- Show model as `Unknown` unless a selected chat or `/api/models` interaction provides a real model name.

## Fields available for provider

Missing from `/health`.

Frontend fallback:

- Show provider as `Unknown` unless a selected chat response provides `model_provider`.

## Fields available for RAG

Partially available:

- `qdrant` indicates vector database availability.

Missing:

- No explicit `rag_enabled` field.
- No retrieval pipeline readiness field.
- No reranker readiness field.

Frontend fallback:

- Show RAG as `Unknown` or derive only a limited `Vector DB connected/disconnected` label from `qdrant`.

## Fields available for Qdrant

Available from `/health`:

- `qdrant`: `connected`, `disconnected`, or `collection_missing`.

Frontend mapping:

- `connected`: Qdrant collection is reachable and expected collection exists.
- `collection_missing`: Qdrant is reachable but expected collection is missing.
- `disconnected`: Qdrant health check failed or did not confirm availability.

## Fields available for OCR

Missing from `/health`.

Frontend fallback:

- Show OCR as `Unknown` or `Unavailable`.
- Do not infer OCR readiness from image upload support.

## Fields available for GPU

Missing from `/health`.

Frontend fallback:

- Show GPU as `Unknown` or hide the field if the design allows optional status fields.

## Fields missing from backend

- Active model name.
- Default model name.
- Provider status.
- RAG enabled flag.
- Retrieval/reranker readiness.
- OCR readiness.
- GPU availability.
- Frontend-safe CORS discovery.

## Frontend fallback behavior for missing fields

- Use `Unknown` for fields that may exist but are not reported.
- Use `Unavailable` for fields whose backing request failed.
- Never display fake `Connected`, `Ready`, `Enabled`, or model names for missing backend fields.
- Prefer hiding optional fields over fabricating values.
