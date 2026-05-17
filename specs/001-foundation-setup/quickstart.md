# Quickstart: Foundation & Setup

**Feature**: 001-foundation-setup
**Date**: 2026-05-18
**Estimated Time**: 15-20 minutes

---

## Prerequisites

Before starting Phase 1, ensure you have:

- [ ] Python 3.11+ installed
- [ ] Docker Desktop for Windows installed and running
- [ ] 8GB+ VRAM (for Gemma2 model) or 16GB+ system RAM (CPU inference)
- [ ] ~10GB free disk space

---

## Step 1: Clone and Navigate

```bash
git clone <repository-url> industrial-ai-assistant
cd industrial-ai-assistant
```

---

## Step 2: Create Conda Environment

```bash
conda env create -f environment.yml
conda activate industrial-ai
```

Expected output:
```
Solving environment: done
Installing packages: done
```

---

## Step 3: Start Qdrant

```bash
docker-compose up -d
```

Verify Qdrant is running:
```bash
curl http://localhost:6333/health
```

Expected output: `{"status":"ok"}`

---

## Step 4: Pull Ollama Models

```bash
ollama pull gemma2:latest
ollama pull nomic-embed-text
```

Verify models are available:
```bash
ollama list
```

Expected output shows both models listed.

---

## Step 5: Configure Environment

```bash
cp .env.example .env
# Edit .env with your preferred editor
```

**IMPORTANT**: Before first run, generate the SECRET_KEY:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Or run the helper script:
```bash
python scripts/generate_secret_key.py
```

Copy the output and set it as `SECRET_KEY` in your `.env` file.

**Note**: For Phase 1 defaults work (SECRET_KEY can be placeholder for testing).

---

## Step 6: Initialize Database

```bash
python scripts/init_db.py
python scripts/setup_qdrant_collection.py
```

Expected output:
```
Database created: industrial_ai.db
Qdrant collection created: industrial_assistant
```

---

## Step 7: Verify Environment

```bash
python scripts/verify_environment.py
```

All checks should pass with ✓ marks.

---

## Step 8: Start Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Backend should start with:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test health endpoint in new terminal:**
```bash
curl http://localhost:8000/health
```

Expected output: `{"status": "ok"}`

---

## Step 9: Start Frontend

```bash
streamlit run frontend/app.py
```

Frontend should open at http://localhost:8501 with:
- Sidebar visible (left)
- Tabs visible (top: Chat, Documents, OCR, Analysis, Tools)
- Status indicator in top-right (green, showing connection status)

---

## Step 10: Stop Services

When done, stop services:

```bash
# Stop Qdrant
docker-compose down

# Deactivate environment (optional)
conda deactivate
```

---

## Troubleshooting

### Qdrant fails to start

**Error**: `Error starting userland proxy: listen tcp 0.0.0.0:6333: bind: address already in use`

**Fix**: Something is using port 6333. Find and kill:
```bash
netstat -ano | findstr :6333
taskkill /PID <PID> /F
```

---

### Ollama connection refused

**Error**: `ollama connection error` or `Connection refused`

**Fix**: Ensure Ollama is running:
```bash
# Windows
# Check Ollama is in system tray or run:
ollama serve
```

---

### Audio transcription is slow

**Symptom**: Audio files take very long to transcribe (several minutes for 1-minute audio).

**Fix**: Check backend logs for GPU detection:

```
INFO:CUDA detected — using GPU for Whisper transcription
```

If you see "GPU not available — falling back to CPU", verify:
1. NVIDIA GPU is present
2. CUDA toolkit is installed
3. PyTorch is installed with CUDA support

For systems without GPU, use shorter audio files or accept slower CPU transcription (approximately 10x slower).

---

### SQLite database locked

**Error**: `sqlite3.OperationalError: database is locked`

**Fix**: Close any other apps accessing the DB (database viewers, etc.)

---

### Frontend can't connect to backend

**Error**: "Connection refused" in browser console

**Fix**: Ensure backend is running on port 8000. Check CORS configuration in `backend/main.py`.

---

## Validation Checklist

After completing Phase 1, verify:

- [ ] Conda environment `industrial-ai` exists
- [ ] Qdrant responds to `/health` endpoint
- [ ] `industrial_ai.db` file exists with 8 tables
- [ ] Qdrant collection `industrial_assistant` exists
- [ ] Backend health check returns `{"status": "ok"}`
- [ ] Frontend loads at http://localhost:8501
- [ ] `verify_environment.py` passes all checks
- [ ] No errors in backend logs
- [ ] No errors in frontend browser console

---

## Next Steps

Phase 1 complete! Proceed to:
- **Phase 2**: Ingestion Pipeline (PDF, audio, image upload)

---

**End of Quickstart**