/* Chat and Message Types */
/*
  TypeScript interfaces for chat sessions, messages, and streaming
  Based on data-model.md and backend contracts
*/

import { AttachedFile } from './attachments'

export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  isActive: boolean
  backendChatId?: string // Created when chat is sent to backend
  messages: Message[]
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  status: 'pending' | 'sending' | 'streaming' | 'complete' | 'failed' | 'cancelled'
  attachments?: AttachedFile[]
  sources?: SourceReference[]
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
  event: 'thinking_step' | 'token' | 'sources' | 'done' | 'error'
  data: unknown
}

export interface TokenEvent {
  event: 'token'
  data: {
    token: string
    message_id?: string
  }
}

export interface ThinkingStepEvent {
  event: 'thinking_step'
  data: {
    type: string
    content: string
    timestamp: string
    step_id: string
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
  | TokenEvent 
  | ThinkingStepEvent 
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
