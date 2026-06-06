import { useEffect, useRef, useCallback } from 'react'
import type { Message } from '../../types/chat'
import { UserMessageCard } from './UserMessageCard'
import { AssistantMessageCard } from './AssistantMessageCard'
import './MessageList.css'

interface MessageListProps {
  messages: Message[]
  isStreaming?: boolean
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const isUserScrollingRef = useRef(false)
  const lastScrollTopRef = useRef(0)

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    isUserScrollingRef.current = distanceFromBottom > 60
    lastScrollTopRef.current = el.scrollTop
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    if (!isUserScrollingRef.current) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages, isStreaming])

  return (
    <div
      className="message-list"
      ref={scrollRef}
      onScroll={handleScroll}
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      {messages.map((msg) => {
        if (msg.role === 'user') {
          return <UserMessageCard key={msg.id} message={msg} />
        }
        return (
          <AssistantMessageCard
            key={msg.id}
            message={msg}
          />
        )
      })}
    </div>
  )
}
