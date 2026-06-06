import { describe, it, expect } from 'vitest'
import { MarkdownRenderer } from './MarkdownRenderer'
import { renderComponent } from '../../test/domTestUtils'

describe('MarkdownRenderer', () => {
  it('renders headings, bold, lists, tables, and inline code', () => {
    const content = '# H\n**B**\n- a\n\n|A|B|\n|-|-|\n|1|2|\n`x`'
    const { container } = renderComponent(<MarkdownRenderer content={content} />)
    expect(container.querySelector('h1')?.textContent).toBe('H')
    expect(container.querySelector('strong')?.textContent).toBe('B')
    expect(container.querySelectorAll('li').length).toBeGreaterThan(0)
    expect(container.querySelector('table')).toBeTruthy()
    expect(container.querySelector('.md-renderer__inline-code')?.textContent).toBe('x')
  })

  it('does not render unsafe raw HTML', () => {
    const { container } = renderComponent(<MarkdownRenderer content={'<script>alert(1)</script><p>ok</p>'} />)
    expect(container.querySelector('script')).toBeNull()
    expect(container.textContent).toContain('ok')
  })
})
