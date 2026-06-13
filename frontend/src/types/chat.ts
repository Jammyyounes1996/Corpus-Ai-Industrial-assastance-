/* Chat and Message Types */
/*
  TypeScript interfaces for chat sessions, messages, and streaming
  Based on data-model.md and backend contracts
*/

import { AttachedFile } from './attachments'

export interface PendingSend {
  query: string
  attachedFileIds?: string[]
  answerMode?: string
  taskType?: string
}

export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  isActive: boolean
  backendChatId?: string // Created when chat is sent to backend
  messages: Message[]
  pendingSend?: PendingSend
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  status: 'pending' | 'sending' | 'streaming' | 'complete' | 'failed' | 'cancelled'
  attachments?: AttachedFile[]
  sources?: SourceReference[]
  thinkingText?: string
  thinkingElapsedMs?: number
  thinkingSteps?: ThinkingStep[]
  usage?: UsageMetadata
  error?: string
}

export interface UsageMetadata {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  generation_time_ms: number
}

export interface ThinkingStep {
  id: string
  type: string
  content: string
  timestamp: Date
  status: 'received' | 'complete' | 'failed'
}

export interface SourceReference {
  file_id: string
  filename: string
  file_type: 'pdf' | 'image' | 'audio' | 'text'
  chunk_index: number
  score?: number
  excerpt: string
}

export interface StreamEvent {
  event: 'workflow_step' | 'thinking_delta' | 'answer_delta' | 'sources' | 'done' | 'error'
  data: unknown
}

export interface WorkflowStepEvent {
  event: 'workflow_step'
  data: {
    type: 'workflow_step'
    node: string
    status: string
    label?: string
    timestamp?: string
    duration_ms?: number
  }
}

export interface ThinkingDeltaEvent {
  event: 'thinking_delta'
  data: {
    delta: string
    elapsed_ms?: number
  }
}

export interface AnswerDeltaEvent {
  event: 'answer_delta'
  data: {
    delta: string
    message_id?: string
  }
}

export interface SourcesEvent {
  event: 'sources'
  data: {
    message_id?: string
    sources: SourceReference[]
  }
}

export interface DoneEvent {
  event: 'done'
  data: {
    message_id: string
    chat_id: string
    usage?: UsageMetadata
  }
}

export interface ErrorEvent {
  event: 'error'
  data: {
    error: string
    code?: string
    message_id?: string
  }
}

export type ChatStreamEvent = 
  | WorkflowStepEvent
  | ThinkingDeltaEvent
  | AnswerDeltaEvent
  | SourcesEvent 
  | DoneEvent 
  | ErrorEvent

export interface CreateChatRequest {
  query: string
  attached_files?: string[] // Array of file_ids from successful uploads
  model?: string
  provider?: string
}

export interface CreateChatResponse {
  id: string
  title: string
  provider: string
  model: string
}
