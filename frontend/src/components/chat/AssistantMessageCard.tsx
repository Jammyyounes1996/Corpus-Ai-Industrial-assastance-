import { LogoMark } from '../ui/LogoMark'
import { AlertCircle } from 'lucide-react'
import { ThinkingCard } from './ThinkingCard'
import { AssistantActions } from './AssistantActions'
import { SourceChips } from './SourceChips'
import { MarkdownRenderer } from '../markdown/MarkdownRenderer'
import type { Message } from '../../types/chat'
import { formatTimestamp } from '../../services/timeService'
import './AssistantMessageCard.css'

interface AssistantMessageCardProps {
  message: Message
}

export function AssistantMessageCard({ message }: AssistantMessageCardProps) {
  const isStreamActive = message.status === 'streaming'
  const isFailed = message.status === 'failed'
  const isCancelled = message.status === 'cancelled'
  const isComplete = message.status === 'complete'

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
        <span className="assistant-msg__role">Assistant</span>
        <time className="assistant-msg__time" dateTime={message.timestamp.toISOString()}>
          {formatTimestamp(message.timestamp)}
        </time>
      </div>

      {message.thinkingSteps && message.thinkingSteps.length > 0 && (
        <ThinkingCard steps={message.thinkingSteps} isStreaming={isStreamActive} />
      )}

      <div className={`assistant-msg__content${isStreamActive ? ' assistant-msg__content--streaming' : ''}`}>
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
          <AssistantActions content={message.content} />
        </div>
      )}
    </div>
  )
}
