import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { OCRTab } from './OCRTab'
import { renderComponent } from '../../test/domTestUtils'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'
import { config } from '../../config'

const imageFile = {
  id: 'file-13',
  original_name: '13.png',
  file_type: 'image',
  size_bytes: 1234,
  indexing_status: 'completed',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
}

const pdfFile = {
  id: 'file-pdf-1',
  original_name: 'report.pdf',
  file_type: 'pdf',
  size_bytes: 91242,
  indexing_status: 'completed',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
}

function makeSessions() {
  return {
    createNewSession: vi.fn(() => ({ id: 'session-1' })),
    appendUserMessage: vi.fn(),
    createAssistantPlaceholder: vi.fn(() => 'msg-assistant-1'),
    appendToken: vi.fn(),
    completeMessage: vi.fn(),
    updateSession: vi.fn(),
    setActiveSession: vi.fn(),
    deleteSession: vi.fn(),
    searchQuery: '',
    setSearchQuery: vi.fn(),
    debouncedSetSearchQuery: vi.fn(),
    sessions: [],
    activeSessionId: null,
    loading: false,
    filteredSessions: [],
    setSources: vi.fn(),
    setThinkingSteps: vi.fn(),
    failMessage: vi.fn(),
    cancelMessage: vi.fn(),
    createStreamEventHandler: vi.fn(),
    cancelStreamingMessage: vi.fn(),
  }
}

function installMockXhr() {
  const requests: MockXMLHttpRequest[] = []

  class MockXMLHttpRequest {
    method = ''
    url = ''
    status = 0
    responseText = ''
    upload = { onprogress: null as ((event: { lengthComputable: boolean; loaded: number; total: number }) => void) | null }
    onload: (() => void) | null = null
    onerror: (() => void) | null = null

    open(method: string, url: string) {
      this.method = method
      this.url = url
    }

    send() {
      requests.push(this)
      this.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 1 })
      this.status = 200
      this.responseText = JSON.stringify({
        file_id: 'uploaded-file',
        filename: 'uploaded-file',
        file_type: 'image',
        size: 10,
        upload_timestamp: '2026-01-01T00:00:00Z',
      })
      this.onload?.()
    }
  }

  vi.stubGlobal('XMLHttpRequest', MockXMLHttpRequest)
  return requests
}

describe('OCRTab', () => {
  beforeEach(() => {
    vi.stubGlobal('URL', Object.assign(URL, {
      createObjectURL: vi.fn(() => 'blob:ocr-image'),
    }))
    vi.stubGlobal('fetch', vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/content')) {
        return new Response(new Blob(['image-bytes'], { type: 'image/png' }), {
          status: 200,
          headers: { 'Content-Type': 'image/png' },
        })
      }

      if (url.includes('/api/ocr/') && opts?.method === 'POST') {
        return new Response(JSON.stringify({
          file_id: 'file-pdf-1',
          extracted_text: '--- PAGE 1 ---\nHello world\n--- PAGE 2 ---\nMore text',
          pages_processed: 2,
          model_used: 'gemma4:12b',
          cached: false,
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      return new Response(JSON.stringify({ files: [imageFile, pdfFile] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens image clicks with an OCR-only prompt and attached file id', async () => {
    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('13.png')

    fireEvent.click(await screen.findByRole('button', { name: 'Extract' }))

    await waitFor(() => {
      expect(sessions.appendUserMessage).toHaveBeenCalled()
      expect(sessions.updateSession).toHaveBeenCalled()
    })

    const message = sessions.appendUserMessage.mock.calls[0][1]
    const attachments = sessions.appendUserMessage.mock.calls[0][2]

    expect(message).toBe('Extract text from image')
    expect(attachments[0]).toMatchObject({
      backendFileId: 'file-13',
      status: 'uploaded',
      metadata: expect.objectContaining({ name: '13.png', type: 'image/png' }),
    })
    expect(sessions.updateSession).toHaveBeenCalledWith('session-1', {
      pendingSend: {
        query: message,
        attachedFileIds: ['file-13'],
        taskType: 'ocr_image',
      },
    })
    expect(onTabChange).toHaveBeenCalledWith('chat')
  })

  it('uploads image files to the OCR image endpoint', async () => {
    const requests = installMockXhr()
    const sessions = makeSessions()
    const onTabChange = vi.fn()
    const { container } = renderComponent(
      <OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />
    )

    await screen.findByText('13.png')

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['img'], 'panel.png', { type: 'image/png' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(requests).toHaveLength(1)
    })

    expect(requests[0].method).toBe('POST')
    expect(requests[0].url).toBe(config.chatEndpoints.ingestImage)
  })

  it('uploads pdf files to the OCR-only pdf endpoint', async () => {
    const requests = installMockXhr()
    const sessions = makeSessions()
    const onTabChange = vi.fn()
    const { container } = renderComponent(
      <OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />
    )

    await screen.findByText('13.png')

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['pdf'], 'report.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(requests).toHaveLength(1)
    })

    expect(requests[0].url).toBe(config.chatEndpoints.ocrPdf)
  })

  it('clicking PDF Extract Text calls OCR endpoint', async () => {
    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')

    const extractBtn = await screen.findByRole('button', { name: 'Extract Text' })
    fireEvent.click(extractBtn)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/ocr/file-pdf-1/extract'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('sends PDF OCR result to chat with user and assistant messages', async () => {
    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')
    fireEvent.click(await screen.findByRole('button', { name: 'Extract Text' }))

    await waitFor(() => {
      expect(sessions.createNewSession).toHaveBeenCalled()
    })

    const userCall = sessions.appendUserMessage.mock.calls[0]
    expect(userCall[0]).toBe('session-1')
    expect(userCall[1]).toBe('Deep OCR extraction: report.pdf')
    expect(userCall[2]).toHaveLength(1)
    expect(userCall[2][0].backendFileId).toBe('file-pdf-1')
    expect(userCall[2][0].metadata.name).toBe('report.pdf')
    expect(userCall[2][0].metadata.type).toBe('application/pdf')

    expect(sessions.createAssistantPlaceholder).toHaveBeenCalledWith('session-1', '')
    expect(sessions.appendToken).toHaveBeenCalledWith(
      'session-1',
      expect.stringContaining('## Page 1'),
    )
    expect(sessions.completeMessage).toHaveBeenCalledWith('session-1', 'msg-assistant-1')
    expect(onTabChange).toHaveBeenCalledWith('chat')
  })

  it('does not render full extracted text inside the PDF card', async () => {
    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')
    fireEvent.click(await screen.findByRole('button', { name: 'Extract Text' }))

    await waitFor(() => {
      expect(screen.getByText('Extracted')).toBeDefined()
    })

    expect(screen.queryByText('## Page 1')).toBeNull()
    expect(screen.queryByText('Hello world')).toBeNull()
    expect(screen.queryByText('More text')).toBeNull()
  })

  it('shows compact Cached badge when backend returns cached=true', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/api/ocr/') && opts?.method === 'POST') {
        return new Response(JSON.stringify({
          file_id: 'file-pdf-1',
          extracted_text: '--- PAGE 1 ---\nCached content',
          pages_processed: 1,
          model_used: 'gemma4:12b',
          cached: true,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      return new Response(JSON.stringify({ files: [pdfFile] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }))

    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')
    fireEvent.click(await screen.findByRole('button', { name: 'Extract Text' }))

    await waitFor(() => {
      expect(screen.getByText('Cached')).toBeDefined()
    })
  })

  it('shows compact Ready status without rendering OCR preview text in image cards', async () => {
    const sessions = makeSessions()
    const onTabChange = vi.fn()

    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      files: [{
        ...imageFile,
        ocr_summary: { text_preview: 'Internal OCR preview should stay out of the card' },
      }],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })))

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('13.png')

    expect(screen.getByText('Cached')).toBeDefined()
    expect(screen.queryByText('Internal OCR preview should stay out of the card')).toBeNull()
  })

  it('shows Extracting during PDF OCR and then updates to Extracted', async () => {
    let resolveFetch!: (value: Response) => void
    vi.stubGlobal('fetch', vi.fn((url: string, opts?: RequestInit) => {
      if (url.includes('/api/ocr/') && opts?.method === 'POST') {
        return new Promise<Response>((resolve) => {
          resolveFetch = resolve
        })
      }

      return Promise.resolve(new Response(JSON.stringify({ files: [pdfFile] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
    }))

    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')
    fireEvent.click(await screen.findByRole('button', { name: 'Extract Text' }))

    expect((await screen.findAllByText('Extracting...')).length).toBeGreaterThan(0)

    resolveFetch(new Response(JSON.stringify({
      file_id: 'file-pdf-1',
      extracted_text: '--- PAGE 1 ---\nHello world',
      pages_processed: 1,
      model_used: 'gemma4:12b',
      cached: false,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))

    await waitFor(() => {
      expect(screen.getByText('Extracted')).toBeDefined()
    })
  })

  it('shows Failed badge on extraction error', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/api/ocr/') && opts?.method === 'POST') {
        return new Response(JSON.stringify({
          detail: { error: 'OCRError', message: 'PDF OCR extraction failed while rendering pages.' },
        }), { status: 500, headers: { 'Content-Type': 'application/json' } })
      }
      return new Response(JSON.stringify({ files: [pdfFile] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }))

    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')
    fireEvent.click(await screen.findByRole('button', { name: 'Extract Text' }))

    await waitFor(() => {
      expect(screen.getByText('Failed')).toBeDefined()
    })

    expect(screen.getByText('PDF OCR extraction failed while rendering pages.')).toBeDefined()
    expect(sessions.createNewSession).not.toHaveBeenCalled()
    expect(onTabChange).not.toHaveBeenCalled()
  })

  it('does not create duplicate chat messages for one PDF extraction click', async () => {
    const sessions = makeSessions()
    const onTabChange = vi.fn()

    renderComponent(<OCRTab sessions={sessions as unknown as UseChatSessionsReturn} onTabChange={onTabChange} />)

    await screen.findByText('report.pdf')
    fireEvent.click(await screen.findByRole('button', { name: 'Extract Text' }))

    await waitFor(() => {
      expect(sessions.appendUserMessage).toHaveBeenCalledTimes(1)
    })

    expect(sessions.createAssistantPlaceholder).toHaveBeenCalledTimes(1)
    expect(sessions.updateSession).not.toHaveBeenCalledWith('session-1', expect.objectContaining({
      pendingSend: expect.anything(),
    }))
  })
})
