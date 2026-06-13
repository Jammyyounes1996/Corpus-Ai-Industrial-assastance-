import { describe, it, expect, vi } from 'vitest'
import { ThinkingCard } from './ThinkingCard'
import { renderComponent } from '../../test/domTestUtils'

describe('ThinkingCard', () => {
  it('renders thinking steps and auto-collapses when complete', () => {
    vi.useFakeTimers()
    const { container } = renderComponent(
      <ThinkingCard
        isStreaming={false}
        content="step"
        elapsedMs={1200}
      />
    )
    expect(container.textContent).toContain('Thought for')
    vi.advanceTimersByTime(2100)
    const header = container.querySelector('.thinking-card__header')
    expect(header?.getAttribute('aria-expanded')).toBe('false')
    vi.useRealTimers()
  })
})
