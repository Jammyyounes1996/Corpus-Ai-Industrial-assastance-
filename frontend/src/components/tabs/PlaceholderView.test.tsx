import { describe, it, expect } from 'vitest'
import { PlaceholderView } from './PlaceholderView'
import { renderComponent } from '../../test/domTestUtils'

describe('PlaceholderView', () => {
  it('renders placeholder copy for non-chat tabs', () => {
    const { container } = renderComponent(
      <PlaceholderView icon="FileText" title="Documents" description="Upload and manage docs" badge="Coming soon" />
    )
    expect(container.textContent).toContain('Documents')
    expect(container.textContent).toContain('Coming soon')
  })
})
