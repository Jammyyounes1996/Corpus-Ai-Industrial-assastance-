/* API Response Types */
/*
  TypeScript interfaces for API responses and request payloads
  Based on backend contracts and streaming specifications
*/



// Chat creation response
export interface CreateChatResponse {
  id: string
  title: string
  provider: string
  model: string
}

// File upload responses
export interface UploadResponse {
  file_id: string
  filename: string
  file_type: 'pdf' | 'image' | 'audio'
  size: number
  upload_timestamp: Date
}

export interface UploadErrorResponse {
  error: string
  code: 'UNSUPPORTED_TYPE' | 'PAYLOAD_TOO_LARGE' | 'VALIDATION_ERROR' | 'INTERNAL_ERROR'
  file?: string
}

// Stream request body
export type AnswerMode = "groundx" | "audio" | "general"

export interface StreamRequestBody {
  query: string
  attached_files?: string[]
  model?: string
  provider?: string
  answer_mode?: AnswerMode
}

// Stream events (chat.ts contains more detailed versions)
export interface StreamEventBase {
  event: 'thinking_step' | 'token' | 'sources' | 'done' | 'error'
}

// Chat service types
export interface ChatStreamOptions {
  chatId?: string // backendChatId
  signal?: AbortSignal
  onMessage?: (token: string) => void
  onThinking?: (step: { type: string; content: string; timestamp: string }) => void
  onSources?: (sources: Array<{ file_id: string; filename: string; file_type: string; chunk_index: number; excerpt: string; score?: number }>) => void
  onComplete?: (messageId: string, chatId: string) => void
  onError?: (error: string) => void
}

// API client configuration
export interface ApiConfig {
  baseUrl: string
  headers?: Record<string, string>
  timeout?: number
}

// Request state types
export interface RequestState<T = unknown> {
  isLoading: boolean
  error: string | null
  data: T | null
}

export interface UploadState extends RequestState<void> {
  progress: number
  uploadedFiles: UploadResponse[]
  failedFiles: UploadErrorResponse[]
}