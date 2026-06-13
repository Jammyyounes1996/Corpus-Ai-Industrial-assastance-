import { useCallback, useState } from 'react'
import { Copy, RotateCcw, Maximize2, Minimize2, Download, ThumbsUp, ThumbsDown } from 'lucide-react'
import './AssistantMessageCard.css'

interface AssistantActionsProps {
  content: string
  expanded?: boolean
  onCopy?: () => void
  onRegenerate?: () => void
  onToggleExpand?: () => void
}

type Feedback = 'up' | 'down' | null

export function AssistantActions({
  content,
  expanded = false,
  onCopy,
  onRegenerate,
  onToggleExpand,
}: AssistantActionsProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      onCopy?.()
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }, [content, onCopy])

  const handleExport = useCallback(() => {
    const stamp = new Date().toISOString().slice(0, 10)
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `corpus-answer-${stamp}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [content])

  const toggleFeedback = useCallback((value: Feedback) => {
    setFeedback((prev) => (prev === value ? null : value))
  }, [])

  return (
    <div className="assistant-actions" role="toolbar" aria-label="Message actions">
      <button
        className="assistant-actions__btn"
        onClick={handleCopy}
        aria-label={copied ? 'Copied' : 'Copy to clipboard'}
        title={copied ? 'Copied' : 'Copy'}
      >
        <Copy size={14} />
        <span className="assistant-actions__label">{copied ? 'Copied' : 'Copy'}</span>
      </button>

      <button
        className="assistant-actions__btn"
        onClick={onRegenerate}
        disabled={!onRegenerate}
        aria-label="Regenerate response"
        title="Regenerate"
      >
        <RotateCcw size={14} />
        <span className="assistant-actions__label">Regenerate</span>
      </button>

      <button
        className="assistant-actions__btn"
        onClick={onToggleExpand}
        aria-label={expanded ? 'Collapse response' : 'Expand response'}
        title={expanded ? 'Collapse' : 'Expand'}
      >
        {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        <span className="assistant-actions__label">{expanded ? 'Collapse' : 'Expand'}</span>
      </button>

      <button
        className="assistant-actions__btn"
        onClick={handleExport}
        aria-label="Export response"
        title="Export as Markdown"
      >
        <Download size={14} />
        <span className="assistant-actions__label">Export</span>
      </button>

      <button
        className={`assistant-actions__btn ${feedback === 'up' ? 'assistant-actions__btn--active' : ''}`}
        onClick={() => toggleFeedback('up')}
        aria-pressed={feedback === 'up'}
        aria-label="Like response"
        title="Like"
      >
        <ThumbsUp size={14} />
      </button>

      <button
        className={`assistant-actions__btn ${feedback === 'down' ? 'assistant-actions__btn--active' : ''}`}
        onClick={() => toggleFeedback('down')}
        aria-pressed={feedback === 'down'}
        aria-label="Dislike response"
        title="Dislike"
      >
        <ThumbsDown size={14} />
      </button>
    </div>
  )
}
