import { useCallback, useState } from 'react'
import { Copy, RotateCcw, Maximize2, Download, ThumbsUp, ThumbsDown } from 'lucide-react'
import './AssistantMessageCard.css'

interface AssistantActionsProps {
  content: string
  onCopy?: () => void
  onRegenerate?: () => void
  onExpand?: () => void
  onExport?: () => void
  onLike?: () => void
  onDislike?: () => void
}

export function AssistantActions({
  content,
  onCopy,
  onRegenerate,
  onExpand,
  onExport,
  onLike,
  onDislike,
}: AssistantActionsProps) {
  const [copied, setCopied] = useState(false)

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
        aria-label="Regenerate response"
        title="Regenerate"
      >
        <RotateCcw size={14} />
        <span className="assistant-actions__label">Regenerate</span>
      </button>

      <button
        className="assistant-actions__btn"
        onClick={onExpand}
        aria-label="Expand response"
        title="Expand"
      >
        <Maximize2 size={14} />
        <span className="assistant-actions__label">Expand</span>
      </button>

      <button
        className="assistant-actions__btn"
        onClick={onExport}
        aria-label="Export response"
        title="Export"
      >
        <Download size={14} />
        <span className="assistant-actions__label">Export</span>
      </button>

      <button
        className="assistant-actions__btn"
        onClick={onLike}
        aria-label="Like response"
        title="Like"
      >
        <ThumbsUp size={14} />
      </button>

      <button
        className="assistant-actions__btn"
        onClick={onDislike}
        aria-label="Dislike response"
        title="Dislike"
      >
        <ThumbsDown size={14} />
      </button>
    </div>
  )
}
