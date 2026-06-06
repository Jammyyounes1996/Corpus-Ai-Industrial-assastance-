# Quickstart: Phase 5 Known Limitations Fix

**Prerequisites**: Running backend (FastAPI on port 8000), running frontend (Vite on port 5173), Ollama with loaded model.

## Verification Steps

### LIM-1: OCR Image Attachment

1. Open the OCR tab in the frontend
2. Upload an image and wait for OCR processing to complete
3. Click the processed image in the gallery — "Open in Chat" action
4. Verify: a new chat session opens with the image visually attached to the first message
5. Verify: the AI response references the actual image content (not just filename)
6. Verify: the image thumbnail appears in the attachment tray

### LIM-2: Real Token Count and Generation Time

1. Open the Analysis tab
2. Submit an analysis query
3. Wait for the response to complete
4. Verify: token count shows a real number (not prefixed with "~")
5. Verify: generation time shows actual backend-measured duration
6. Verify: if backend doesn't return usage data, values show estimated indicator

### LIM-3: CSS Split

1. Open the Tools tab
2. Navigate to the Audio Transcriber section
3. Verify: audio transcriber UI renders identically (recording button, file upload, waveform display)
4. Check: `ToolsTab.css` file is under 400 lines
5. Check: `AudioTranscriber.css` file exists and is imported by `AudioTranscriber.tsx`
