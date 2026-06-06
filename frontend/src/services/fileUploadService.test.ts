import { describe, it, expect, vi } from 'vitest'
import { getUploadEndpoint, uploadFile, uploadFiles } from './fileUploadService'

describe('fileUploadService', () => {
  it('maps supported mime types to endpoints', () => {
    expect(getUploadEndpoint('application/pdf')).toBe('/api/ingest/pdf')
    expect(getUploadEndpoint('image/png')).toBe('/api/ingest/image')
    expect(getUploadEndpoint('audio/mpeg')).toBe('/api/ingest/audio')
  })

  it('uploads one file per request with FormData file field', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ file_id: 'f1', filename: 'doc.pdf', file_type: 'pdf', size: 5, upload_timestamp: '2026-01-01T00:00:00.000Z' })
    } as Response)

    const file = new File(['abc'], 'doc.pdf', { type: 'application/pdf' })
    const result = await uploadFile(file)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, request] = fetchMock.mock.calls[0]
    const form = request?.body as FormData
    expect(form.get('file')).toBe(file)
    expect(result.file_id).toBe('f1')
  })

  it('rejects unsupported file types', async () => {
    const file = new File(['abc'], 'doc.txt', { type: 'text/plain' })
    await expect(uploadFile(file)).rejects.toThrow('Unsupported file type')
  })

  it('returns mapped backend payload errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Bad upload payload' })
    } as Response)

    const file = new File(['abc'], 'doc.pdf', { type: 'application/pdf' })
    await expect(uploadFile(file)).rejects.toThrow('Bad upload payload')
  })

  it('supports partial failures in multi-upload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: async () => ({ file_id: 'ok', filename: 'a.pdf', file_type: 'pdf', size: 1, upload_timestamp: '2026-01-01T00:00:00.000Z' }) } as Response)
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ error: 'failed' }) } as Response)

    const first = new File(['1'], 'a.pdf', { type: 'application/pdf' })
    const second = new File(['2'], 'b.pdf', { type: 'application/pdf' })
    const result = await uploadFiles([first, second])

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result.successes).toHaveLength(1)
    expect(result.errors).toHaveLength(1)
    expect(result.errors[0].file.name).toBe('b.pdf')
  })
})
