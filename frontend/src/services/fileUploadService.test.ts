import { describe, it, expect, vi } from 'vitest'
import { getUploadEndpoint, uploadFile, uploadFiles, uploadFileWithProgress } from './fileUploadService'

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

  it('preserves GroundX lifecycle metadata in XHR upload responses', async () => {
    class MockXMLHttpRequest {
      status = 200
      responseText = JSON.stringify({
        file_id: 'pdf-1',
        filename: 'manual.pdf',
        file_type: 'pdf',
        size: 12,
        upload_timestamp: '2026-01-01T00:00:00.000Z',
        indexing_status: 'queued',
        status_message: 'Queued for GroundX indexing',
        groundx_process_id: 'proc-1',
        groundx_bucket_id: '28306',
      })
      upload = { onprogress: null as ((event: { lengthComputable: boolean; loaded: number; total: number }) => void) | null }
      onload: (() => void) | null = null
      onerror: (() => void) | null = null

      open() {}

      send() {
        this.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 })
        this.onload?.()
      }
    }

    vi.stubGlobal('XMLHttpRequest', MockXMLHttpRequest)
    const progress = vi.fn()

    const file = new File(['abc'], 'manual.pdf', { type: 'application/pdf' })
    const result = await uploadFileWithProgress(file, progress)

    expect(progress).toHaveBeenCalledWith(50)
    expect(result.indexing_status).toBe('queued')
    expect(result.status_message).toBe('Queued for GroundX indexing')
    expect(result.groundx_process_id).toBe('proc-1')
    expect(result.groundx_bucket_id).toBe('28306')
  })
})
