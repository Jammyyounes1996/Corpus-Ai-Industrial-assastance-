import { describe, it, expect, vi } from 'vitest'
import { ThinkingCard } from './ThinkingCard'
import { renderComponent } from '../../test/domTestUtils'

describe('ThinkingCard', () => {
  it('renders thinking steps and auto-collapses when complete', () => {
    vi.useFakeTimers()
    const { container } = renderComponent(
      <ThinkingCard
        isStreaming={false}
        steps={[{ id: 's1', type: 'reasoning', content: 'step', timestamp: new Date(), status: 'complete' }]}
      />
    )
    expect(container.textContent).toContain('Thinking')
    vi.advanceTimersByTime(2100)
    const header = container.querySelector('.thinking-card__header')
    expect(header?.getAttribute('aria-expanded')).toBe('false')
    vi.useRealTimers()
  })
})
