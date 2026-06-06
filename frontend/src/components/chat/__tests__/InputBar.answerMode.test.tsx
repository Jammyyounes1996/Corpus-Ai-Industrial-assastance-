import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { InputBar } from '../InputBar'
import type { AnswerMode } from '../../../types/api'

function renderInputBar(overrides: {
  answerMode?: AnswerMode
  onAnswerModeChange?: (mode: AnswerMode) => void
  onSend?: (text: string) => void
} = {}) {
  const onSend = overrides.onSend ?? vi.fn()
  const onAnswerModeChange = overrides.onAnswerModeChange ?? vi.fn()

  const result = render(
    <InputBar
      onSend={onSend}
      onAttachFiles={() => {}}
      onRemoveAttachment={() => {}}
      onRetryAttachment={() => {}}
      validateAttachmentFiles={() => []}
      canAddMoreFiles={true}
      attachments={[]}
      failedAttachments={[]}
      answerMode={overrides.answerMode}
      onAnswerModeChange={onAnswerModeChange}
    />
  )

  return { onSend, onAnswerModeChange, ...result }
}

function openModeMenu() {
  const btn = screen.getByRole('button', { name: 'Select answer mode' })
  fireEvent.click(btn)
}

describe('InputBar answer_mode dropdown', () => {
  it('renders three answer mode options', () => {
    renderInputBar()
    openModeMenu()

    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(3)

    const labels = options.map((o) => o.textContent)
    expect(labels).toEqual(
      expect.arrayContaining(['GroundX Mode', 'Audio Mode', 'General Mode'])
    )
  })

  it('defaults to General Mode', () => {
    renderInputBar()

    const btn = screen.getByRole('button', { name: 'Select answer mode' })
    expect(btn.textContent).toContain('General Mode')
  })

  it('sends answer_mode=groundx when GroundX Mode is selected', () => {
    const onAnswerModeChange = vi.fn()
    renderInputBar({ onAnswerModeChange })

    openModeMenu()

    const groundxOption = screen.getAllByRole('option').find((o) => o.textContent === 'GroundX Mode')
    expect(groundxOption).toBeTruthy()
    fireEvent.click(groundxOption!)

    expect(onAnswerModeChange).toHaveBeenCalledWith('groundx')
  })

  it('sends answer_mode=audio when Audio Mode is selected', () => {
    const onAnswerModeChange = vi.fn()
    renderInputBar({ onAnswerModeChange })

    openModeMenu()

    const audioOption = screen.getAllByRole('option').find((o) => o.textContent === 'Audio Mode')
    expect(audioOption).toBeTruthy()
    fireEvent.click(audioOption!)

    expect(onAnswerModeChange).toHaveBeenCalledWith('audio')
  })

  it('sends answer_mode=general when General Mode is selected', () => {
    const onAnswerModeChange = vi.fn()
    renderInputBar({ onAnswerModeChange, answerMode: 'groundx' })

    openModeMenu()

    const generalOption = screen.getAllByRole('option').find((o) => o.textContent === 'General Mode')
    expect(generalOption).toBeTruthy()
    fireEvent.click(generalOption!)

    expect(onAnswerModeChange).toHaveBeenCalledWith('general')
  })
})
