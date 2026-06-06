import { useState, useEffect, useCallback, useRef } from 'react'
import { ChevronDown, ChevronRight, Brain, Loader, CheckCircle, AlertCircle } from 'lucide-react'
import type { ThinkingStep } from '../../types/chat'
import './ThinkingCard.css'

interface ThinkingCardProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
}

function StepIcon({ status }: { status: ThinkingStep['status'] }) {
  switch (status) {
    case 'received':
      return <Loader size={14} className="thinking-step__icon thinking-step__icon--loading" />
    case 'complete':
      return <CheckCircle size={14} className="thinking-step__icon thinking-step__icon--complete" />
    case 'failed':
      return <AlertCircle size={14} className="thinking-step__icon thinking-step__icon--failed" />
    default:
      return null
  }
}

function formatStepTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export function ThinkingCard({ steps, isStreaming = false }: ThinkingCardProps) {
  const [isExpanded, setIsExpanded] = useState(isStreaming)
  const autoCollapseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (isStreaming) {
      setIsExpanded(true)
      if (autoCollapseTimerRef.current) {
        clearTimeout(autoCollapseTimerRef.current)
        autoCollapseTimerRef.current = null
      }
    }
  }, [isStreaming])

  useEffect(() => {
    if (!isStreaming && steps.length > 0) {
      const hasFailed = steps.some((s) => s.status === 'failed')
      if (!hasFailed) {
        const timer = setTimeout(() => {
          setIsExpanded(false)
        }, 2000)
        autoCollapseTimerRef.current = timer
        return () => clearTimeout(timer)
      }
    }
  }, [isStreaming, steps])

  const toggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev)
  }, [])

  if (steps.length === 0) return null

  const completedCount = steps.filter((s) => s.status === 'complete').length
  const failedCount = steps.filter((s) => s.status === 'failed').length

  return (
    <div className={`thinking-card ${isExpanded ? 'thinking-card--expanded' : 'thinking-card--collapsed'}`}>
      <button
        className="thinking-card__header"
        onClick={toggleExpand}
        aria-expanded={isExpanded}
        aria-label={`Thinking steps: ${completedCount} of ${steps.length} complete${failedCount > 0 ? `, ${failedCount} failed` : ''}`}
      >
        <Brain size={16} className="thinking-card__header-icon" />
        <span className="thinking-card__title">
          Thinking
          {isStreaming && <span className="thinking-card__badge thinking-card__badge--streaming">active</span>}
        </span>
        <span className="thinking-card__count">
          {completedCount}/{steps.length}
        </span>
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {isExpanded && (
        <ol className="thinking-card__steps" role="list">
          {steps.map((step, index) => (
            <li
              key={step.id || index}
              className={`thinking-step thinking-step--${step.status}`}
            >
              <div className="thinking-step__header">
                <StepIcon status={step.status} />
                <span className="thinking-step__type">{step.type}</span>
                <span className="thinking-step__time">{formatStepTime(step.timestamp)}</span>
              </div>
              <div className="thinking-step__content">{step.content}</div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
