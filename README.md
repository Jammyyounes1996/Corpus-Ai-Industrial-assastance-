# CORPUS — Industrial AI Assistant

CORPUS is a local-first Industrial AI Assistant designed for engineers working with technical documents, industrial knowledge, OCR outputs, audio transcripts, and updated web-verified information.

The project combines a **FastAPI backend**, **React/Vite frontend**, **LangGraph agent workflow**, **Ollama local LLMs**, **Qdrant vector search**, **GroundX document indexing**, **SQLite persistence**, and **Tavily web search** for current source-backed answers.

CORPUS helps engineers ask questions, analyze documents, extract text from images, transcribe audio, search local knowledge, and double-check updated technical information with sources.

---

## Why CORPUS?

Industrial engineers usually work with scattered knowledge sources such as:

* equipment manuals
* technical PDFs
* inspection notes
* standards
* OCR images
* audio recordings
* plant documentation
* web references
* internal engineering reports

Traditional search tools are not enough because engineers need answers that are contextual, detailed, traceable, and source-aware.

CORPUS aims to provide a single AI workspace that can combine local knowledge, document retrieval, OCR, audio transcription, and web verification in one assistant.

---

## Key Features

* Local-first AI assistant using Ollama
* FastAPI backend with async support
* React/Vite frontend
* LangGraph agent routing
* Long structured answer generation
* Tavily web search with citations
* Qdrant vector database for local retrieval
* GroundX integration for PDF/document indexing
* OCR workflow for extracting text from images/documents
* Audio transcription workflow
* Streaming chat responses
* Arabic RTL and English LTR support
* Source-aware answers
* Configurable model and generation settings
* Prepared architecture for future industrial connectors

---

## Planned Industrial Connectors

Future integration targets include:

* OPC-UA connector
* Time-series model
* Maximo connector
* SAP connector
* Industrial equipment dashboards
* Plant data connectors

---

## Tech Stack

| Layer             | Technology                  |
| ----------------- | --------------------------- |
| Backend           | FastAPI                     |
| Frontend          | React + Vite + TypeScript   |
| Agent Workflow    | LangGraph                   |
| Local LLM         | Ollama                      |
| Vector Database   | Qdrant                      |
| Document Indexing | GroundX                     |
| Web Search        | Tavily                      |
| Database          | SQLite + SQLAlchemy         |
| OCR / Audio       | Project ingestion workflows |
| Testing           | Pytest + frontend tests     |

---

## Project Structure

```text
Industrial Ai assiatant/
├── backend/
│   ├── agent/
│   ├── api/
│   ├── config/
│   ├── core/
│   ├── database/
│   └── main.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── index.html
│   └── vite.config.ts
│
├── tests/
├── specs/
├── scripts/
├── docker-compose.yml
├── requirements.txt
├── environment.yml
├── .env.example
└── README.md
```

---

## Prerequisites

Install the following before running the project:

* Python 3.12+
* Node.js 18+
* npm
* Docker Desktop
* Ollama
* Git
* Miniconda or Python virtual environment

Optional external services:

* GroundX API key
* Tavily API key

---

## Clone the Repository

```bash
git clone https://github.com/Jammyyounes1996/Corpus-Ai-Industrial-assastance-.git
cd Corpus-Ai-Industrial-assastance-
```

---

## Environment Configuration

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and add your local settings.

Example:

```env
APP_NAME=Industrial AI Assistant
APP_VERSION=1.0.0
DEBUG=true

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
FRONTEND_URL=http://localhost:8501

DATABASE_URL=sqlite+aiosqlite:///./industrial_ai.db

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=industrial_assistant

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=your-local-ollama-model
OLLAMA_EMBED_MODEL=nomic-embed-text:latest

DEFAULT_NUM_CTX=50000
DEFAULT_NUM_PREDICT=2048
LONG_ANSWER_NUM_PREDICT=4096
MAX_NUM_PREDICT=8192

GROUNDX_API_KEY=your_groundx_api_key
GROUNDX_BUCKET_ID=your_groundx_bucket_id

WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=tavily
WEB_SEARCH_API_KEY=your_tavily_api_key
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_TIMEOUT_SECONDS=10

SECRET_KEY=replace_with_generated_secret_key
LOG_LEVEL=INFO
```

Important: never commit `.env` to GitHub.

---

## Start Qdrant

From the project root:

```bash
docker compose up qdrant -d
```

Check that Qdrant is running:

```bash
docker ps
```

Qdrant should be available at:

```text
http://localhost:6333
```

---

## Start Ollama

Make sure Ollama is installed and running.

```bash
ollama serve
```

Pull the embedding model:

```bash
ollama pull nomic-embed-text:latest
```

Pull your selected chat model:

```bash
ollama pull your-model-name
```

Then update `.env`:

```env
OLLAMA_MODEL=your-model-name
DEFAULT_MODEL_NAME=your-model-name
```

---

## Backend Setup

Create and activate a Python environment.

### Option 1: Conda

```bash
conda env create -f environment.yml
conda activate industrial-ai
```

### Option 2: venv

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Initialize Database and Services

If the scripts are available in your local project, run:

```bash
python scripts/init_db.py
python scripts/setup_qdrant_collection.py
python scripts/verify_environment.py
```

If these scripts were moved or archived, check the `scripts/` folder.

---

## Start Backend

From the project root:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

Or, if `run.py` is configured:

```bash
python run.py
```

Health check:

```text
http://127.0.0.1:8001/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "qdrant": "connected",
  "ollama": "connected"
}
```

---

## Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 8501
```

Open the app:

```text
http://127.0.0.1:8501/
```

If the root route does not open, try:

```text
http://127.0.0.1:8501/index.html
```

---



## Development Status

CORPUS is under active development. The current focus is improving frontend source display, validating retrieval behavior, strengthening web search workflows, and preparing future industrial connectors.

---

## License

MIT License

---

## Author

Developed by Mohamed Ali as part of an Industrial AI Assistant project for engineering and industrial knowledge workflows.
