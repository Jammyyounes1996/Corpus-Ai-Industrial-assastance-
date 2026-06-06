import { describe, it, expect, vi } from 'vitest'
import { fetchHealthStatus } from './statusService'

describe('statusService', () => {
  it('handles ok status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok', version: '1.0', database: 'ok', qdrant: 'ok', ollama: 'ok', model: 'm', provider: 'p', rag_enabled: true, ocr_available: true, gpu_available: false })
    } as Response)
    const result = await fetchHealthStatus()
    expect(result.connection).toBe('connected')
    expect(result.details.model).toBe('m')
  })

  it('handles degraded and qdrant collection missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'degraded', version: '1.0', database: 'ok', qdrant: 'collection_missing', ollama: 'ok' })
    } as Response)
    const result = await fetchHealthStatus()
    expect(result.connection).toBe('degraded')
    expect(result.details.qdrant).toBe('Unavailable')
  })

  it('handles network failure with unavailable details', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'))
    const result = await fetchHealthStatus()
    expect(result.connection).toBe('disconnected')
    expect(result.details.model).toBe('Unavailable')
    expect(result.error).toBe('offline')
  })

  it('handles non-2xx responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 503 } as Response)
    const result = await fetchHealthStatus()
    expect(result.connection).toBe('disconnected')
    expect(result.error).toContain('503')
  })

  it('applies missing optional fields fallback labels', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok', version: '1.2', database: 'ok', qdrant: 'ok', ollama: 'ok' })
    } as Response)
    const result = await fetchHealthStatus()
    expect(result.details.model).toBe('Unknown')
    expect(result.details.provider).toBe('Unknown')
    expect(result.details.ocr).toBe('Unknown')
    expect(result.details.gpu).toBe('Unknown')
    expect(result.details.rag).toBe('Unknown')
  })
})
