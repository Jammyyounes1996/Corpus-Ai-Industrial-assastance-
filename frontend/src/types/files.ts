export interface TranscriptSummary {
  duration_seconds: number | null
  language: string | null
  text: string
}

export interface OcrSummary {
  text_preview: string
  model_used: string
}

export interface FileItem {
  id: string
  original_name: string
  file_type: string
  size_bytes: number
  indexing_status: string
  status_message?: string | null
  error_message: string | null
  groundx_process_id?: string | null
  groundx_document_id?: string | null
  groundx_bucket_id?: string | null
  ready_for_groundx_retrieval?: boolean
  created_at: string | null
  transcript_summary?: TranscriptSummary
  ocr_summary?: OcrSummary
}

export interface FileListResponse {
  files: FileItem[]
  total: number
  limit: number
  offset: number
}
