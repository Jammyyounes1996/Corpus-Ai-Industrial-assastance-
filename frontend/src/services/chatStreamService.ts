/* Chat Stream Service */
/*
  T046 streaming service: POST to an existing chat stream endpoint,
  decode the readable stream, and delegate SSE parsing to chatStreamParser.
*/

import { config } from '../config'
import { createChatStreamParser } from './chatStreamParser'
import type { StreamRequestBody, CreateChatResponse } from '../types/api'
import type { ChatStreamEvent } from '../types/chat'
import { createFrontendError, normalizeError } from '../types/errors'

export interface StreamChatOptions {
  signal?: AbortSignal
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: string) => void
}

/**
 * Stream chat responses from the backend.
 */
export async function streamChat(
  chatId: string,
  request: StreamRequestBody,
  onEvent: (event: ChatStreamEvent) => void,
  options: StreamChatOptions = {}
): Promise<void> {
  if (!chatId.trim()) {
    throw createFrontendError('validation', 'Chat ID is required for streaming', 'INVALID_CHAT_ID')
  }

  const endpoint = config.chatEndpoints.streamChat.replace(':chatId', encodeURIComponent(chatId))
  const url = `${config.backendBaseUrl}${endpoint}`
  const parser = createChatStreamParser()

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query: request.query,
        attached_files: request.attached_files,
        model: request.model,
        provider: request.provider,
        answer_mode: request.answer_mode
      }),
      signal: options.signal
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw createFrontendError(
        'backend',
        `Stream request failed: ${response.status} ${response.statusText}${errorText ? ` - ${errorText}` : ''}`,
        'STREAM_REQUEST_FAILED',
        { status: response.status }
      )
    }

    if (!response.body) {
      throw createFrontendError('network', 'No readable stream found', 'STREAM_BODY_MISSING')
    }

    options.onOpen?.()

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let streamComplete = false

    try {
      while (!streamComplete) {
        const { done, value } = await reader.read()

        if (done) {
          streamComplete = true
          continue
        }

        const chunk = decoder.decode(value, { stream: true })
        emitParsedEvents(chunk, parser, onEvent)
      }

      const finalChunk = decoder.decode()
      if (finalChunk) {
        emitParsedEvents(finalChunk, parser, onEvent)
      }
    } finally {
      reader.releaseLock()
    }

    options.onClose?.()
  } catch (error) {
    if (isAbortError(error)) {
      options.onClose?.()
      return
    }

    const normalizedError = normalizeError(error)
    options.onError?.(normalizedError.message)
    throw normalizedError
  }
}

function emitParsedEvents(
  chunk: string,
  parser: ReturnType<typeof createChatStreamParser>,
  onEvent: (event: ChatStreamEvent) => void
): void {
  const events = parser.parse(chunk)
  for (const event of events) {
    onEvent(event)
  }
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export async function createBackendChat(request: StreamRequestBody): Promise<CreateChatResponse> {
  const url = `${config.backendBaseUrl}${config.chatEndpoints.createChat}`

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: request.query,
      attached_files: request.attached_files,
      model: request.model,
      provider: request.provider,
      answer_mode: request.answer_mode
    })
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw createFrontendError(
      'backend',
      `Failed to create chat: ${response.status} ${response.statusText}${errorText ? ` - ${errorText}` : ''}`,
      'CHAT_CREATE_FAILED',
      { status: response.status }
    )
  }

  return response.json()
}
