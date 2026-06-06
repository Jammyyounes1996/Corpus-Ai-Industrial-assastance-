# Quickstart: Frontend Core UI

This guide validates the Phase 4 React frontend against the verified backend contracts. It must not rely on mock backend data or fake success states.

## 1. Install Frontend Dependencies

1. Open a terminal at the repository root.
2. Go to the frontend directory: `cd frontend`.
3. If `package.json` does not exist yet, complete the Phase 4 dependency setup tasks first.
4. Install dependencies with the package manager selected by the implementation tasks, normally `npm install`.
5. Confirm scripts exist with `npm run`.

Expected result: frontend scripts for `dev`, `build`, `test`, and `lint` are available, and no heavy UI framework was added without approval.

## 2. Run Backend

1. From the repository root, activate the project Python environment.
2. Start required local services such as Qdrant and Ollama using the project-standard setup.
3. Start FastAPI on the configured backend port, default `8001`.
4. Verify health: `GET http://localhost:8001/health`.

Expected result: `/health` returns JSON with `status`, `version`, `database`, `qdrant`, and `ollama`.

## 3. Run Frontend

1. Open a terminal in `frontend/`.
2. Set `VITE_BACKEND_BASE_URL=http://localhost:8001` in the frontend environment file or shell.
3. Start the dev server with the configured script, normally `npm run dev`.
4. Open the shown frontend URL in a desktop browser at 1280px width or wider.

Expected result: the React app renders the sidebar, Chat tab, workspace tabs, input bar, and status badge without launching Streamlit.

## 4. Configure Backend Base URL

1. Confirm the frontend reads backend base URL from `VITE_BACKEND_BASE_URL` through `frontend/src/config.ts`.
2. Confirm services import the config value instead of hardcoding backend URLs in components.
3. If the backend is on a different host or port, update only the environment value.

Expected result: all frontend API calls use the configured backend base URL.

## React Dev Server and CORS

The current backend CORS configuration is known to allow the existing Streamlit origin:

- `http://localhost:8501`

The React/Vite dev server may run on:

- `http://localhost:5173`

Because backend CORS/config changes require explicit user approval, the preferred development workaround is a frontend-only Vite proxy, not a backend CORS modification.

Development-only Vite proxy example:

```ts
server: {
  proxy: {
    "/api": {
      target: "http://localhost:8001",
      changeOrigin: true,
    },
    "/health": {
      target: "http://localhost:8001",
      changeOrigin: true,
    },
  },
}
```

Validation steps:

1. Start the backend on `http://localhost:8001`.
2. Start the React/Vite dev server on `http://localhost:5173`.
3. Confirm frontend calls `/health` through the proxy.
4. Confirm frontend calls `/api/chats` through the proxy.
5. Confirm no backend CORS/config files were modified.
6. If CORS still blocks requests, stop and report instead of changing backend.

## 5. Test Chat Streaming

1. Keep backend and frontend running.
2. Open the Chat tab.
3. Type a non-empty industrial equipment question.
4. Click Send or press Enter.
5. In browser dev tools, confirm the frontend creates or reuses a backend chat with `POST /api/chats` before streaming.
6. Confirm the stream request is `POST /api/chat/{chat_id}/stream`, not `POST /api/chat/stream`.
7. Confirm the request body uses `query` and, when applicable, `attached_files` as backend file ID strings.
8. Confirm the response is parsed as SSE frames with `thinking_step`, `token`, `sources`, `done`, and `error` support.
9. Confirm tokens appear progressively without waiting for a final JSON response.

Expected result: the assistant response streams token-by-token, thinking steps render as events arrive, and the message completes on `done` when no prior `error` event occurred.

## 6. Test File Upload Before Chat Send

1. Click Attach in the input bar.
2. Select a supported PDF, image, or audio file.
3. Confirm a preview chip appears above the input.
4. For images, confirm a thumbnail appears.
5. Type a non-empty message and click Send.
6. Confirm each selected file is uploaded before chat streaming starts.
7. Confirm PDFs use `POST /api/ingest/pdf`.
8. Confirm audio files use `POST /api/ingest/audio`.
9. Confirm images use `POST /api/ingest/image`.
10. Confirm each upload request uses `multipart/form-data` with one `file` field.
11. Confirm the stream request includes only returned `file_id` strings in `attached_files`.

Expected result: upload success creates backend attachment references; upload failure blocks stream start and preserves the user text/files for retry or removal.

## 7. Test Source Chips

1. Send a chat request expected to retrieve document context.
2. Wait for a `sources` stream event.
3. Confirm source chips appear below the assistant message.
4. Confirm each chip uses backend fields such as `filename`, `file_type`, `chunk_index`, `score`, and `excerpt`.
5. Confirm only 3 chips are visible when more than 3 sources exist.
6. Confirm the `+N more` chip count matches the hidden source count.

Expected result: sources display only backend-provided citation data and never fake filenames or scores.

## 8. Test Status Indicator

1. Load the frontend while the backend is running.
2. Confirm the status service calls `GET /health`.
3. Confirm the compact badge shows connected, degraded, loading, or disconnected text.
4. Open the expanded status menu.
5. Confirm backend `version`, `database`, `qdrant`, and `ollama` reflect real `/health` values.
6. Confirm active model and provider show `Unknown` unless a real selected chat or model-list interaction supplied them.
7. Confirm RAG does not show fake `Enabled`; it may show `Unknown` or a limited vector DB label from Qdrant.
8. Confirm OCR and GPU show `Unknown`, `Unavailable`, or are hidden if the design chooses optional display.
9. Stop the backend and confirm the badge changes to disconnected or unavailable.

Expected result: no fake model, provider, RAG, OCR, GPU, or backend readiness values are shown.

## 9. Test Placeholder Tabs

1. Click Documents.
2. Click OCR.
3. Click Analysis.
4. Click Tools.
5. Confirm each tab displays a polished placeholder view.
6. Confirm no non-Chat tab calls backend workflows or implements functional document/OCR/analysis/tool screens.
7. Return to Chat and confirm local in-memory chat state is still available.

Expected result: non-Chat tabs are navigable and visually complete, but remain placeholders for Phase 4.

## 10. Test Reduced Motion

1. Enable reduced motion in the operating system or browser accessibility settings.
2. Reload the frontend.
3. Confirm the starburst does not continuously rotate or pulse.
4. Confirm tab transitions, hover motion, thinking indicators, and streaming cursor animation are minimized.
5. Confirm all controls remain usable and visible.

Expected result: reduced-motion users receive the same functionality without distracting decorative motion.

## 11. Run Tests

1. Open a terminal in `frontend/`.
2. Run the configured test command, normally `npm test`.
3. Run the configured lint command, normally `npm run lint`.
4. Run the configured build command, normally `npm run build`.

Expected result: parser, upload service, status service, hooks, components, markdown, source chips, tabs, and accessibility-related tests pass.

## 12. Verify No Fake Or Mock Backend Data Is Shown

1. Search the frontend source for hardcoded successful backend status labels.
2. Confirm missing status fields render as `Unknown`, `Unavailable`, degraded, disconnected, or hidden.
3. Confirm upload success requires a real upload response containing `file_id`.
4. Confirm source chips require a real `sources` event.
5. Confirm chat streaming requires a real backend chat ID and real SSE response.
6. Confirm no mock endpoint, mock stream event, fake model name, fake provider, fake RAG enabled state, fake OCR ready state, or fake GPU available state appears in production UI.

Expected result: the frontend gracefully handles unavailable data but never fabricates backend success.

## 13. Known Limitations Of Phase 4

- Browser-based React streaming may require a Vite proxy for the React dev-server origin; current backend contract notes CORS for `http://localhost:8501`, while React/Vite may run on `http://localhost:5173`.
- Chat sidebar sessions are local frontend state only and reset on browser refresh.
- Backend-persisted chat history management is out of scope.
- Non-Chat tabs are placeholders only.
- Attachment-only messages are out of scope; text is required to send.
- Upload endpoints accept one file per request; multiple files require multiple requests.
- `/health` does not expose active model, provider, explicit RAG enabled, OCR readiness, or GPU availability.
- PDF ingestion may return `processing`; the frontend must not display it as fully indexed unless the backend says so.
- Stream `error` events mark the assistant response failed even if a later `done` event arrives.
