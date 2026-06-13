import { screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DocumentsTab } from './DocumentsTab'
import { renderComponent } from '../../test/domTestUtils'


describe('DocumentsTab', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/api/files/file-1/status')) {
        return new Response(JSON.stringify({
          file_id: 'file-1',
          original_name: 'manual.pdf',
          file_type: 'pdf',
          indexing_status: 'indexed',
          groundx_process_id: 'proc-1',
          groundx_document_id: 'doc-1',
          groundx_bucket_id: '28306',
          status_message: 'Ready for GroundX retrieval',
          error_message: null,
          ready_for_groundx_retrieval: true,
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }

      return new Response(JSON.stringify({
        files: [{
          id: 'file-1',
          original_name: 'manual.pdf',
          file_type: 'pdf',
          size_bytes: 100,
          indexing_status: 'processing',
          status_message: 'Processing in GroundX',
          error_message: null,
          groundx_process_id: 'proc-1',
          groundx_document_id: null,
          groundx_bucket_id: '28306',
          ready_for_groundx_retrieval: false,
          created_at: '2026-01-01T00:00:00Z',
        }],
        total: 1,
        limit: 100,
        offset: 0,
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('polls processing pdf cards until GroundX marks them ready', async () => {
    renderComponent(<DocumentsTab />)

    await screen.findByText('Processing in GroundX')

    await waitFor(() => {
      expect(screen.getByText('Ready for GroundX retrieval')).toBeTruthy()
    }, { timeout: 5000 })
  }, 8000)
})
