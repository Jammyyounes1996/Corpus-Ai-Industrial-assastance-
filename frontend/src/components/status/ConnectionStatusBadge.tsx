import { ConnectionStatus, StatusDisplay } from '../../types/status'
import './ConnectionStatusBadge.css'

interface ConnectionStatusBadgeProps {
  status: ConnectionStatus
  onClick?: () => void
  ariaExpanded?: boolean
  ariaHasPopup?: 'menu' | 'dialog' | true
}

export function ConnectionStatusBadge({
  status,
  onClick,
  ariaExpanded,
  ariaHasPopup
}: ConnectionStatusBadgeProps) {
  const display = StatusDisplay[status]
  const isInteractive = typeof onClick === 'function'

  const badge = (
    <span className={`status-badge status-badge--${status}`}>
      <span className={`status-badge__dot status-badge__dot--${status}`} />
      <span className="status-badge__label">{display.text}</span>
    </span>
  )

  if (isInteractive) {
    return (
      <button
        type="button"
        className="status-badge__trigger"
        onClick={onClick}
        aria-expanded={ariaExpanded}
        aria-haspopup={ariaHasPopup}
        aria-label={`Backend status: ${display.text}. Click for details.`}
      >
        {badge}
      </button>
    )
  }

  return (
    <div
      className="status-badge__trigger"
      role="status"
      aria-label={`Backend status: ${display.text}`}
    >
      {badge}
    </div>
  )
}
