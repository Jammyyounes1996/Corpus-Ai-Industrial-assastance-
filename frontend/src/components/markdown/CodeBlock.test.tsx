import { describe, it, expect, vi } from 'vitest'
import { CodeBlock } from './CodeBlock'
import { renderComponent, click } from '../../test/domTestUtils'

describe('CodeBlock', () => {
  it('copies code successfully', async () => {
    const writeText = vi.fn(async () => undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true
    })
    const { container } = renderComponent(<CodeBlock language="ts">const x = 1;</CodeBlock>)
    const button = container.querySelector('.code-block__copy-btn')
    click(button)
    expect(writeText).toHaveBeenCalledWith('const x = 1;')
  })

  it('handles copy failure without crashing', async () => {
    const writeText = vi.fn(async () => {
      throw new Error('denied')
    })
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true
    })
    const { container } = renderComponent(<CodeBlock language="ts">const y = 2;</CodeBlock>)
    click(container.querySelector('.code-block__copy-btn'))
    expect(container.textContent).toContain('Copy')
  })
})
