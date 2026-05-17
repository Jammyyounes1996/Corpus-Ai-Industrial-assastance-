# Industrial AI Assistant — Implementation Plan

> **Document Type:** Specification & Implementation Plan
> **Methodology:** Spec-Driven Development (SDD) using spec-kit
> **Target Executor:** Claude Code
> **Project Duration:** 7 days
> **Last Updated:** 2026-05-17

---

## Table of Contents

1. [Vision & Goals](#1-vision--goals)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Frontend Specifications](#4-frontend-specifications)
5. [Backend Specifications](#5-backend-specifications)
6. [Database Schema](#6-database-schema)
7. [API Contract](#7-api-contract)
8. [Project Folder Structure](#8-project-folder-structure)
9. [Environment & Dependencies](#9-environment--dependencies)
10. [Implementation Phases](#10-implementation-phases)
11. [Testing Strategy](#11-testing-strategy)
12. [Final User Experience](#12-final-user-experience)
13. [Deliverables](#13-deliverables)

---

## 1. Vision & Goals

### 1.1 Vision

Build an **Industrial AI Assistant** — a premium, Claude-inspired local AI workspace that helps industrial engineers query equipment manuals, audio recordings, and images through a unified agentic RAG pipeline.

### 1.2 Primary Goals

| # | Goal | Success Criteria |
|---|------|------------------|
| 1 | Multimodal ingestion (PDF, audio, images) | All 3 file types processed end-to-end |
| 2 | Agentic retrieval with LangGraph | Real thinking steps streamed to UI |
| 3 | Local-first, free-tier-only stack | No paid services required |
| 4 | Premium Claude-inspired UX | Matches provided design pixel-by-pixel |
| 5 | Retrieval quality evaluation | RAGAS scores visible in UI |
| 6 | Modular, maintainable codebase | Passes CONSTITUTION.md review |

### 1.3 Non-Goals (Out of Scope)

- Real-time voice streaming (we use file upload only)
- Multi-user authentication
- Production deployment / horizontal scaling
- Mobile responsive layout (desktop-only)
- ColBERT retrieval (replaced with hybrid BM25 + dense)

### 1.4 Target User

Industrial engineer with one or more of:
- Equipment manuals (PDFs with tables, diagrams)
- Audio recordings from technicians
- Photos of nameplates, gauges, schematics

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                       │
│             (Port 8501 — Custom CSS Theme)                  │
│                                                             │
│  Sidebar  │  Chat │ Documents │ OCR │ Analysis │ Tools     │
└────────────────────────┬───────────────────────────────────┘
                         │  HTTP REST + SSE Streaming
                         ▼
┌────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                         │
│                       (Port 8000)                           │
│                                                             │
│   /api/chat    /api/ingest    /api/ocr    /api/evaluate    │
│   /api/projects   /api/settings   /api/files               │
└──────┬─────────────────┬──────────────────┬────────────────┘
       │                 │                  │
       ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  LangGraph   │  │  Ingestion   │  │   Evaluation     │
│    Agent     │  │   Pipeline   │  │     (RAGAS)      │
└──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
       │                 │                    │
       └────────┬────────┴────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                       │
│                                                             │
│   Qdrant   │   SQLite   │   Disk    │  Ollama (Gemma4 +    │
│  (Docker)  │  (Local)   │  Storage  │   nomic-embed)       │
│            │            │           │                       │
│                              GroundX API (Free Tier)        │
│                              faster-whisper (Local)         │
│                              Optional: Gemini / Grok APIs   │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Communication Flow

**Request types:**

1. **Synchronous REST** — file uploads, CRUD operations, settings
2. **Server-Sent Events (SSE)** — chat responses with thinking steps streaming
3. **Static file serving** — uploaded images for OCR gallery

**Why FastAPI + Streamlit (separate)?**
- LangGraph nodes execute asynchronously; SSE streams each node's status to UI
- Clean separation of concerns (UI vs business logic)
- Backend reusable for future clients (mobile, CLI)
- Streamlit alone cannot stream intermediate agent steps cleanly

### 2.3 Data Flow Example (User asks a question)

```
1. User types question in Chat tab
2. Streamlit POST → /api/chat/stream with {chat_id, message, attached_files}
3. FastAPI opens SSE connection
4. LangGraph router node runs → emits "Analyzing query..."
5. LangGraph routes to GroundX retrieve → emits "Reading PDF documents..."
6. LangGraph routes to Qdrant retrieve → emits "Searching memory (RAG)..."
7. LangGraph answer node runs Gemma4 → streams tokens
8. Streamlit renders thinking steps + streamed response
9. On completion, FastAPI persists message + thinking_steps to SQLite
```

---

## 3. Technology Stack

### 3.1 Frontend Stack

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| UI Framework | Streamlit | 1.40+ | Application framework |
| HTTP Client | httpx | 0.27+ | Async API calls |
| SSE Client | httpx-sse | 0.4+ | Streaming responses |
| Markdown | streamlit native | — | Colored response rendering |
| Icons | Lucide icons (SVG) | — | UI iconography |

### 3.2 Backend Stack

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| API Framework | FastAPI | 0.115+ | REST + SSE server |
| ASGI Server | Uvicorn | 0.32+ | Production-grade ASGI |
| Agent | LangGraph | 0.2+ | Stateful agent orchestration |
| LangChain Core | langchain-core | 0.3+ | Message types, tools |
| Ollama Client | langchain-ollama | 0.2+ | Gemma4 + nomic-embed |
| PDF Parser | groundx-python-sdk | latest | Complex PDF parsing |
| Audio STT | faster-whisper | 1.0+ | Local audio transcription |
| Vector DB | qdrant-client | 1.12+ | Hybrid search |
| Evaluation | ragas | 0.2+ | RAG metrics |
| Database | SQLAlchemy | 2.0+ | ORM |
| Database Driver | aiosqlite | 0.20+ | Async SQLite |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Config | pydantic-settings | 2.6+ | Env-based config |
| Validation | pydantic | 2.9+ | Request/response models |

### 3.3 Infrastructure

| Component | Tool | Purpose |
|-----------|------|---------|
| Container Orchestration | docker-compose | Qdrant deployment |
| Vector DB | Qdrant 1.12 (Docker) | Hybrid search backend |
| Local LLM Server | Ollama | Gemma4 + nomic-embed serving |
| Environment Manager | Miniconda | Python environment isolation |
| External API | GroundX (eyelevel) | PDF parsing (free tier) |
| Optional External | Gemini API / Grok API | LLM alternatives |

### 3.4 Models

| Model | Provider | Purpose | Size |
|-------|----------|---------|------|
| Gemma4 | Ollama (local) | LLM, Vision, OCR | ~4-8 GB VRAM |
| nomic-embed-text | Ollama (local) | Text embeddings (768d) | ~270 MB |
| faster-whisper (base) | Local download | Audio transcription | ~150 MB |
| Gemini 2.5 Flash | API (optional) | LLM alternative | Cloud |
| Grok (latest) | API (optional) | LLM alternative | Cloud |

---

## 4. Frontend Specifications

### 4.1 Design System

#### 4.1.1 Color Palette

```css
/* Primary palette — Claude-inspired warm minimalism */
--bg-main:         #FAF7F2;    /* Main workspace background */
--bg-sidebar:      #F5F1EB;    /* Sidebar background */
--bg-card:         #FFFFFF;    /* Message/card surfaces */
--bg-hover:        #F0EBE3;    /* Hover state */
--bg-active:       #FFF1E8;    /* Active item background */

/* Accent — terracotta/warm amber */
--accent-primary:  #D4623F;    /* Primary brand orange */
--accent-soft:     #FCE4D6;    /* New Chat button background */
--accent-glow:     #E07856;    /* Hover/active accent */

/* Text */
--text-primary:    #2D2D2D;    /* Headings, body */
--text-secondary:  #6B6B6B;    /* Subtitles, metadata */
--text-tertiary:   #9B9B9B;    /* Timestamps, hints */
--text-link:       #4A6FA5;    /* Response headings (blue) */

/* Borders */
--border-light:    #E8E3DA;    /* Standard borders */
--border-medium:   #DCD5C8;    /* Stronger separators */

/* Status */
--status-success:  #5BAE5B;    /* Connected, completed */
--status-warning:  #E0A040;    /* In-progress */
--status-error:    #D85555;    /* Error, disconnected */

/* Code blocks */
--code-bg:         #2D2D2D;
--code-text:       #F0EBE3;
```

#### 4.1.2 Typography

```css
--font-family: 'Inter', -apple-system, BlinkMacSystemFont,
               'SF Pro Display', 'Segoe UI', sans-serif;

--font-size-xs:   12px;   /* Timestamps, metadata */
--font-size-sm:   13px;   /* Section headers (uppercase) */
--font-size-base: 15px;   /* Body text */
--font-size-md:   16px;   /* Response paragraphs */
--font-size-lg:   18px;   /* Response headings */
--font-size-xl:   20px;   /* App title */

--font-weight-regular:  400;
--font-weight-medium:   500;
--font-weight-semibold: 600;

--line-height-tight:  1.4;
--line-height-base:   1.6;
--line-height-loose:  1.75;  /* Long-form content */
```

#### 4.1.3 Spacing & Layout

```css
--space-xs:  4px;
--space-sm:  8px;
--space-md:  12px;
--space-lg:  16px;
--space-xl:  24px;
--space-2xl: 32px;
--space-3xl: 48px;

--radius-sm:  6px;
--radius-md:  10px;
--radius-lg:  14px;
--radius-xl:  20px;
--radius-full: 9999px;

--sidebar-width:    280px;
--content-max-width: 900px;
--input-bar-height:  120px;

--shadow-sm: 0 1px 2px rgba(45, 45, 45, 0.04);
--shadow-md: 0 4px 12px rgba(45, 45, 45, 0.06);
--shadow-lg: 0 8px 24px rgba(45, 45, 45, 0.08);
```

### 4.2 Layout Structure

```
┌──────────────┬────────────────────────────────────────────┐
│              │ ┌─Tabs──────────────────┐ ┌─Status──────┐ │
│              │ │ Chat Documents OCR... │ │ 🟢 Gemma4   │ │
│              │ └───────────────────────┘ └─────────────┘ │
│              │                                            │
│   SIDEBAR    │            MAIN WORKSPACE                  │
│   (280px)    │            (flexible, max 900px content)   │
│              │                                            │
│              │                                            │
│              │ ┌──────────────────────────────────────┐  │
│              │ │ Input Bar (sticky bottom)            │  │
│              │ └──────────────────────────────────────┘  │
└──────────────┴────────────────────────────────────────────┘
```

### 4.3 Sidebar Specification

#### 4.3.1 Logo Header
- **Position:** Top of sidebar, ~48px height
- **Content:**
  - Animated starburst icon (16px) on left
  - Text: "Industrial AI Assistant" (semibold, 15px)
- **Padding:** 16px horizontal, 14px vertical

#### 4.3.2 New Chat Button
- **Background:** `--accent-soft` (#FCE4D6)
- **Text color:** `--text-primary`
- **Icon:** "+" plus icon (16px)
- **Text:** "New Chat" (medium weight)
- **Height:** 42px
- **Border radius:** `--radius-md`
- **Margin:** 12px horizontal, 8px vertical
- **Hover:** subtle scale 1.02, slightly darker bg
- **Click action:** Creates new chat session, navigates to Chat tab

#### 4.3.3 Search Chats Input
- **Icon:** Search icon (14px) on left, gray
- **Placeholder:** "Search chats..."
- **Background:** transparent
- **Border:** 1px solid `--border-light`
- **Behavior:** Live filter chat list on type (debounced 200ms)

#### 4.3.4 Chats Section
- **Header:** "Chats" (uppercase, 13px, semibold, gray)
- **List items:**
  - Title (truncated to 1 line, 14px)
  - Right-aligned timestamp ("2m ago", "Yesterday", "3d ago")
  - Active state: `--bg-active` background, orange left border (2px)
  - Hover: `--bg-hover` background
  - Click: loads chat in Chat tab
  - Right-click / hover icon: context menu with "Move to project", "Rename", "Delete"
- **Empty state:** "No conversations yet"

#### 4.3.5 Projects Section
- **Header:** "Projects" with "+" button on right
- **Items:**
  - Folder icon (14px) + project name
  - Click to expand: shows chats within
  - Drag-and-drop chat → project (alternative: context menu)
- **"+" button:** Opens modal to create new project (name input only)

#### 4.3.6 Knowledge Bases Section
- **Header:** "Knowledge Bases" with "+" button
- **Items:**
  - Document icon + filename
  - Hover: shows file size and date
  - Click: opens preview in Documents tab
- **"+" button:** Opens file upload dialog (PDF only here)

#### 4.3.7 Tools Section
- **Static list** (not expandable):
  - "RAGAS Evaluator" → opens Tools tab with RAGAS view
  - "Audio Transcriber" → opens Tools tab with transcriber view

#### 4.3.8 Settings Footer
- **Position:** Sticky to bottom of sidebar
- **Icon:** Gear icon + "Settings" text
- **Click:** Opens Settings modal (see 4.10)

### 4.4 Top Bar

#### 4.4.1 Tab Navigation
- **Tabs:** Chat | Documents | OCR | Analysis | Tools
- **Active tab:**
  - 2px orange underline (`--accent-primary`)
  - Text color: `--text-primary`
  - Icon color: `--accent-primary`
- **Inactive tab:**
  - No underline
  - Text color: `--text-secondary`
- **Hover:** subtle background, smooth 200ms transition
- **Icons:** Each tab has Lucide icon (Chat, FileText, Image, BarChart3, Wrench)

#### 4.4.2 Status Indicator (Top-Right)
- **Container:** rounded card, 220px wide, with subtle shadow
- **Content:**
  - Green dot (8px circle) for connected, red for disconnected
  - "Connected to local model" (13px, semibold)
  - "{ModelName} • {Provider} • RAG Enabled" (12px, gray)
- **Click:** Opens model details popover
- **Dropdown arrow:** expands to show GPU status, Qdrant status, OCR ready

### 4.5 Chat Tab Specification

#### 4.5.1 Message Container
- **Max-width:** 900px
- **Centered horizontally**
- **Vertical scroll** for history

#### 4.5.2 User Message
- **Layout:** avatar (left, 32px) + content
- **Background:** `--bg-card` with subtle border
- **Padding:** 14px 18px
- **Border radius:** `--radius-md`
- **Timestamp:** Right-aligned, 12px, `--text-tertiary`
- **Avatar:** Generic user icon in light gray circle

#### 4.5.3 Thinking Card (CRITICAL FEATURE)
- **Position:** Above AI response
- **Header:**
  - Animated starburst icon (left, 18px)
  - Text "Thinking" (semibold, 15px)
  - Expand/collapse chevron (right)
- **Body (when expanded):**
  - Vertical list of steps
  - Each step has:
    - Status indicator (left, 16px):
      - `⟳` Animated spinner (in-progress) — `--status-warning`
      - `✓` Green checkmark (completed) — `--status-success`
      - `○` Empty circle (pending) — `--text-tertiary`
    - Step description text (14px)
  - Smooth fade-in for new steps (300ms)
  - Smooth status transitions
- **Behavior:**
  - Auto-expands during streaming
  - Auto-collapses 2 seconds after final step completes
  - User can toggle manually

**Step descriptions (exact strings, mapped from LangGraph nodes):**
```
"Analyzing your query..."          → router_node
"Reading PDF documents..."         → groundx_retrieve_node
"Searching memory (RAG)..."        → qdrant_retrieve_node
"Running OCR on images..."         → ocr_node (only if image attached)
"Analyzing information..."          → context_synthesis_node
"Generating answer..."              → answer_node
```

#### 4.5.4 AI Response Card
- **No traditional chat bubble** — clean card design
- **Background:** `--bg-card`
- **Border:** 1px solid `--border-light`
- **Border radius:** `--radius-lg`
- **Padding:** 20px 24px
- **Margin-top:** 12px (after thinking card)

**Content rendering:**
- Animated starburst icon (top-left, 20px)
- Markdown rendered with custom styles:
  - **H1/H2/H3 headings:** color `--text-link` (#4A6FA5), font-weight 600
  - **Bold text (`**text**`):** `--accent-primary` color
  - **Inline code:** monospace, light cream background, 13px
  - **Code blocks:** `--code-bg` background, `--code-text` color, with copy button
  - **Tables:** Clean borders, alternating row backgrounds, sticky header
  - **Bullet lists:** custom orange bullet markers
  - **Links:** `--text-link`, underline on hover

**Hover state:**
- Action buttons appear on top-right of card (fade-in 200ms):
  - Copy (clipboard icon)
  - Regenerate (refresh icon)
  - Expand (full-screen icon) — opens modal with response
  - Export (download icon) — exports as MD or PDF
  - Speak (volume icon) — TTS playback (optional/skip for MVP)
  - Like (thumbs-up)
  - Dislike (thumbs-down)
- Buttons: 32x32px, icon-only, ghost style, subtle hover glow

#### 4.5.5 Sources Display
- **Position:** Below response content
- **Label:** "Sources:" (13px, gray, semibold)
- **Chips:**
  - Background: `--bg-hover`
  - Border: 1px solid `--border-light`
  - Border radius: `--radius-sm`
  - Padding: 4px 10px
  - Text: filename + small icon (PDF/audio/image)
  - "+N more" chip if > 3 sources
  - Hover: preview tooltip with chunk text excerpt

#### 4.5.6 Input Bar (Sticky Bottom)
- **Position:** Sticky to bottom of main area
- **Background:** `--bg-main` with subtle top shadow
- **Container:**
  - Border: 1px solid `--border-medium`
  - Border radius: `--radius-xl`
  - Padding: 14px 18px
  - Min-height: 56px
  - Max-height: 200px (expandable)

**Inner controls (left to right):**
- **Attach button:** `+ Attach` (opens file picker — PDF, image, audio)
- **Audio File button:** Microphone icon + "Audio File" text (opens audio file picker specifically)
- **Tools dropdown:** Tools icon + "Tools" (shows agent tools available)
- **Model selector:** "Model {current_model}" with dropdown (Gemma4 / Gemini / Grok)
- **Spacer (flex-grow)**
- **Textarea:** placeholder "Ask anything about your industrial systems..."
- **Send button:**
  - Orange circular (40x40), `--accent-primary` background
  - Disabled (gray) when textarea empty
  - Active glow effect when text typed
  - Sends on click OR Enter (Shift+Enter for newline)

**Attached files preview:**
- Show above input bar as horizontal scrollable list of chips
- Each chip: filename + X to remove
- For images: small thumbnail (40x40)

### 4.6 Documents Tab Specification

**Purpose:** View, upload, and delete files in knowledge base.

**Layout:**
- **Top bar:** "Knowledge Base" title + "+ Upload Document" button
- **Grid view:** 3-column grid of document cards
- **Each card:**
  - File icon (large, top)
  - Filename (14px, semibold)
  - File size + upload date (12px, gray)
  - Status badge: "Indexed" (green) or "Processing" (orange)
  - Hover: shows delete icon (top-right)
- **Empty state:** Illustration + "No documents yet. Upload your first PDF, audio, or image."

**Filter/sort controls:**
- Filter by type (All / PDF / Audio / Image)
- Sort by (Date ↓ / Name A-Z / Size)

### 4.7 OCR Tab Specification

**Purpose:** Gallery of all images previously OCR'd, with click-to-chat.

**Layout:**
- **Top bar:** "OCR History" title
- **Grid:** 4-column grid of image thumbnails
- **Each thumbnail:**
  - Image preview (200x200, object-fit: cover)
  - Filename overlay (bottom)
  - Hover: shows "Open in Chat" overlay + extracted text preview tooltip
- **Click action:**
  - Creates a new chat session
  - Pre-loads the image as attached
  - Pre-fills first message: "Tell me about this image"
  - Navigates to Chat tab

### 4.8 Analysis Tab Specification

**Purpose:** Inspect the LangGraph execution trace of the last conversation turn.

**Layout (3 vertical sections):**

#### Section 1: Execution Trace (Top)
- **Title:** "LangGraph Execution Trace"
- **Content:** Vertical timeline of nodes
- **Each node card:**
  - Node name (e.g., "router_node")
  - Status badge (completed / failed / skipped)
  - Execution time (ms)
  - Input summary (collapsed by default)
  - Output summary (collapsed by default)
  - Click to expand for full details

#### Section 2: Retrieved Context (Middle)
- **Title:** "Retrieved Context"
- **Content:** List of chunks used in the answer
- **Each chunk card:**
  - Source filename + chunk index
  - Similarity score (0-1)
  - Chunk text (collapsed to 2 lines, expandable)
  - "Open in source" link

#### Section 3: Model Thinking (Bottom)
- **Title:** "Gemma4 Reasoning Output"
- **Content:**
  - Raw thinking/reasoning output from Gemma4 (when thinking mode is supported)
  - Rendered as monospace block with syntax highlighting
  - Token count + generation time

### 4.9 Tools Tab Specification

**Two sub-views (toggleable at top):**

#### 4.9.1 RAGAS Evaluator View
- **Top bar:** Title + "Run Evaluation on Last Chat" button
- **Metrics dashboard:**
  - 4 metric cards in 2x2 grid:
    - **Faithfulness** (0-1) — answer grounded in context
    - **Answer Relevancy** (0-1) — answer addresses question
    - **Context Precision** (0-1) — relevant chunks retrieved
    - **Context Recall** (0-1) — all relevant info retrieved
  - Each card shows: score, gauge visualization, brief explanation
- **History table:** Past evaluations with timestamps, chat reference, scores
- **Loading state:** Show LangGraph-style thinking steps when running RAGAS

#### 4.9.2 Audio Transcriber View
- **Top bar:** Title
- **List view:** All uploaded audio files
- **Each item (expandable):**
  - Audio filename + duration
  - Date uploaded
  - Play/pause inline audio player
  - Transcript text (full, scrollable)
  - "Copy transcript" button

### 4.10 Settings Modal Specification

**Triggered by:** Click on "Settings" in sidebar footer

**Modal sections:**

#### 4.10.1 Appearance
- **Theme toggle:** Light / Dark (light is default)
- Note: Dark mode applies inverted color palette while preserving accent colors

#### 4.10.2 Model Provider
- **Radio buttons:**
  - 🟢 Ollama (Local) — default, requires Gemma4 pulled
  - 🌐 Gemini API — requires API key input
  - 🌐 Grok API — requires API key input
- **Model dropdown** (depends on provider):
  - Ollama: list of installed models (queried from `/api/tags`)
  - Gemini: gemini-2.5-flash, gemini-2.5-pro
  - Grok: grok-4
- **API Key field** (hidden if Ollama selected):
  - Password input
  - Test Connection button
  - Encrypted at rest in SQLite

#### 4.10.3 Connection Status
- Shows current model + connection status
- Updates the top-right status bar live

### 4.11 Animations & Interactions

#### 4.11.1 Animated Starburst Icon
- **Visual:** Radial orange burst with 8 rays
- **Animations:**
  - Slow rotation (8s linear infinite)
  - Subtle breathing (scale 1.0 → 1.05 → 1.0, 3s ease infinite)
  - Used: logo, AI message icon, thinking icon
- **Implementation:** Inline SVG with CSS keyframes

#### 4.11.2 Streaming Cursor
- **Visual:** 2px wide vertical bar, `--accent-primary` color
- **Animation:** blink 0.7s ease-in-out infinite
- **Position:** end of streaming text

#### 4.11.3 Thinking Step Transitions
- **Spinner → checkmark:**
  - Spinner fades out (200ms)
  - Checkmark scales 0 → 1.2 → 1 with rotation (400ms ease-out)
- **New step appearing:** opacity 0 → 1 + translateY 8px → 0 (300ms)

#### 4.11.4 Tab Switch
- **Smooth fade** between tab contents (200ms)
- **Underline slide** between active tabs (250ms ease-out)

#### 4.11.5 Hover Effects
- **Buttons:** scale 1.02 + slightly darker shadow (150ms)
- **Cards:** subtle shadow lift (200ms)
- **Sidebar items:** background fade-in (150ms)

#### 4.11.6 Reduced Motion Accessibility
All animations must respect the user's OS-level motion preferences.

**CSS implementation** (in `frontend/styles/main.css`):
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Applies to:**
- Starburst icon rotation/breathing
- Thinking step fade-in transitions
- Tab underline slide
- Streaming cursor blink
- Hover scale effects
- Modal open/close transitions

**Note:** No Settings toggle needed — the OS preference is the source of truth.

---

## 5. Backend Specifications

### 5.1 FastAPI Application Structure

**Main file:** `backend/main.py`
- Initialize FastAPI with CORS for Streamlit (localhost:8501)
- Mount routers
- Startup event: initialize Qdrant client, Ollama health check
- Shutdown event: close DB connections
- Exception handlers for graceful errors

**Routers** (in `backend/api/routes/`):

| Router File | Endpoints |
|-------------|-----------|
| `chat.py` | POST /chat, GET /chat/stream, GET /chat/{id}, DELETE /chat/{id}, GET /chats |
| `ingest.py` | POST /ingest/pdf, POST /ingest/audio, POST /ingest/image |
| `ocr.py` | GET /ocr/history, GET /ocr/{file_id} |
| `evaluation.py` | POST /evaluate, GET /evaluations |
| `projects.py` | POST /projects, GET /projects, PUT /projects/{id}, DELETE /projects/{id}, POST /projects/{id}/chats |
| `files.py` | GET /files, DELETE /files/{id}, GET /files/{id}/download |
| `settings.py` | GET /settings, PUT /settings, POST /settings/test-connection |

### 5.2 LangGraph Agent Design

**State definition** (`backend/core/agent/state.py`):

```python
class AgentState(TypedDict):
    # User input
    chat_id: str
    user_message: str
    attached_image_path: Optional[str]
    attached_files: List[str]

    # Conversation memory
    messages: List[BaseMessage]

    # Intermediate results
    query_intent: Optional[str]      # "pdf_only" | "audio" | "image" | "general"
    groundx_results: List[Dict]
    qdrant_results: List[Dict]
    ocr_result: Optional[str]

    # Output
    thinking_steps: List[ThinkingStep]
    final_answer: str
    sources: List[Source]
```

**Nodes** (`backend/core/agent/nodes.py`):

```
router_node          → analyzes query, sets query_intent
groundx_retrieve     → queries GroundX for PDF context
qdrant_retrieve      → hybrid search over audio transcripts + PDF chunks
ocr_node             → runs Gemma4 vision on attached image
context_synthesis    → combines all retrieved context
answer_node          → generates final response with Gemma4
```

**Graph definition** (`backend/core/agent/graph.py`):

```
START
  ↓
router_node
  ↓
[conditional edge based on query_intent]
  ├─→ groundx_retrieve ─┐
  ├─→ qdrant_retrieve ──┤
  ├─→ ocr_node ─────────┤
  ↓                     ↓
context_synthesis ←─────┘
  ↓
answer_node
  ↓
END
```

**Streaming:** Each node yields a `ThinkingStep` event via `astream_events` API.

### 5.3 Ingestion Pipelines

#### 5.3.1 PDF Ingestion
**File:** `backend/core/ingestion/pdf_ingestor.py`

```
1. Receive PDF file → save to data/uploads/
2. Upload to GroundX via groundx-python-sdk
3. Poll GroundX for indexing completion (with progress)
4. Store metadata in SQLite (file_id, groundx_id, status)
5. Return file_id to frontend
```

#### 5.3.2 Audio Ingestion
**File:** `backend/core/ingestion/audio_ingestor.py`

```
1. Receive audio file → save to data/audio/
2. Run faster-whisper transcription
3. Chunk transcript (semantic chunking, ~500 tokens each)
4. Embed chunks with nomic-embed-text via Ollama
5. Store chunks in Qdrant (with metadata: file_id, chunk_index)
6. Store transcript in SQLite
7. Return file_id
```

#### 5.3.3 Image Ingestion (OCR)
**File:** `backend/core/ingestion/image_processor.py`

```
1. Receive image file → save to data/images/
2. Send to Gemma4 vision via Ollama
3. Extract structured text + scene understanding
4. Store result in SQLite (ocr_results table)
5. Return file_id + extracted_text
```

### 5.4 Retrieval Strategy

**Hybrid Search in Qdrant** (`backend/core/retrieval/qdrant_client.py`):

```
For each query:
1. Generate dense vector (nomic-embed-text, 768d)
2. Tokenize query for BM25 sparse vector
3. Query Qdrant with both vectors
4. RRF fusion (Reciprocal Rank Fusion) of results
5. Return top-k (default k=5)
```

**Qdrant collection schema:**
```
{
  "vectors": {
    "dense": {"size": 768, "distance": "Cosine"},
    "sparse": {"index": {"on_disk": false}}
  },
  "payload_schema": {
    "file_id": "keyword",
    "file_type": "keyword",   // "audio" or "pdf"
    "chunk_index": "integer",
    "chunk_text": "text",
    "created_at": "datetime"
  }
}
```

---

## 6. Database Schema

### 6.1 SQLite Tables (via SQLAlchemy)

```python
class Project(Base):
    __tablename__ = "projects"
    id: int (primary key, autoincrement)
    name: str (unique, not null)
    created_at: datetime (default now)

class Chat(Base):
    __tablename__ = "chats"
    id: str (UUID, primary key)
    title: str (auto-generated from first message)
    project_id: Optional[int] (FK to projects.id, nullable)
    model_provider: str  # "ollama" | "gemini" | "grok"
    model_name: str
    created_at: datetime
    updated_at: datetime

class Message(Base):
    __tablename__ = "messages"
    id: int (primary key, autoincrement)
    chat_id: str (FK to chats.id)
    role: str  # "user" | "assistant"
    content: str (text)
    thinking_steps: JSON  # list of {"step": str, "status": str, "duration_ms": int}
    retrieved_context: JSON  # list of {"file_id": str, "chunk": str, "score": float}
    attached_files: JSON  # list of file_ids
    created_at: datetime

class File(Base):
    __tablename__ = "files"
    id: str (UUID, primary key)
    original_name: str
    file_type: str  # "pdf" | "audio" | "image"
    disk_path: str
    size_bytes: int
    groundx_id: Optional[str]  # for PDFs
    qdrant_collection: Optional[str]  # for indexed files
    indexing_status: str  # "pending" | "processing" | "indexed" | "failed"
    created_at: datetime

class OCRResult(Base):
    __tablename__ = "ocr_results"
    id: int (primary key)
    file_id: str (FK to files.id)
    extracted_text: str (text)
    model_used: str
    created_at: datetime

class Transcript(Base):
    __tablename__ = "transcripts"
    id: int (primary key)
    file_id: str (FK to files.id)
    transcript_text: str (text)
    duration_seconds: float
    language: str
    created_at: datetime

class AppSettings(Base):
    __tablename__ = "app_settings"
    id: int (primary key, always 1 — singleton)
    model_provider: str
    model_name: str
    gemini_api_key_encrypted: Optional[str]
    grok_api_key_encrypted: Optional[str]
    theme: str  # "light" | "dark"
    updated_at: datetime

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id: int (primary key)
    chat_id: str (FK to chats.id)
    message_id: int (FK to messages.id)
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    created_at: datetime
```

### 6.1.2 Database Indexes

All indexes are created via SQLAlchemy `Index` definitions:

```python
# Chat indexes
Index("idx_chats_updated_at", Chat.updated_at.desc())
Index("idx_chats_project_id", Chat.project_id)

# Message indexes
Index("idx_messages_chat_id_created", Message.chat_id, Message.created_at)

# File indexes
Index("idx_files_type", File.file_type)
Index("idx_files_created_at", File.created_at.desc())
Index("idx_files_status", File.indexing_status)

# OCR indexes
Index("idx_ocr_file_id", OCRResult.file_id)

# Transcript indexes
Index("idx_transcripts_file_id", Transcript.file_id)

# Evaluation indexes
Index("idx_eval_chat_id", EvaluationResult.chat_id)
Index("idx_eval_message_id", EvaluationResult.message_id)
```

### 6.2 Qdrant Collections

**Collection name:** `industrial_assistant`

```json
{
  "vectors": {
    "dense": { "size": 768, "distance": "Cosine" },
    "sparse": { }
  },
  "shard_number": 1,
  "replication_factor": 1
}
```

---

## 7. API Contract

### 7.1 Chat Endpoints

#### POST /api/chat/stream
**Description:** Send a message and stream the agent's response.

**Request body:**
```json
{
  "chat_id": "uuid-or-null-for-new",
  "message": "What is the main function of the machine?",
  "attached_files": ["file-uuid-1", "file-uuid-2"]
}
```

**Response:** Server-Sent Events stream

**Event types:**
```
event: thinking_step
data: {"step": "Reading PDF documents...", "status": "in_progress", "node": "groundx_retrieve"}

event: thinking_step
data: {"step": "Reading PDF documents...", "status": "completed", "node": "groundx_retrieve", "duration_ms": 1240}

event: token
data: {"content": "The main"}

event: token
data: {"content": " function"}

event: sources
data: {"sources": [{"file_id": "...", "filename": "manual.pdf", "chunk": "...", "score": 0.92}]}

event: done
data: {"chat_id": "uuid", "message_id": 42}
```

#### GET /api/chats
**Returns:** List of all chats (sorted by updated_at DESC)

#### GET /api/chat/{chat_id}
**Returns:** Full chat with all messages

#### DELETE /api/chat/{chat_id}
**Returns:** 204 No Content

### 7.2 Ingestion Endpoints

#### POST /api/ingest/pdf
**Request:** multipart/form-data with `file` field
**Returns:**
```json
{
  "file_id": "uuid",
  "filename": "manual.pdf",
  "status": "processing"
}
```

#### POST /api/ingest/audio
**Request:** multipart/form-data with `file` field
**Returns:** same shape as PDF

#### POST /api/ingest/image
**Request:** multipart/form-data with `file` field
**Returns:** same shape + `extracted_text` field

### 7.3 OCR Endpoints

#### GET /api/ocr/history
**Returns:** List of all OCR'd images with metadata

#### GET /api/ocr/{file_id}
**Returns:** Single OCR result with extracted text

### 7.4 Evaluation Endpoints

#### POST /api/evaluate
**Request body:**
```json
{
  "chat_id": "uuid",
  "message_id": 42
}
```
**Returns:** RAGAS metrics (streamed via SSE during computation)

### 7.5 Projects Endpoints

Standard CRUD: POST/GET/PUT/DELETE /api/projects
Plus: POST /api/projects/{id}/chats — move chat to project

### 7.6 Settings Endpoints

#### GET /api/settings
**Returns:** Current settings (API keys masked)

#### PUT /api/settings
**Request:**
```json
{
  "model_provider": "ollama",
  "model_name": "gemma4:latest",
  "theme": "light"
}
```

#### POST /api/settings/test-connection
**Returns:** `{"status": "connected" | "failed", "details": "..."}`

### 7.7 File Upload Constraints

All file uploads are validated at the FastAPI boundary using `UploadFile` with explicit size and MIME type checks.

| File Type | Max Size | Allowed MIME Types |
|-----------|----------|---------------------|
| PDF | 100 MB | `application/pdf` |
| Audio | 100 MB | `audio/mpeg`, `audio/wav`, `audio/m4a`, `audio/ogg` |
| Image | 25 MB | `image/jpeg`, `image/png`, `image/webp` |

**Validation behavior:**
- Size exceeded: HTTP 413 Payload Too Large with error message
- Invalid MIME type: HTTP 415 Unsupported Media Type with error message
- Filename sanitized: No path traversal, max 255 characters

**Example error response:**
```json
{
  "error": "ValidationError",
  "message": "File size (150 MB) exceeds maximum allowed size (100 MB) for PDF files",
  "details": {
    "file_type": "pdf",
    "max_size_mb": 100,
    "actual_size_mb": 150
  }
}
```

---

## 8. Project Folder Structure

```
industrial-ai-assistant/
│
├── backend/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entry
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       ├── ingest.py
│   │       ├── ocr.py
│   │       ├── evaluation.py
│   │       ├── projects.py
│   │       ├── files.py
│   │       └── settings.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── state.py                 # AgentState definition
│   │   │   ├── nodes.py                 # All graph nodes
│   │   │   ├── graph.py                 # Graph composition
│   │   │   ├── tools.py                 # Tool definitions
│   │   │   └── streaming.py             # SSE event helpers
│   │   │
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_ingestor.py
│   │   │   ├── audio_ingestor.py
│   │   │   ├── image_processor.py
│   │   │   └── chunking.py              # Semantic chunking utility
│   │   │
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── qdrant_client.py         # Hybrid search wrapper
│   │   │   ├── groundx_client.py        # GroundX wrapper
│   │   │   └── fusion.py                # RRF implementation
│   │   │
│   │   ├── evaluation/
│   │   │   ├── __init__.py
│   │   │   └── ragas_eval.py
│   │   │
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── ollama_client.py
│   │       ├── gemini_client.py
│   │       ├── grok_client.py
│   │       └── llm_factory.py           # Returns LLM based on settings
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py                  # Engine + session
│   │   ├── models.py                    # SQLAlchemy models
│   │   ├── crud.py                      # CRUD operations
│   │   └── migrations/                  # Alembic migrations
│   │       └── versions/
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py                      # Pydantic models for chat API
│   │   ├── ingest.py
│   │   ├── settings.py
│   │   └── evaluation.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                  # pydantic-settings
│   │
│   └── utils/
│       ├── __init__.py
│       ├── encryption.py                # API key encryption
│       ├── logging.py                   # Structured logging setup
│       └── file_helpers.py
│
├── frontend/
│   ├── app.py                           # Streamlit entry point
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py
│   │   ├── status_bar.py
│   │   ├── starburst_icon.py            # Animated SVG component
│   │   ├── thinking_card.py
│   │   ├── message_card.py
│   │   ├── input_bar.py
│   │   ├── source_chips.py
│   │   └── settings_modal.py
│   │
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── chat_tab.py
│   │   ├── documents_tab.py
│   │   ├── ocr_tab.py
│   │   ├── analysis_tab.py
│   │   └── tools_tab.py
│   │
│   ├── styles/
│   │   ├── main.css                     # All custom styles
│   │   └── load_css.py                  # CSS injection helper
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   └── session.py                   # Streamlit session state helpers
│   │
│   └── utils/
│       ├── __init__.py
│       ├── api_client.py                # All HTTP/SSE calls
│       └── sse_handler.py               # SSE event parser
│
├── data/                                # Created at runtime, .gitkept
│   ├── uploads/                         # PDFs
│   ├── audio/                           # Audio files
│   └── images/                          # OCR images
│
├── tests/
│   ├── backend/
│   │   ├── test_agent.py
│   │   ├── test_ingestion.py
│   │   ├── test_retrieval.py
│   │   └── test_api.py
│   └── conftest.py
│
├── scripts/
│   ├── init_db.py                       # Initialize SQLite + Alembic
│   ├── setup_qdrant_collection.py      # Create Qdrant collection
│   ├── generate_secret_key.py          # Generate Fernet key for .env
│   └── verify_environment.py            # Pre-flight checks
│
├── docker-compose.yml                   # Qdrant + (optional) backend
├── environment.yml                      # Miniconda env definition
├── requirements.txt                     # Pip requirements (mirror)
├── .env.example                         # Template env file
├── .gitignore
├── README.md                            # Complete user guide
├── PLAN.md                              # This file
└── CONSTITUTION.md                      # Development principles
```

---

## 9. Environment & Dependencies

### 9.1 Miniconda Environment

**Environment name:** `industrial-ai`
**Python version:** 3.11

**`environment.yml`:**
```yaml
name: industrial-ai
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - pip
  - pip:
    - -r requirements.txt
```

### 9.2 Python Dependencies (`requirements.txt`)

Pinned versions to prevent conflicts:

```
# Web framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
sse-starlette==2.1.3

# Frontend
streamlit==1.40.0
httpx==0.27.2
httpx-sse==0.4.0

# Agent
langgraph==0.2.45
langchain-core==0.3.15
langchain-ollama==0.2.0

# Models
ollama==0.4.0
faster-whisper==1.0.3
groundx==2.3.0

# Vector DB
qdrant-client==1.12.0

# Evaluation
ragas==0.2.6
datasets==3.1.0

# Database
sqlalchemy==2.0.36
aiosqlite==0.20.0
alembic==1.13.3

# Config & validation
pydantic==2.9.2
pydantic-settings==2.6.0
python-dotenv==1.0.1

# Utilities
cryptography==43.0.3
loguru==0.7.2
tenacity==9.0.0

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2

# Optional model providers
google-generativeai==0.8.3   # for Gemini
openai==1.54.0                # for Grok (uses OpenAI-compatible API)
```

### 9.3 External Services

| Service | Setup |
|---------|-------|
| Ollama | Install from ollama.com, run `ollama pull gemma3:latest` and `ollama pull nomic-embed-text` |
| Qdrant | `docker-compose up -d qdrant` |
| GroundX | Sign up at eyelevel.ai, get free-tier API key |

### 9.4 .env Template

```bash
# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend
FRONTEND_PORT=8501
BACKEND_API_URL=http://localhost:8000

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=gemma3:latest
OLLAMA_EMBED_MODEL=nomic-embed-text

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=industrial_assistant

# GroundX
GROUNDX_API_KEY=your-key-here
GROUNDX_BUCKET_NAME=industrial-docs

# Database
DATABASE_URL=sqlite+aiosqlite:///./industrial_ai.db

# Encryption (for API keys at rest)
SECRET_KEY=generate-with-fernet

## Generating SECRET_KEY

Before first run, generate a Fernet-compatible encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and set it as `SECRET_KEY` in your `.env` file.

Alternatively, run the helper script (created in Phase 1):
```bash
python scripts/generate_secret_key.py
```

**IMPORTANT:** Do NOT use `openssl rand -base64 32` — it produces standard base64 with `+` and `/` characters, but Fernet requires URL-safe base64 (`-` and `_`). The key would fail validation at runtime.

**WARNING:** Do NOT auto-generate the key on first run — if `.env` is ever lost or recreated, all encrypted API keys stored in SQLite become unrecoverable.

# Optional external LLMs
GEMINI_API_KEY=
GROK_API_KEY=

# Whisper
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=auto       # auto | cuda | cpu
WHISPER_COMPUTE_TYPE=auto # auto | float16 | int8
```

### 9.5 docker-compose.yml

```yaml
version: "3.8"
services:
  qdrant:
    image: qdrant/qdrant:v1.12.0
    container_name: industrial-ai-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    restart: unless-stopped
```

---

## 10. Implementation Phases

### Phase 1 — Foundation & Setup (Day 1)

**Goal:** Working scaffolding with all infrastructure connected.

**Deliverables:**
- [ ] Folder structure created
- [ ] Miniconda environment initialized
- [ ] `requirements.txt` installed cleanly
- [ ] `.env` configured from template
- [ ] Qdrant running in Docker
- [ ] Ollama models pulled
- [ ] SQLite database created with all tables (via Alembic)
- [ ] FastAPI server boots, returns health check
- [ ] Streamlit app boots, shows empty layout

**Acceptance criteria:**
- `curl http://localhost:8000/health` → `{"status": "ok"}`
- `streamlit run frontend/app.py` shows sidebar + tabs (empty content OK)
- `python scripts/verify_environment.py` passes all checks

**Files to create:**
- All folder structure (empty `__init__.py` files)
- `backend/main.py` (minimal app)
- `backend/config/settings.py`
- `backend/database/database.py`
- `backend/database/models.py` (all tables)
- `frontend/app.py` (basic layout)
- `frontend/styles/main.css` (skeleton)
- `docker-compose.yml`
- `environment.yml`
- `requirements.txt`
- `.env.example`
- `scripts/init_db.py`
- `scripts/generate_secret_key.py`
- `scripts/verify_environment.py`

### Phase 2 — Ingestion Pipeline (Day 2)

**Goal:** All three file types can be ingested via API.

**Deliverables:**
- [ ] `pdf_ingestor.py` working (upload → GroundX → indexed)
- [ ] `audio_ingestor.py` working (upload → Whisper → chunks → Qdrant)
- [ ] `image_processor.py` working (upload → Gemma4 → text)
- [ ] `qdrant_client.py` with hybrid search setup
- [ ] `/api/ingest/{pdf,audio,image}` endpoints functional
- [ ] Files saved to disk under `data/`
- [ ] Metadata persisted to SQLite

**Acceptance criteria:**
- Upload sample PDF → file appears in `data/uploads/`, GroundX shows it indexed, SQLite has row
- Upload sample audio → transcript visible in SQLite, chunks in Qdrant
- Upload sample image → OCR text in SQLite

**Files to create:**
- `backend/core/ingestion/pdf_ingestor.py`
- `backend/core/ingestion/audio_ingestor.py`
- `backend/core/ingestion/image_processor.py`
- `backend/core/ingestion/chunking.py`
- `backend/core/retrieval/qdrant_client.py`
- `backend/core/retrieval/groundx_client.py`
- `backend/core/models/ollama_client.py`
- `backend/api/routes/ingest.py`
- `backend/database/crud.py` (CRUD for File, Transcript, OCRResult)
- `backend/schemas/ingest.py`

**Audio Transcription Device Detection:**

The `audio_ingestor.py` module includes device auto-detection with graceful fallback:

```python
from loguru import logger
from backend.config.settings import settings

def get_whisper_device() -> tuple[str, str]:
    """Detect available device with safe fallback to CPU.

    Returns:
        Tuple of (device, compute_type) suitable for faster-whisper.
    """
    if settings.WHISPER_DEVICE != "auto":
        return (settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE)

    try:
        import torch
        if torch.cuda.is_available():
            logger.info("CUDA detected — using GPU for Whisper transcription")
            return ("cuda", "float16")
    except ImportError:
        pass

    logger.warning(
        "GPU not available — falling back to CPU. "
        "Transcription will be approximately 10x slower than GPU."
    )
    return ("cpu", "int8")
```

**Behavior:**
- Default `WHISPER_DEVICE=auto` enables auto-detection
- Explicit setting (`cuda`/`cpu`) overrides auto-detection
- CPU mode uses `int8` quantization for better speed
- Clear log line informs user which mode is active

### Phase 3 — LangGraph Agent (Day 3)

**Goal:** Agent answers questions over ingested content with streaming thinking steps.

**Deliverables:**
- [ ] `AgentState` defined
- [ ] All nodes implemented (router, groundx_retrieve, qdrant_retrieve, ocr, synthesis, answer)
- [ ] Graph compiled and runs end-to-end
- [ ] SSE streaming endpoint `/api/chat/stream` emits thinking_step + token events
- [ ] Conversation memory persisted to SQLite

**Acceptance criteria:**
- POST to `/api/chat/stream` with question about ingested PDF returns streamed answer
- Each LangGraph node emits a thinking_step event
- Final answer cites correct sources
- Multi-turn conversation maintains context

**Files to create:**
- `backend/core/agent/state.py`
- `backend/core/agent/nodes.py`
- `backend/core/agent/graph.py`
- `backend/core/agent/tools.py`
- `backend/core/agent/streaming.py`
- `backend/core/retrieval/fusion.py`
- `backend/api/routes/chat.py`
- `backend/schemas/chat.py`

### Phase 4 — Frontend Core UI (Day 4)

**Goal:** Pixel-perfect Claude-inspired interface with working chat.

**Deliverables:**
- [ ] `main.css` complete with all design tokens
- [ ] Animated starburst SVG component
- [ ] Sidebar fully styled (Logo, New Chat, Search, Chats, Projects, Knowledge Base, Tools, Settings)
- [ ] Top tab bar with active states
- [ ] Status indicator (top-right) connected to backend
- [ ] Chat tab: user message + thinking card + AI response card all functional
- [ ] Input bar with all controls (Attach, Audio File, Tools, Model, Send)
- [ ] SSE streaming consumed and rendered

**Acceptance criteria:**
- Visual match with `Proposed_frontend_design.png` (>90% similarity)
- Sending a message triggers SSE, thinking steps appear progressively
- Markdown rendered with custom colors (blue headings, orange accents)
- Source chips appear below response
- Hover states work on all interactive elements

**Files to create:**
- `frontend/styles/main.css` (complete)
- `frontend/styles/load_css.py`
- `frontend/components/starburst_icon.py`
- `frontend/components/sidebar.py`
- `frontend/components/status_bar.py`
- `frontend/components/thinking_card.py`
- `frontend/components/message_card.py`
- `frontend/components/input_bar.py`
- `frontend/components/source_chips.py`
- `frontend/tabs/chat_tab.py`
- `frontend/utils/api_client.py`
- `frontend/utils/sse_handler.py`
- `frontend/state/session.py`

### Phase 5 — Remaining Tabs (Day 5)

**Goal:** Documents, OCR, Analysis, Tools tabs all functional.

**Deliverables:**
- [ ] Documents tab: grid of files, upload modal, delete confirmation
- [ ] OCR tab: image gallery, click → opens new chat with image attached
- [ ] Analysis tab: 3 sections (trace + context + thinking) showing last conversation
- [ ] Tools tab: RAGAS view + Audio Transcriber view (toggleable)

**Acceptance criteria:**
- All tabs visually consistent with main theme
- Documents tab supports upload + delete cycle
- Clicking OCR image opens new chat with pre-attached image
- Analysis tab shows real data from last LangGraph run
- Tools tab can run RAGAS evaluation on last message

**Files to create:**
- `frontend/tabs/documents_tab.py`
- `frontend/tabs/ocr_tab.py`
- `frontend/tabs/analysis_tab.py`
- `frontend/tabs/tools_tab.py`
- `backend/core/evaluation/ragas_eval.py`
- `backend/api/routes/ocr.py`
- `backend/api/routes/evaluation.py`
- `backend/api/routes/files.py`

### Phase 6 — Advanced Features (Day 6)

**Goal:** Projects, model switching, settings, dark mode.

**Deliverables:**
- [ ] Projects: create project, move chats into projects (drag-and-drop or context menu)
- [ ] Model switcher works (Ollama / Gemini / Grok)
- [ ] API key field encrypts and persists
- [ ] Test Connection button validates each provider
- [ ] Dark mode toggle works (CSS variables swap)
- [ ] Status bar live-updates when model changes

**Acceptance criteria:**
- Switching from Ollama to Gemini sends next message through Gemini API
- API keys stored encrypted in SQLite (verified with sqlite3 CLI)
- Dark mode applies to all components consistently
- Projects organize chats correctly in sidebar

**Files to create:**
- `frontend/components/settings_modal.py`
- `backend/core/models/gemini_client.py`
- `backend/core/models/grok_client.py`
- `backend/core/models/llm_factory.py`
- `backend/utils/encryption.py`
- `backend/api/routes/settings.py`
- `backend/api/routes/projects.py`

### Phase 7 — Testing, Polish & Demo (Day 7)

**Goal:** Production-ready demo with sample data.

**Deliverables:**
- [ ] End-to-end test with real pump maintenance manual PDF
- [ ] End-to-end test with engineer audio recording
- [ ] End-to-end test with nameplate image
- [ ] RAGAS evaluation runs successfully on real chats
- [ ] All animations smooth (no jank)
- [ ] Error states handled gracefully (Ollama down, GroundX timeout, etc.)
- [ ] README.md complete with install + usage, including troubleshooting for:
  - GPU detection (check logs for "CUDA detected — using GPU")
  - Slow audio transcription (falls back to CPU if GPU unavailable)
- [ ] Sample data folder with demo files
- [ ] Loom-style demo script written

**Acceptance criteria:**
- Cold-start to first answer in < 30 seconds
- All 5 tabs work without errors
- Restart preserves all chats, projects, files
- Demo script can be followed by anyone to reproduce key flows

**Files to create:**
- `README.md` (full)
- `tests/backend/test_agent.py`
- `tests/backend/test_ingestion.py`
- `tests/backend/test_retrieval.py`
- `tests/backend/test_api.py`
- `scripts/seed_demo_data.py`

---

## 11. Testing Strategy

### 11.1 Unit Tests (pytest)

- Each ingestion module: test with fixture file
- Retrieval module: test hybrid search with seeded vectors
- Agent nodes: test each node independently with mocked dependencies
- CRUD operations: test all database functions

### 11.2 Integration Tests

- Full chat flow: ingest PDF → ask question → verify answer cites source
- File deletion: delete file → verify removed from disk, SQLite, Qdrant
- Project move: create project → move chat → verify association

### 11.3 Manual UX Testing Checklist

- [ ] Animations don't stutter on RTX 3060
- [ ] Streaming feels real-time (< 200ms per token)
- [ ] Hover states all respond within 150ms
- [ ] Dark mode toggle is instantaneous
- [ ] File upload progress visible
- [ ] Error toasts appear on failures
- [ ] Long chats scroll smoothly

---

## 12. Final User Experience

### 12.1 First-Time User Journey

```
1. User runs `streamlit run frontend/app.py` and opens browser
2. Sees empty Industrial AI Assistant with sidebar
3. Status bar shows: 🟢 Connected to local model · Gemma4 · Ollama
4. Clicks "+ New Chat"
5. Drags pump_manual.pdf onto input bar
6. Toast appears: "Indexing pump_manual.pdf..."
7. Types: "What is the recommended maintenance interval for the bearings?"
8. Sees Thinking card animate:
   ✓ Analyzing your query...
   ⟳ Reading PDF documents...  (then ✓)
   ⟳ Searching memory (RAG)...  (then ✓)
   ⟳ Analyzing information...  (then ✓)
   ⟳ Generating answer...  (then ✓)
9. Sees response stream in with:
   - Blue heading "Maintenance Schedule"
   - Bulleted list with intervals
   - Source chips: [pump_manual.pdf]
10. Clicks "Analysis" tab to see LangGraph trace
11. Switches to "Tools" → clicks "Run Evaluation on Last Chat"
12. Sees RAGAS metrics: Faithfulness 0.92, Answer Relevancy 0.88, ...
```

### 12.2 Daily Usage Journey

```
1. User opens app — sees previous chats in sidebar with timestamps
2. Selects "Pump maintenance guide" from yesterday
3. Continues conversation with full context preserved
4. Uploads photo of vibration gauge via Attach button
5. AI auto-runs OCR, replies with reading interpretation
6. User clicks "OCR" tab to browse all previously analyzed images
7. Clicks an image → opens new chat scoped to that image
```

---

## 13. Deliverables

### 13.1 Code Deliverables
- Complete `industrial-ai-assistant/` repository
- All source code organized per Section 8
- `environment.yml` and `requirements.txt`
- `docker-compose.yml`
- Alembic migrations

### 13.2 Documentation Deliverables
- `README.md` — installation, usage, troubleshooting
- `PLAN.md` — this document
- `CONSTITUTION.md` — development principles
- `docs/architecture.md` — architecture diagrams + decisions
- `docs/api.md` — API endpoint reference

### 13.3 Demo Deliverables
- Sample pump manual PDF in `data/samples/`
- Sample audio recording in `data/samples/`
- Sample nameplate image in `data/samples/`
- Demo script (markdown walkthrough)
- 3-minute screen recording

---

## End of Plan

> Execute this plan phase by phase. Do not skip ahead.
> Validate acceptance criteria for each phase before moving on.
> Refer to `CONSTITUTION.md` for code quality standards throughout.