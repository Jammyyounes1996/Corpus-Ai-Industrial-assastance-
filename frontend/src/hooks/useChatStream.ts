import { useRef, useCallback, useState } from 'react'
import { streamChat, createBackendChat } from '../services/chatStreamService'
import type { ChatStreamEvent } from '../types/chat'
import type { StreamRequestBody } from '../types/api'
import { normalizeError } from '../types/errors'

export interface UseChatStreamOptions {
  onEvent: (event: ChatStreamEvent) => void
  onBackendChatCreated?: (backendChatId: string) => void
  onCancel?: () => void
}

export interface UseChatStreamReturn {
  isStreaming: boolean
  error: string | null
  canRetry: boolean
  send: (backendChatId: string | null, request: StreamRequestBody) => Promise<string | null>
  retryLast: () => Promise<string | null>
  clearError: () => void
  cancel: () => void
}

interface RetryPayload {
  backendChatId: string | null
  request: StreamRequestBody
}

export function useChatStream(options: UseChatStreamOptions): UseChatStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [canRetry, setCanRetry] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const lastRetryPayloadRef = useRef<RetryPayload | null>(null)
  const optionsRef = useRef(options)
  optionsRef.current = options

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
    optionsRef.current.onCancel?.()
  }, [])

  const clearError = useCallback(() => {
    setError(null)
    setCanRetry(false)
  }, [])

  const send = useCallback(async (backendChatId: string | null, request: StreamRequestBody): Promise<string | null> => {
    if (!request.query.trim()) {
      const msg = 'Message cannot be empty'
      setError(msg)
      return null
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller
    setIsStreaming(true)
    setError(null)
    setCanRetry(false)

    lastRetryPayloadRef.current = {
      backendChatId,
      request: {
        ...request,
        attached_files: request.attached_files ? [...request.attached_files] : undefined
      }
    }

    let tokensStarted = false
    const onEvent = (event: ChatStreamEvent) => {
      if (event.event === 'answer_delta') {
        tokensStarted = true
      }
      optionsRef.current.onEvent(event)
    }

    try {
      let chatId = backendChatId

      if (!chatId) {
        const response = await createBackendChat(request)
        chatId = response.id
        optionsRef.current.onBackendChatCreated?.(chatId)
      }

      await streamChat(
        chatId,
        request,
        onEvent,
        {
          signal: controller.signal,
          onError: (msg: string) => {
            setError(msg)
          }
        }
      )

      return chatId
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return null
      }
      const normalized = normalizeError(err)
      setError(normalized.message)
      setCanRetry(!tokensStarted)
      return null
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }, [])

  const retryLast = useCallback(async (): Promise<string | null> => {
    if (!lastRetryPayloadRef.current || !canRetry) {
      return null
    }

    const { backendChatId, request } = lastRetryPayloadRef.current
    return send(backendChatId, request)
  }, [canRetry, send])

  return { isStreaming, error, canRetry, send, retryLast, clearError, cancel }
}
