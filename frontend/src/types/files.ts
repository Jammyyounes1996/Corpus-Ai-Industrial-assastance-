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
  id: number
  original_name: string
  file_type: string
  size_bytes: number
  indexing_status: string
  error_message: string | null
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
