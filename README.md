# Industrial AI Assistant

An AI-powered assistant for industrial environments with RAG capabilities, document processing, OCR, and audio transcription.

## Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop (for Qdrant)
- Ollama (for local LLM)
- Miniconda (recommended)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd industrial-ai-assistant
   ```

2. **Create conda environment:**
   ```bash
   conda env create -f environment.yml
   conda activate industrial-ai
   ```

3. **Start Qdrant:**
   ```bash
   docker-compose up -d
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   python scripts/generate_secret_key.py
   # Copy the key into .env as SECRET_KEY
   ```

5. **Initialize database and vector store:**
   ```bash
   python scripts/init_db.py
   python scripts/setup_qdrant_collection.py
   ```

6. **Verify environment:**
   ```bash
   python scripts/verify_environment.py
   ```

7. **Start backend:**
   ```bash
   python run.py
   # Or with uvicorn directly:
   # uvicorn backend.main:app --reload --port 8001
   ```

8. **Start frontend (in a new terminal):**
   ```bash
   streamlit run frontend/app.py
   ```

## Architecture

- **Backend**: FastAPI (Python 3.12) - REST API with async support
- **Frontend**: Streamlit - Interactive web UI
- **Database**: SQLite via SQLAlchemy 2.0 async
- **Vector Store**: Qdrant (Docker) for RAG
- **LLM**: Ollama (Gemma 4) for local inference

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | FastAPI | 0.115 |
| Frontend | Streamlit | 1.41.1 |
| Agent | LangGraph | 0.2 |
| ORM | SQLAlchemy | 2.0 |
| Validation | Pydantic | 2.10.4 |
| Vector DB | Qdrant | 1.12 |
| LLM | Ollama (Gemma 4) | Latest |

## License

MIT
