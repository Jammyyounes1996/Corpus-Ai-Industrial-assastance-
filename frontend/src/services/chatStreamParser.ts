/* SSE Frame Parser for Chat Streaming */
/*
  Server-Sent Events (SSE) frame parser for chat streaming
  Handles chunked text streams, incomplete frames, and multiple frames per chunk
  Emits typed StreamEvent objects based on the chat streaming contract
*/

import {
  ChatStreamEvent,
  DoneEvent,
  ErrorEvent,
  SourceReference,
  SourcesEvent,
  ThinkingStepEvent,
  TokenEvent,
  UsageMetadata
} from '../types/chat'

export interface ParseResult {
  events: ChatStreamEvent[]
  buffer: string
}

/**
  * Parse SSE frames from a text chunk
  * @param chunk - Text chunk from the stream
  * @param buffer - Previous incomplete chunk data
  * @returns ParseResult containing events and remaining buffer
  */
export function parseSSEFrame(chunk: string, buffer: string = ''): ParseResult {
  // Safety check: ensure inputs are strings
  if (typeof chunk !== 'string') chunk = ''
  if (typeof buffer !== 'string') buffer = ''
  
  // Combine buffer with new chunk
  const combined = (buffer + chunk).replace(/\r\n/g, '\n')
  const events: ChatStreamEvent[] = []
  
  // Split by double newline (SSE frame delimiter)
  const frames = combined.split('\n\n')
  
  // Keep the last frame as it might be incomplete unless it can be parsed now.
  const completeFrames = frames.slice(0, -1)
  const finalFrame = frames[frames.length - 1] || ''
  let incompleteFrame = ''
  
  for (const frame of completeFrames) {
    if (frame.trim() === '') continue // Skip empty frames
    
    const event = parseSingleFrame(frame)
    if (event) {
      events.push(event)
    }
  }
  
  if (finalFrame.trim() === '') {
    if (frames.length === 1 && finalFrame.length > 0) {
      incompleteFrame = finalFrame
    }
  } else if (shouldBufferFinalFrame(finalFrame)) {
    incompleteFrame = finalFrame
  } else {
    const event = parseSingleFrame(finalFrame)
    if (event) events.push(event)
  }
  
  return {
    events,
    buffer: incompleteFrame
  }
}

/**
 * Parse a single SSE frame into a typed event
 * @param frame - Single SSE frame string
 * @returns ChatStreamEvent or null if invalid
 */
function parseSingleFrame(frame: string): ChatStreamEvent | null {
  const lines = frame.split('\n')
  let currentEvent: string | null = null
  let dataLines: string[] = []
  
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue // Skip empty lines within frame
    
    if (trimmed.startsWith('event:')) {
      // Handle previous event if any
      if (currentEvent && dataLines.length > 0) {
        const event = createEvent(currentEvent, dataLines.join('\n'))
        if (event) return event
      }
      
      // Start new event
      currentEvent = trimmed.substring(6).trim()
      dataLines = []
    } else if (trimmed.startsWith('data:')) {
      const data = trimmed.substring(5).trim()
      dataLines.push(data)
    } else {
      // Skip unknown line formats
      continue
    }
  }
  
  // Handle final event in the frame
  if (currentEvent && dataLines.length > 0) {
    return createEvent(currentEvent, dataLines.join('\n'))
  }
  
  return null
}

/**
 * Create a typed ChatStreamEvent from event name and data
 * @param eventName - The event type from SSE
 * @param data - The data content as string (JSON or plain text)
 * @returns ChatStreamEvent or null for invalid/unknown events
 */
function createEvent(eventName: string, data: string): ChatStreamEvent | null {
  try {
    // Parse the data as JSON if possible, otherwise keep as string
    const parsedData = tryParseJSON(data)
    
    switch (eventName) {
      case 'token':
        return validateTokenEvent(parsedData)
        
      case 'thinking_step':
        return validateThinkingStepEvent(parsedData)
        
      case 'sources':
        return validateSourcesEvent(parsedData)
        
      case 'done':
        return validateDoneEvent(parsedData)
        
      case 'error':
        return validateErrorEvent(parsedData)
        
      default:
        // Unknown event types are ignored safely
        return null
    }
  } catch (error) {
    // JSON parsing errors create a parse error event
    return {
      event: 'error',
      data: {
        error: `Failed to parse ${eventName} event data: ${error instanceof Error ? error.message : 'JSON parse error'}`,
        code: 'INVALID_JSON'
      }
    }
  }
}

function shouldBufferFinalFrame(frame: string): boolean {
  const lines = frame.split('\n')
  const hasEventLine = lines.some(line => line.trim().startsWith('event:'))
  const dataLines = lines
    .map(line => line.trim())
    .filter(line => line.startsWith('data:'))
    .map(line => line.substring(5).trim())
  
  if (!hasEventLine || dataLines.length === 0) return frame.length > 0
  
  const data = dataLines.join('\n').trim()
  if (!data.startsWith('{') && !data.startsWith('[')) return false
  
  try {
    JSON.parse(data)
    return false
  } catch {
    return true
  }
}

function isRecord(data: unknown): data is Record<string, unknown> {
  return typeof data === 'object' && data !== null && !Array.isArray(data)
}

function parseRecord(data: unknown): Record<string, unknown> | null {
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data)
      return isRecord(parsed) ? parsed : null
    } catch {
      return null
    }
  }
  
  return isRecord(data) ? data : null
}

function normalizeMessageId(value: unknown): string | null {
  if (typeof value === 'string' && value) return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return null
}

function generateFallbackStepId(data: {
  type: string
  content: string
  timestamp: string
}): string {
  const raw = `${data.type}|${data.timestamp}|${data.content}`
  let hash = 5381
  for (let i = 0; i < raw.length; i += 1) {
    hash = (hash * 33) ^ raw.charCodeAt(i)
  }
  const unsignedHash = hash >>> 0
  return `step_${unsignedHash.toString(36)}`
}

/**
  * Try to parse data as JSON, throw error if invalid
  */
function tryParseJSON(data: string): unknown {
  // Check if data looks like JSON (starts with { or [)
  const trimmed = data.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return JSON.parse(trimmed)
    } catch {
      throw new Error('JSON parse error')
    }
  }
  return data
}

/**
  * Validate and create a TokenEvent
  */
function validateTokenEvent(data: unknown): TokenEvent | null {
  // Handle both string data and object data
  if (typeof data === 'string') {
    if (!data.trim()) return null
    return {
      event: 'token',
      data: { token: data }
    }
  }
  
  const parsedData = parseRecord(data)
  if (!parsedData) return null
  
  const { token, message_id } = parsedData
  
  if (typeof token !== 'string' || !token) return null
  if (message_id !== undefined && normalizeMessageId(message_id) === null) return null
  
  const eventData: TokenEvent['data'] = { token }
  if (message_id !== undefined) {
    const normalizedId = normalizeMessageId(message_id)
    if (normalizedId) eventData.message_id = normalizedId
  }
  
  return { event: 'token', data: eventData }
}

/**
  * Validate and create a ThinkingStepEvent
  */
function validateThinkingStepEvent(data: unknown): ThinkingStepEvent | null {
  // Handle both string data and object data
  const parsedData = parseRecord(data)
  if (!parsedData) return null
  
  const { type, content, timestamp, step_id } = parsedData

  if (typeof type !== 'string' || !type) return null
  if (typeof content !== 'string' || !content) return null
  if (typeof timestamp !== 'string' || !timestamp) return null

  let normalizedStepId: string
  if (typeof step_id === 'string' && step_id) {
    normalizedStepId = step_id
  } else {
    normalizedStepId = generateFallbackStepId({ type, content, timestamp })
  }
  
  return {
    event: 'thinking_step',
      data: {
        type,
        content,
        timestamp,
        step_id: normalizedStepId
      }
    }
}

/**
  * Validate and create a SourcesEvent
  */
function validateSourcesEvent(data: unknown): SourcesEvent | null {
  // Handle both string data and object data
  const parsedData = parseRecord(data)
  if (!parsedData) return null
  
  const { message_id, sources } = parsedData
  
  if (!Array.isArray(sources)) return null
  if (sources.length === 0) return null

  let normalizedMessageId: string | undefined
  if (message_id !== undefined) {
    const parsedMessageId = normalizeMessageId(message_id)
    if (!parsedMessageId) return null
    normalizedMessageId = parsedMessageId
  }
  
  const sourceReferences: SourceReference[] = []
  for (const source of sources) {
    if (!isSourceReference(source)) return null
    sourceReferences.push(source)
  }
  
  return {
    event: 'sources',
    data: {
      ...(normalizedMessageId ? { message_id: normalizedMessageId } : {}),
      sources: sourceReferences
    }
  }
}

function isSourceReference(source: unknown): source is SourceReference {
  if (!isRecord(source)) return false
  
  return (
    typeof source.file_id === 'string' && source.file_id.length > 0 &&
    typeof source.filename === 'string' && source.filename.length > 0 &&
    ['pdf', 'image', 'audio', 'text'].includes(String(source.file_type)) &&
    typeof source.chunk_index === 'number' &&
    (source.score === undefined || typeof source.score === 'number') &&
    typeof source.excerpt === 'string' && source.excerpt.length > 0
  )
}

function isUsageMetadata(usage: unknown): usage is UsageMetadata {
  const data = parseRecord(usage)
  if (!data) return false

  return (
    typeof data.prompt_tokens === 'number' &&
    typeof data.completion_tokens === 'number' &&
    typeof data.total_tokens === 'number' &&
    typeof data.generation_time_ms === 'number'
  )
}

/**
  * Validate and create a DoneEvent
  */
function validateDoneEvent(data: unknown): DoneEvent | null {
  // Handle both string data and object data
  const parsedData = parseRecord(data)
  if (!parsedData) return null
  
  const { message_id, chat_id, usage } = parsedData
  
  const normalizedMessageId = normalizeMessageId(message_id)
  if (!normalizedMessageId) return null
  if (typeof chat_id !== 'string' || !chat_id) return null
  
  const eventData: DoneEvent['data'] = { message_id: normalizedMessageId, chat_id }
  if (usage !== undefined && isUsageMetadata(usage)) {
    eventData.usage = usage
  }

  return { event: 'done', data: eventData }
}

/**
  * Validate and create an ErrorEvent
  */
function validateErrorEvent(data: unknown): ErrorEvent | null {
  // Handle both string data and object data
  if (typeof data === 'string') {
    if (!data.trim()) return null
    return {
      event: 'error',
      data: { error: data }
    }
  }
  
  const parsedData = parseRecord(data)
  if (!parsedData) return null
  
  const { error, code, message_id } = parsedData
  
  if (typeof error !== 'string' || !error) return null
  if (code !== undefined && typeof code !== 'string') return null
  if (message_id !== undefined && normalizeMessageId(message_id) === null) return null
  
  const eventData: ErrorEvent['data'] = { error }
  if (typeof code === 'string') eventData.code = code
  if (message_id !== undefined) {
    const normalizedMessageId = normalizeMessageId(message_id)
    if (normalizedMessageId) eventData.message_id = normalizedMessageId
  }
  
  return { event: 'error', data: eventData }
}

/**
 * Create a chat stream parser instance with state management
 */
export function createChatStreamParser() {
  let buffer = ''
  
  return {
    /**
     * Parse a chunk and return events
     * @param chunk - Text chunk from the stream
     * @returns Array of parsed events
     */
    parse(chunk: string): ChatStreamEvent[] {
      const result = parseSSEFrame(chunk, buffer)
      buffer = result.buffer
      return result.events
    },
    
    /**
     * Reset the parser state (for new streams)
     */
    reset(): void {
      buffer = ''
    },
    
    /**
     * Get current buffer state (for testing/debugging)
     */
    getBuffer(): string {
      return buffer
    }
  }
}
