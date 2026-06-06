import { describe, it, expect, vi } from 'vitest'
import { ConnectionStatusMenu } from './ConnectionStatusMenu'
import { renderComponent } from '../../test/domTestUtils'
import type { BackendStatus } from '../../types/status'

const baseStatus: BackendStatus = {
  connection: 'connected',
  health: {
    status: 'ok',
    version: '1.0',
    database: 'ok',
    qdrant: 'ok',
    ollama: 'ok'
  },
  lastUpdated: new Date(),
  error: null
}

describe('ConnectionStatusMenu', () => {
  it('renders unknown fallbacks for optional fields', () => {
    const { container } = renderComponent(<ConnectionStatusMenu status={baseStatus} open={true} onRefresh={vi.fn()} />)
    expect(container.textContent).toContain('Unknown')
  })

  it('renders unavailable values when disconnected', () => {
    const disconnected: BackendStatus = { ...baseStatus, connection: 'disconnected', health: null }
    const { container } = renderComponent(<ConnectionStatusMenu status={disconnected} open={true} onRefresh={vi.fn()} />)
    expect(container.textContent).toContain('Unavailable')
  })

  it('shows inline error and retry label when error exists', () => {
    const withError: BackendStatus = { ...baseStatus, error: 'failed to fetch' }
    const { container } = renderComponent(<ConnectionStatusMenu status={withError} open={true} onRefresh={vi.fn()} />)
    expect(container.textContent).toContain('failed to fetch')
    expect(container.textContent).toContain('Retry status check')
  })
})
