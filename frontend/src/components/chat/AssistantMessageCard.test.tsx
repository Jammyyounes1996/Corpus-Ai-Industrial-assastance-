import { describe, it, expect } from 'vitest'
import { AssistantMessageCard } from './AssistantMessageCard'
import type { Message } from '../../types/chat'
import { renderComponent } from '../../test/domTestUtils'

describe('AssistantMessageCard', () => {
  it('shows partial text with cursor while streaming and error state keeps text', () => {
    const base: Message = {
      id: 'm1',
      role: 'assistant',
      content: 'Partial response',
      timestamp: new Date(),
      status: 'streaming'
    }
    const { container, rerender } = renderComponent(<AssistantMessageCard message={base} />)
    expect(container.textContent).toContain('Partial response')
    expect(container.querySelector('.assistant-msg__cursor')).toBeTruthy()

    rerender(<AssistantMessageCard message={{ ...base, status: 'failed', error: 'stream failed' }} />)
    expect(container.textContent).toContain('Partial response')
    expect(container.textContent).toContain('stream failed')
  })
})
