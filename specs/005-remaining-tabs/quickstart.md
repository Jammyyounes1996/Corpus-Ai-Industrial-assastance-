# Quickstart: Remaining Workspace Tabs

**Date**: 2026-06-06 | **Feature**: [spec.md](spec.md)

## Prerequisites

- Backend running at `localhost:8001` (`uvicorn backend.main:app`)
- Frontend dev server at `localhost:5173` (`npm run dev` in `frontend/`)
- Ollama running at `localhost:11434` with the configured model
- Qdrant running at `localhost:6333`
- At least one file ingested (PDF, image, or audio) for Documents/OCR tabs
- At least one completed chat conversation for Analysis/Tools tabs

## New Dependency

```bash
pip install ragas
```

Pin the installed version in `requirements.txt` after install.

## Implementation Order

1. **Backend first** — all 3 backend changes (Tasks 1.1-1.3) before any frontend work
2. **Documents tab** — simplest tab, validates file API integration
3. **OCR tab** — depends on file content endpoint from Task 1.2
4. **Analysis tab** — depends on retrieved_context fix from Task 1.1
5. **Tools tab** — depends on evaluation endpoint from Task 1.3
6. **Integration** — wire routing, verify cross-tab consistency

## Verification Sequence

After each backend task, verify with curl before proceeding:

```bash
# Task 1.1: Verify retrieved_context in messages
curl localhost:8001/api/chat/{chat_id} | python -m json.tool | grep retrieved_context

# Task 1.2: Verify file content serving
curl -I localhost:8001/api/files/{file_id}/content

# Task 1.3: Verify evaluation endpoint
curl -X POST localhost:8001/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "...", "message_id": 42}'
```

## Key Files to Touch

| File | Change Type | Phase |
|------|-------------|-------|
| `backend/api/routes/chat.py` | Modify (1 line) | 1 |
| `backend/api/routes/files.py` | Modify (add endpoint) | 1 |
| `backend/api/routes/evaluate.py` | New | 1 |
| `backend/schemas/evaluate.py` | New | 1 |
| `backend/core/evaluation/ragas_evaluator.py` | New | 1 |
| `backend/database/crud.py` | Modify (add eval CRUD) | 1 |
| `backend/main.py` | Modify (register evaluate router) | 1 |
| `requirements.txt` | Modify (add ragas) | 1 |
| `frontend/src/components/tabs/DocumentsTab.tsx` | New | 2 |
| `frontend/src/components/tabs/OCRTab.tsx` | New | 3 |
| `frontend/src/components/tabs/AnalysisTab.tsx` | New | 4 |
| `frontend/src/components/tabs/ToolsTab.tsx` | New | 5 |
| `frontend/src/components/layout/WorkspaceContent.tsx` | Modify | 6 |
| `frontend/src/components/tabs/WorkspaceData.ts` | Modify (isPlaceholder→false) | 6 |
