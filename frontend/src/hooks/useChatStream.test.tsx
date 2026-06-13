import { useEffect, act } from 'react'
import { describe, it, expect, vi } from 'vitest'
import { useChatStream, type UseChatStreamReturn } from './useChatStream'
import { renderComponent } from '../test/domTestUtils'

const streamChatMock = vi.fn()
const createBackendChatMock = vi.fn()

vi.mock('../services/chatStreamService', () => ({
  streamChat: (...args: unknown[]) => streamChatMock(...args),
  createBackendChat: (...args: unknown[]) => createBackendChatMock(...args)
}))

function HookProbe({ onValue, onEvent }: { onValue: (v: UseChatStreamReturn) => void; onEvent: (event: unknown) => void }) {
  const hook = useChatStream({ onEvent })
  useEffect(() => onValue(hook), [hook, onValue])
  return null
}

describe('useChatStream', () => {
  it('enforces upload -> create chat -> stream order', async () => {
    const calls: string[] = []
    createBackendChatMock.mockImplementation(async () => {
      calls.push('create')
      return { id: 'chat-1' }
    })
    streamChatMock.mockImplementation(async () => {
      calls.push('stream')
    })

    let state: UseChatStreamReturn | null = null
    renderComponent(<HookProbe onValue={(v) => { state = v }} onEvent={() => undefined} />)

    let id: string | null = null
    await act(async () => {
      id = await state!.send(null, { query: 'hello', attached_files: ['f1'] })
    })
    expect(id).toBe('chat-1')
    expect(calls).toEqual(['create', 'stream'])
    expect(streamChatMock).toHaveBeenCalledWith(
      'chat-1',
      expect.objectContaining({ query: 'hello', attached_files: ['f1'] }),
      expect.any(Function),
      expect.any(Object),
    )
  })

  it('handles failure and enables retry before token', async () => {
    createBackendChatMock.mockResolvedValue({ id: 'chat-2' })
    streamChatMock.mockRejectedValue(new Error('drop'))
    let state: UseChatStreamReturn | null = null
    renderComponent(<HookProbe onValue={(v) => { state = v }} onEvent={() => undefined} />)
    await act(async () => {
      await state!.send(null, { query: 'hello' })
    })
    expect(state!.error).toBe('drop')
    expect(state!.canRetry).toBe(true)
  })

  it('forwards explicit GroundX mode without selected scope', async () => {
    createBackendChatMock.mockResolvedValue({ id: 'chat-3' })
    streamChatMock.mockResolvedValue(undefined)
    let state: UseChatStreamReturn | null = null
    renderComponent(<HookProbe onValue={(v) => { state = v }} onEvent={() => undefined} />)

    await act(async () => {
      await state!.send(null, { query: 'search bucket', answer_mode: 'groundx' })
    })

    expect(streamChatMock).toHaveBeenCalledWith(
      'chat-3',
      expect.objectContaining({ query: 'search bucket', answer_mode: 'groundx' }),
      expect.any(Function),
      expect.any(Object),
    )
  })
})
