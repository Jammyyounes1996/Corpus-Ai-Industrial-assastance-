import { describe, it, expect, vi } from 'vitest'
import { WorkspaceTabs } from './WorkspaceTabs'
import { renderComponent, click } from '../../test/domTestUtils'

describe('WorkspaceTabs', () => {
  it('changes active tab via click', () => {
    const onTabChange = vi.fn()
    const { container } = renderComponent(<WorkspaceTabs activeTab="chat" onTabChange={onTabChange} />)
    const docsButton = Array.from(container.querySelectorAll('button')).find((btn) => btn.textContent?.includes('Documents'))
    click(docsButton || null)
    expect(onTabChange).toHaveBeenCalledWith('documents')
  })
})
