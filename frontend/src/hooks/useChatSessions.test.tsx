import { useEffect } from 'react'
import { describe, it, expect, vi } from 'vitest'
import { useChatSessions, type UseChatSessionsReturn } from './useChatSessions'
import { renderComponent } from '../test/domTestUtils'
import { act } from 'react'

function HookProbe({ onValue }: { onValue: (v: UseChatSessionsReturn) => void }) {
  const hook = useChatSessions()
  useEffect(() => onValue(hook), [hook, onValue])
  return null
}

describe('useChatSessions', () => {
  it('creates and selects sessions, updates title/message flow', async () => {
    let state: UseChatSessionsReturn | null = null
    renderComponent(<HookProbe onValue={(v) => { state = v }} />)
    expect(state).toBeTruthy()

    let sessionId = ''
    let assistantId = ''
    await act(async () => {
      const session = state!.createNewSession()
      sessionId = session.id
      state!.appendUserMessage(session.id, '   first user prompt   ')
      assistantId = state!.createAssistantPlaceholder(session.id, '')
      state!.appendToken(session.id, 'hello')
      state!.setSources(session.id, assistantId, [{ file_id: 'f', filename: 'n', file_type: 'pdf', chunk_index: 0, excerpt: 'e' }])
      state!.failMessage(session.id, assistantId, 'oops')
    })

    const current = state!.sessions.find((s) => s.id === sessionId)
    expect(current?.title).not.toBe('New chat')
    expect(current?.messages[0].role).toBe('user')
    expect(current?.messages[1].status).toBe('failed')
    expect(current?.messages[1].sources?.length).toBe(1)
  })

  it('filters by debounced search', async () => {
    vi.useFakeTimers()
    let state: UseChatSessionsReturn | null = null
    renderComponent(<HookProbe onValue={(v) => { state = v }} />)
    await act(async () => {
      const session = state!.createNewSession()
      state!.appendUserMessage(session.id, 'compressor alarm')
      state!.debouncedSetSearchQuery('compressor')
      vi.advanceTimersByTime(200)
    })
    expect(state!.filteredSessions.length).toBe(1)
    await act(async () => {
      state!.debouncedSetSearchQuery('nomatch')
      vi.advanceTimersByTime(200)
    })
    expect(state!.filteredSessions.length).toBe(0)
    vi.useRealTimers()
  })
})
