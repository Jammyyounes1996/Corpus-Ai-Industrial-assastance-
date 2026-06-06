import { AlertCircle, RotateCcw, X } from 'lucide-react'
import './InlineError.css'

interface InlineErrorProps {
  message: string
  onRetry?: () => void
  onDismiss?: () => void
  retryLabel?: string
  dismissLabel?: string
}

function toSafeMessage(message: string): string {
  const text = message.trim()
  if (!text) {
    return 'Something went wrong. Please try again.'
  }

  const lower = text.toLowerCase()
  if (
    lower.includes('traceback') ||
    lower.includes('exception:') ||
    lower.includes(' at ') ||
    lower.includes('stack')
  ) {
    return 'Request failed. Please try again.'
  }

  return text.length > 220 ? `${text.slice(0, 220)}...` : text
}

export function InlineError({
  message,
  onRetry,
  onDismiss,
  retryLabel = 'Retry',
  dismissLabel = 'Dismiss error'
}: InlineErrorProps) {
  const safeMessage = toSafeMessage(message)

  return (
    <div className="inline-error" role="alert" aria-live="assertive">
      <div className="inline-error__content">
        <AlertCircle size={16} aria-hidden="true" />
        <span>{safeMessage}</span>
      </div>
      <div className="inline-error__actions">
        {onRetry ? (
          <button type="button" className="inline-error__btn" onClick={onRetry}>
            <RotateCcw size={14} aria-hidden="true" />
            <span>{retryLabel}</span>
          </button>
        ) : null}
        {onDismiss ? (
          <button
            type="button"
            className="inline-error__btn inline-error__btn--ghost"
            onClick={onDismiss}
            aria-label={dismissLabel}
          >
            <X size={14} aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </div>
  )
}
