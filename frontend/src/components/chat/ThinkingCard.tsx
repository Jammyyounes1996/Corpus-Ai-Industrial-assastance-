import { useState, useEffect, useCallback, useRef } from 'react'
import { ChevronDown, ChevronRight, Brain } from 'lucide-react'
import './ThinkingCard.css'

interface ThinkingCardProps {
  content: string
  elapsedMs?: number
  isStreaming?: boolean
}

function formatElapsedLabel(elapsedMs?: number): string {
  if (!elapsedMs || elapsedMs < 1000) return 'Thought for <1 second'
  const seconds = elapsedMs / 1000
  return `Thought for ${seconds.toFixed(seconds >= 10 ? 0 : 1)} seconds`
}

export function ThinkingCard({ content, elapsedMs, isStreaming = false }: ThinkingCardProps) {
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
    if (!isStreaming && content.trim()) {
      const timer = setTimeout(() => {
        setIsExpanded(false)
      }, 2000)
      autoCollapseTimerRef.current = timer
      return () => clearTimeout(timer)
    }
  }, [content, isStreaming])

  const toggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev)
  }, [])

  if (!isStreaming && !content.trim()) return null

  return (
    <div className={`thinking-card ${isExpanded ? 'thinking-card--expanded' : 'thinking-card--collapsed'}`}>
      <button
        className="thinking-card__header"
        onClick={toggleExpand}
        aria-expanded={isExpanded}
        aria-label={isStreaming ? 'Thinking in progress' : formatElapsedLabel(elapsedMs)}
      >
        <Brain size={16} className="thinking-card__header-icon" />
        <span className="thinking-card__title">
          {isStreaming ? 'Thinking...' : formatElapsedLabel(elapsedMs)}
        </span>
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {isExpanded && (
        <div className="thinking-card__steps">
          <div className="thinking-step thinking-step--received">
            <div className="thinking-step__content">{content || 'Thinking...'}</div>
          </div>
        </div>
      )}
    </div>
  )
}
