import { useState } from 'react'
import { LogoMark } from '../ui/LogoMark'
import { AlertCircle } from 'lucide-react'
import { ThinkingCard } from './ThinkingCard'
import { AssistantActions } from './AssistantActions'
import { SourceChips } from './SourceChips'
import { MarkdownRenderer } from '../markdown/MarkdownRenderer'
import type { Message } from '../../types/chat'
import { formatTimestamp } from '../../services/timeService'
import { getTextDirection } from '../../utils/textDirection'
import './AssistantMessageCard.css'

interface AssistantMessageCardProps {
  message: Message
  onRegenerate?: () => void
}

export function AssistantMessageCard({ message, onRegenerate }: AssistantMessageCardProps) {
  const isStreamActive = message.status === 'streaming'
  const isFailed = message.status === 'failed'
  const isCancelled = message.status === 'cancelled'
  const isComplete = message.status === 'complete'
  const [expanded, setExpanded] = useState(false)

  const dir = getTextDirection(message.content)

  return (
    <div
      className={`assistant-msg ${isFailed ? 'assistant-msg--failed' : ''} ${isCancelled ? 'assistant-msg--cancelled' : ''}`}
      role="article"
      aria-label={`Assistant message at ${formatTimestamp(message.timestamp)}`}
    >
      <div className="assistant-msg__header">
        <div className="assistant-msg__avatar" aria-hidden="true">
          <LogoMark />
        </div>
        <span className="assistant-msg__role">CORPUS INDUSTRIAL AI AGENT</span>
        <time className="assistant-msg__time" dateTime={message.timestamp.toISOString()}>
          {formatTimestamp(message.timestamp)}
        </time>
      </div>

      {(isStreamActive || message.thinkingText) && (
        <ThinkingCard
          content={message.thinkingText ?? ''}
          elapsedMs={message.thinkingElapsedMs}
          isStreaming={isStreamActive}
        />
      )}

      <div
        className={`assistant-msg__content assistant-msg__content--${dir}${
          isStreamActive ? ' assistant-msg__content--streaming' : ''
        }${expanded ? ' assistant-msg__content--expanded' : ''}`}
        dir={dir}
      >
        {isStreamActive ? (
          <>
            {message.content}
            <span className="assistant-msg__cursor" aria-hidden="true" />
          </>
        ) : (
          <MarkdownRenderer content={message.content} />
        )}
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="assistant-msg__sources">
          <SourceChips sources={message.sources} />
        </div>
      )}

      {isFailed && message.error && (
        <div className="assistant-msg__error" role="alert">
          <AlertCircle size={14} />
          <span>{message.error}</span>
        </div>
      )}

      {isCancelled && (
        <div className="assistant-msg__cancelled" role="status">
          Response cancelled
        </div>
      )}

      {isComplete && message.content.trim() && (
        <div className="assistant-msg__actions-wrapper">
          <AssistantActions
            content={message.content}
            expanded={expanded}
            onRegenerate={onRegenerate}
            onToggleExpand={() => setExpanded((v) => !v)}
          />
        </div>
      )}
    </div>
  )
}
