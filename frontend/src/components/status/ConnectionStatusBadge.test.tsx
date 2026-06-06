import { describe, it, expect } from 'vitest'
import { ConnectionStatusBadge } from './ConnectionStatusBadge'
import { renderComponent } from '../../test/domTestUtils'

describe('ConnectionStatusBadge', () => {
  it('renders all states labels', () => {
    const statuses = ['loading', 'connected', 'degraded', 'disconnected'] as const
    for (const status of statuses) {
      const { container, unmount } = renderComponent(<ConnectionStatusBadge status={status} />)
      expect(container.textContent?.length).toBeGreaterThan(0)
      unmount()
    }
  })
})
