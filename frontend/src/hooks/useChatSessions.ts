/* Chat Sessions Hook */
/*
  Local chat session state management
  Handles session creation, selection, updates without backend calls
*/

import { useState, useCallback, useRef } from 'react'
import { ChatSession, ChatStreamEvent, Message, ThinkingStep, SourceReference } from '../types/chat'
import { AttachedFile } from '../types/attachments'
import { generateChatTitle } from '../services/timeService'

export interface UseChatSessionsReturn {
  sessions: ChatSession[]
  activeSessionId: string | null
  loading: boolean
  createNewSession: () => ChatSession
  setActiveSession: (sessionId: string) => void
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void
  deleteSession: (sessionId: string) => void
  searchQuery: string
  setSearchQuery: (query: string) => void
  debouncedSetSearchQuery: (query: string) => void
  filteredSessions: ChatSession[]
  appendUserMessage: (sessionId: string, content: string, attachments?: AttachedFile[]) => void
  createAssistantPlaceholder: (sessionId: string, content: string) => string
  appendToken: (sessionId: string, token: string) => void
  setSources: (sessionId: string, messageId: string, sources: SourceReference[]) => void
  setThinkingSteps: (sessionId: string, messageId: string, steps: ThinkingStep[]) => void
  completeMessage: (sessionId: string, messageId: string) => void
  failMessage: (sessionId: string, messageId: string, error?: string) => void
  cancelMessage: (sessionId: string, messageId: string) => void
  createStreamEventHandler: (sessionId: string) => (event: ChatStreamEvent) => void
  cancelStreamingMessage: (sessionId: string) => void
}

const MAX_SESSIONS = 100

export function useChatSessions(): UseChatSessionsReturn {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [searchQuery, setSearchQueryState] = useState('')
  const searchTimeoutRef = useRef<NodeJS.Timeout>()
  const streamingMessageIdRef = useRef<string | null>(null)

  // Create a new chat session
  const createNewSession = useCallback((): ChatSession => {
    const sessionId = `session-${Date.now()}`
    const newSession: ChatSession = {
      id: sessionId,
      title: 'New chat',
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true,
      messages: []
    }

    setSessions(prev => {
      const updated = [newSession, ...prev].slice(0, MAX_SESSIONS)
      return updated
    })

    setActiveSessionId(sessionId)
    return newSession
  }, [])

  // Set active session
  const setActiveSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId)
    setSessions(prev => 
      prev.map(session => ({
        ...session,
        isActive: session.id === sessionId
      }))
    )
  }, [])

  // Update session
  const updateSession = useCallback((sessionId: string, updates: Partial<ChatSession>) => {
    setSessions(prev => 
      prev.map(session => 
        session.id === sessionId 
          ? { ...session, ...updates, updatedAt: new Date() }
          : session
      )
    )
  }, [])

  // Delete session
  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => {
      const updated = prev.filter(session => session.id !== sessionId)
      if (activeSessionId === sessionId && updated.length > 0) {
        setActiveSessionId(updated[0].id)
      } else if (updated.length === 0) {
        setActiveSessionId(null)
      }
      return updated
    })
  }, [activeSessionId, setActiveSessionId])

  // Debounced search
  const setSearchQuery = useCallback((query: string) => {
    setSearchQueryState(query)
  }, [])

  const debouncedSetSearchQuery = useCallback((query: string) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
    
    searchTimeoutRef.current = setTimeout(() => {
      setSearchQueryState(query)
    }, 200)
  }, [])

  // Filter sessions based on search query
  const filteredSessions = sessions.filter(session => {
    if (!searchQuery.trim()) return true
    const query = searchQuery.toLowerCase().trim()
    return (
      session.title.toLowerCase().includes(query) ||
      session.messages.some(msg => 
        msg.content.toLowerCase().includes(query)
      )
    )
  })

  // Message mutations
  const appendUserMessage = useCallback((sessionId: string, content: string, attachments?: AttachedFile[]) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const userMessage: Message = {
          id: `msg-${Date.now()}-user`,
          role: 'user',
          content,
          timestamp: new Date(),
          status: 'complete',
          attachments
        }

        const updatedSession = {
          ...session,
          messages: [...session.messages, userMessage],
          updatedAt: new Date()
        }

        // Auto-generate title if this is the first message
        if (session.messages.length === 0) {
          updatedSession.title = generateChatTitle(content)
        }

        return updatedSession
      })
    )
  }, [])

  const createAssistantPlaceholder = useCallback((sessionId: string, content: string): string => {
    const messageId = `msg-${Date.now()}-assistant`
    streamingMessageIdRef.current = messageId

    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const assistantMessage: Message = {
          id: messageId,
          role: 'assistant',
          content,
          timestamp: new Date(),
          status: 'streaming'
        }

        return {
          ...session,
          messages: [...session.messages, assistantMessage],
          updatedAt: new Date()
        }
      })
    )

    return messageId
  }, [])

  const appendToken = useCallback((sessionId: string, token: string) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const lastMessage = session.messages[session.messages.length - 1]
        if (!lastMessage || lastMessage.role !== 'assistant' || lastMessage.status !== 'streaming') {
          return session
        }

        const updatedMessage = {
          ...lastMessage,
          content: lastMessage.content + token,
          timestamp: new Date()
        }

        return {
          ...session,
          messages: [...session.messages.slice(0, -1), updatedMessage],
          updatedAt: new Date()
        }
      })
    )
  }, [])

  const setSources = useCallback((sessionId: string, messageId: string, sources: SourceReference[]) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const updatedMessages = session.messages.map(msg => {
          if (msg.id === messageId) {
            return { ...msg, sources }
          }
          return msg
        })

        return {
          ...session,
          messages: updatedMessages,
          updatedAt: new Date()
        }
      })
    )
  }, [])

  const setThinkingSteps = useCallback((sessionId: string, messageId: string, steps: ThinkingStep[]) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const updatedMessages = session.messages.map(msg => {
          if (msg.id === messageId) {
            return { ...msg, thinkingSteps: steps }
          }
          return msg
        })

        return {
          ...session,
          messages: updatedMessages,
          updatedAt: new Date()
        }
      })
    )
  }, [])

  const completeMessage = useCallback((sessionId: string, messageId: string) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const updatedMessages = session.messages.map(msg => 
          msg.id === messageId 
            ? { ...msg, status: 'complete' as const, timestamp: new Date() }
            : msg
        )

        return {
          ...session,
          messages: updatedMessages,
          updatedAt: new Date()
        }
      })
    )
  }, [])

  const failMessage = useCallback((sessionId: string, messageId: string, error?: string) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const updatedMessages = session.messages.map(msg => 
          msg.id === messageId 
            ? { ...msg, status: 'failed' as const, error, timestamp: new Date() }
            : msg
        )

        return {
          ...session,
          messages: updatedMessages,
          updatedAt: new Date()
        }
      })
    )
  }, [])

  const cancelMessage = useCallback((sessionId: string, messageId: string) => {
    setSessions(prev => 
      prev.map(session => {
        if (session.id !== sessionId) return session

        const updatedMessages = session.messages.map(msg => 
          msg.id === messageId 
            ? { ...msg, status: 'cancelled' as const, timestamp: new Date() }
            : msg
        )

        return {
          ...session,
          messages: updatedMessages,
          updatedAt: new Date()
        }
      })
    )
  }, [])

  const createStreamEventHandler = useCallback((sessionId: string) => {
    const accumulatedSteps: ThinkingStep[] = []

    return (event: ChatStreamEvent) => {
      const messageId = streamingMessageIdRef.current

      switch (event.event) {
        case 'token':
          appendToken(sessionId, event.data.token)
          break
        case 'thinking_step': {
          const step: ThinkingStep = {
            id: event.data.step_id,
            type: event.data.type,
            content: event.data.content,
            timestamp: new Date(event.data.timestamp),
            status: 'received'
          }
          accumulatedSteps.push(step)
          if (messageId) {
            setThinkingSteps(sessionId, messageId, [...accumulatedSteps])
          }
          break
        }
        case 'sources':
          if (messageId) {
            setSources(sessionId, messageId, event.data.sources)
          }
          break
        case 'done':
          if (messageId) {
            completeMessage(sessionId, messageId)
          }
          streamingMessageIdRef.current = null
          break
        case 'error':
          if (messageId) {
            failMessage(sessionId, messageId, event.data.error)
          }
          streamingMessageIdRef.current = null
          break
      }
    }
  }, [appendToken, setThinkingSteps, setSources, completeMessage, failMessage])

  const cancelStreamingMessage = useCallback((sessionId: string) => {
    const messageId = streamingMessageIdRef.current
    if (messageId) {
      cancelMessage(sessionId, messageId)
      streamingMessageIdRef.current = null
    }
  }, [cancelMessage])

  return {
    sessions,
    activeSessionId,
    loading: false,
    createNewSession,
    setActiveSession,
    updateSession,
    deleteSession,
    searchQuery,
    setSearchQuery,
    debouncedSetSearchQuery,
    filteredSessions,
    appendUserMessage,
    createAssistantPlaceholder,
    appendToken,
    setSources,
    setThinkingSteps,
    completeMessage,
    failMessage,
    cancelMessage,
    createStreamEventHandler,
    cancelStreamingMessage
  }
}