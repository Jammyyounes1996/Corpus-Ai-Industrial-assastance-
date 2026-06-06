import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { InputBar } from './InputBar'
import { renderComponent, changeInput, keydown, click } from '../../test/domTestUtils'

function renderInputBar(props: Partial<React.ComponentProps<typeof InputBar>> = {}) {
  const onSend = vi.fn()
  const defaults: React.ComponentProps<typeof InputBar> = {
    onSend,
    onAttachFiles: vi.fn(),
    onRemoveAttachment: vi.fn(),
    onRetryAttachment: vi.fn(),
    validateAttachmentFiles: () => [],
    canAddMoreFiles: true,
    attachments: [],
    failedAttachments: []
  }
  const result = renderComponent(<InputBar {...defaults} {...props} />)
  return { ...result, onSend }
}

describe('InputBar', () => {
  it('keeps send disabled for empty input', () => {
    const { container, onSend } = renderInputBar()
    const send = container.querySelector('[aria-label="Send message"]') as HTMLButtonElement
    expect(send.disabled).toBe(true)
    click(send)
    expect(onSend).not.toHaveBeenCalled()
  })

  it('sends on Enter and keeps Shift+Enter as newline', () => {
    const { container, onSend } = renderInputBar()
    const textarea = container.querySelector('textarea') as HTMLTextAreaElement
    changeInput(textarea, 'hello')
    keydown(textarea, 'Enter')
    expect(onSend).toHaveBeenCalledWith('hello')

    changeInput(textarea, 'line1')
    keydown(textarea, 'Enter', true)
    expect(onSend).toHaveBeenCalledTimes(1)
  })

  it('blocks attachment-only send', () => {
    const { container, onSend } = renderInputBar({
      attachments: [{
        id: '1',
        file: new File(['x'], 'a.pdf', { type: 'application/pdf' }),
        metadata: {
          name: 'a.pdf',
          size: 1,
          type: 'application/pdf',
          lastModified: new Date()
        },
        status: 'uploaded',
        progress: 100
      }]
    })
    const send = container.querySelector('[aria-label="Send message"]') as HTMLButtonElement
    click(send)
    expect(onSend).not.toHaveBeenCalled()
  })
})
