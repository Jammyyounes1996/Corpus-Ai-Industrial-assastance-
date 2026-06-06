import { useMemo } from 'react'
import { BackendStatus, getStatusDetails } from '../../types/status'
import { InlineError } from '../ui/InlineError'
import './ConnectionStatusMenu.css'

interface ConnectionStatusMenuProps {
  status: BackendStatus
  open: boolean
  onRefresh: () => void
}

export function ConnectionStatusMenu({ status, open, onRefresh }: ConnectionStatusMenuProps) {
  const details = useMemo(() => {
    if (status.connection === 'disconnected') {
      return {
        version: 'Unavailable',
        database: 'Unavailable',
        qdrant: 'Unavailable',
        ollama: 'Unavailable',
        model: 'Unavailable',
        provider: 'Unavailable',
        rag: 'Unavailable',
        ocr: 'Unavailable',
        gpu: 'Unavailable'
      }
    }

    return getStatusDetails(status.health)
  }, [status.connection, status.health])

  if (!open) {
    return null
  }

  return (
    <div className="status-menu" role="dialog" aria-label="Backend status details">
      <div className="status-menu__header">
        <h2 className="status-menu__title">System Status</h2>
        <button type="button" className="status-menu__refresh" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      {status.error ? (
        <InlineError
          message={status.error}
          onRetry={onRefresh}
          retryLabel="Retry status check"
        />
      ) : null}

      <dl className="status-menu__grid">
        <div><dt>Backend</dt><dd>{status.connection === 'connected' ? 'Connected' : status.connection === 'degraded' ? 'Degraded' : status.connection === 'loading' ? 'Loading...' : 'Disconnected'}</dd></div>
        <div><dt>Version</dt><dd>{details.version}</dd></div>
        <div><dt>Database</dt><dd>{details.database}</dd></div>
        <div><dt>Qdrant</dt><dd>{details.qdrant}</dd></div>
        <div><dt>Ollama</dt><dd>{details.ollama}</dd></div>
        <div><dt>Model</dt><dd>{details.model}</dd></div>
        <div><dt>Provider</dt><dd>{details.provider}</dd></div>
        <div><dt>RAG</dt><dd>{details.rag}</dd></div>
        <div><dt>OCR</dt><dd>{details.ocr}</dd></div>
        <div><dt>GPU</dt><dd>{details.gpu}</dd></div>
      </dl>

      <p className="status-menu__hint">
        Last check: {status.lastUpdated.toLocaleTimeString()}
      </p>
    </div>
  )
}
