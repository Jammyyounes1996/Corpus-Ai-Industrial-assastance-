import './OCRTab.css'
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Camera,
  AlertCircle,
  MessageCircle,
  FileText,
  Upload,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Archive,
} from 'lucide-react'
import { config } from '../../config'
import type { FileItem } from '../../types/files'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'
import type { AttachedFile, SupportedMimeType } from '../../types/attachments'
import { uploadFileToEndpoint } from '../../services/fileUploadService'

type OCRFilter = 'all' | 'image' | 'pdf'
type CardStatus = 'ready' | 'extracting' | 'extracted' | 'cached' | 'failed'

const FILTER_OPTIONS: { value: OCRFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'image', label: 'Images' },
  { value: 'pdf', label: 'PDFs' },
]

const LARGE_IMAGE_WARNING_BYTES = 10 * 1024 * 1024
const OCR_IMAGE_PROMPT = 'Extract text from image'
const NO_READABLE_TEXT_MESSAGE = 'No readable text was found.'

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes >= 1024 * 1024) {
    return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
  }
  if (sizeBytes >= 1024) {
    return `${Math.round(sizeBytes / 1024)} KB`
  }
  return `${sizeBytes} B`
}

function formatFileDate(createdAt: string | null | undefined): string {
  if (!createdAt) return 'Unknown date'

  const parsed = new Date(createdAt)
  if (Number.isNaN(parsed.getTime())) return 'Unknown date'
  return parsed.toLocaleDateString()
}

function formatPdfExtractedText(text: string): string {
  const normalized = text.trim()
  if (!normalized) return NO_READABLE_TEXT_MESSAGE
  return normalized.replace(/---\s*PAGE\s+(\d+)\s*---/gi, '## Page $1')
}

function getInitialCardStatus(file: FileItem): CardStatus {
  return file.ocr_summary ? 'cached' : 'ready'
}

function getStatusLabel(status: CardStatus): string {
  switch (status) {
    case 'extracting':
      return 'Extracting...'
    case 'extracted':
      return 'Extracted'
    case 'cached':
      return 'Cached'
    case 'failed':
      return 'Failed'
    default:
      return 'Ready'
  }
}

interface OCRTabProps {
  sessions: UseChatSessionsReturn
  onTabChange: (tabId: string) => void
}

export function OCRTab({ sessions, onTabChange }: OCRTabProps) {
  const [files, setFiles] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<OCRFilter>('all')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(new Map())
  const [cardStatuses, setCardStatuses] = useState<Map<string, CardStatus>>(new Map())
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchFiles = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ sort: 'date_desc', limit: '200', offset: '0' })
      const res = await fetch(`${config.fileEndpoints.listFiles}?${params}`, { signal })
      if (!res.ok) throw new Error(`Failed to fetch files (${res.status})`)
      const data = await res.json()
      const ocrFiles = (data.files || []).filter(
        (f: FileItem) => f.file_type === 'image' || f.file_type === 'pdf'
      )
      setFiles(ocrFiles)
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchFiles(controller.signal)
    return () => controller.abort()
  }, [fetchFiles])

  const getOCREndpoint = (file: File): string | null => {
    if (file.type === 'application/pdf') return config.chatEndpoints.ocrPdf
    if (file.type.startsWith('image/')) return config.chatEndpoints.ingestImage
    return null
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files
    if (!selected || selected.length === 0) return
    setUploading(true)
    setError(null)
    for (const file of Array.from(selected)) {
      const endpoint = getOCREndpoint(file)
      if (!endpoint) continue
      try {
        setUploadProgress((prev) => new Map(prev).set(file.name, 0))
        await uploadFileToEndpoint(file, endpoint, (percent) => {
          setUploadProgress((prev) => new Map(prev).set(file.name, percent))
        })
        setUploadProgress((prev) => {
          const next = new Map(prev)
          next.delete(file.name)
          return next
        })
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      }
    }
    setUploading(false)
    setUploadProgress(new Map())
    if (fileInputRef.current) fileInputRef.current.value = ''
    await fetchFiles()
  }

  const handleOpenInChat = async (file: FileItem) => {
    const session = sessions.createNewSession()
    const fileId = String(file.id)
    const message = OCR_IMAGE_PROMPT
    let attachments: AttachedFile[] | undefined

    try {
      const url = config.fileEndpoints.fileContent.replace(':fileId', fileId)
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Failed to fetch image (${response.status})`)

      const blob = await response.blob()
      const fileObject = new File([blob], file.original_name, {
        type: blob.type || file.file_type || 'image/jpeg',
      })

      if (fileObject.size === 0) {
        console.warn('OCR image attachment is empty; falling back to text-only chat message')
      } else {
        if (fileObject.size > LARGE_IMAGE_WARNING_BYTES) {
          console.warn(`OCR image attachment is larger than 10MB: ${fileObject.size} bytes`)
        }

        attachments = [{
          id: `ocr-${file.id}`,
          backendFileId: fileId,
          file: fileObject,
          metadata: {
            name: fileObject.name,
            size: fileObject.size,
            type: fileObject.type as SupportedMimeType,
            lastModified: new Date(fileObject.lastModified),
          },
          status: 'uploaded',
          progress: 100,
          objectUrl: URL.createObjectURL(fileObject),
        }]
      }
    } catch (err) {
      console.warn('Failed to attach OCR image; falling back to text-only chat message', err)
    }

    sessions.appendUserMessage(session.id, message, attachments)
    sessions.updateSession(session.id, {
      pendingSend: {
        query: message,
        attachedFileIds: [fileId],
        taskType: 'ocr_image',
      },
    })
    onTabChange('chat')
  }

  const handleExtractOCR = async (file: FileItem) => {
    const fileId = String(file.id)
    if (cardStatuses.get(fileId) === 'extracting') return
    setCardStatuses((prev) => new Map(prev).set(fileId, 'extracting'))
    setError(null)
    try {
      const url = config.ocrEndpoints.extract.replace(':fileId', fileId)
      const res = await fetch(url, { method: 'POST' })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail?.message || `OCR extraction failed (${res.status})`)
      }
      const data = await res.json()
      const extractedText = formatPdfExtractedText(String(data.extracted_text || ''))
      const wasCached: boolean = data.cached === true

      setCardStatuses((prev) => new Map(prev).set(fileId, wasCached ? 'cached' : 'extracted'))

      const session = sessions.createNewSession()
      const userMessage = `Deep OCR extraction: ${file.original_name}`

      const pdfFileObj = new File([], file.original_name, { type: 'application/pdf' })
      const attachment: AttachedFile = {
        id: `ocr-pdf-${file.id}`,
        backendFileId: fileId,
        file: pdfFileObj,
        metadata: {
          name: file.original_name,
          size: file.size_bytes,
          type: 'application/pdf' as SupportedMimeType,
          lastModified: new Date(),
        },
        status: 'uploaded',
        progress: 100,
      }

      sessions.appendUserMessage(session.id, userMessage, [attachment])

      const assistantMsgId = sessions.createAssistantPlaceholder(session.id, '')
      sessions.appendToken(session.id, extractedText)
      sessions.completeMessage(session.id, assistantMsgId)
      onTabChange('chat')
      await fetchFiles()
    } catch (err: unknown) {
      setCardStatuses((prev) => new Map(prev).set(fileId, 'failed'))
      setError(err instanceof Error ? err.message : 'OCR extraction failed')
    }
  }

  const getCardStatus = (file: FileItem): CardStatus => {
    return cardStatuses.get(String(file.id)) ?? getInitialCardStatus(file)
  }

  const filteredFiles = files.filter((f) => {
    if (activeFilter === 'all') return true
    if (activeFilter === 'image') return f.file_type === 'image'
    if (activeFilter === 'pdf') return f.file_type === 'pdf'
    return true
  })

  if (loading) {
    return (
      <div className="ocr-loading">
        <Camera size={32} className="spin" />
        <p>Loading files...</p>
      </div>
    )
  }

  return (
    <div className="ocr-tab">
      <div className="ocr-toolbar">
        <div className="ocr-filters">
          {FILTER_OPTIONS.map((f) => (
            <button
              key={f.value}
              className={`filter-chip ${activeFilter === f.value ? 'active' : ''}`}
              onClick={() => setActiveFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="ocr-actions">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={16} />
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>

      {error && (
        <div className="ocr-error-bar">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {uploadProgress.size > 0 && (
        <div className="ocr-upload-progress">
          {Array.from(uploadProgress.entries()).map(([name, percent]) => (
            <div key={name} className="ocr-progress-card">
              <span className="ocr-progress-name">{name}</span>
              <span className="ocr-progress-percent">
                {percent < 100 ? `${percent}%` : 'Processing...'}
              </span>
              <div className="ocr-progress-bar">
                <div className="ocr-progress-fill" style={{ width: `${percent}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {filteredFiles.length === 0 && uploadProgress.size === 0 && (
        <div className="ocr-empty">
          <Camera size={48} />
          <p>No files for OCR yet. Upload an image or PDF to get started.</p>
        </div>
      )}

      <div className="ocr-grid">
        {filteredFiles.map((file) => (
          <div key={file.id} className={`ocr-card ${file.file_type === 'pdf' ? 'ocr-card-pdf' : ''}`}>
            {file.file_type === 'image' ? (
              <>
                <img
                  src={config.fileEndpoints.fileContent.replace(':fileId', String(file.id))}
                  alt={file.original_name}
                  className="ocr-thumbnail"
                  loading="lazy"
                />
                <div className="ocr-card-body">
                  <span className="ocr-filename">{file.original_name}</span>
                  <div className="ocr-card-meta">
                    <span className={`ocr-status ocr-status--${getCardStatus(file)}`}>
                      {getStatusLabel(getCardStatus(file))}
                    </span>
                    <button className="ocr-card-action" onClick={() => handleOpenInChat(file)}>
                      <MessageCircle size={16} />
                      <span>Extract</span>
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div
                  className="ocr-pdf-icon-area"
                  onClick={() => {
                    if (getCardStatus(file) !== 'extracting') {
                      handleExtractOCR(file)
                    }
                  }}
                >
                  <FileText size={48} />
                  {getCardStatus(file) === 'extracting' && (
                    <div className="ocr-pdf-overlay">
                      <RefreshCw size={24} className="spin" />
                      <span>Extracting...</span>
                    </div>
                  )}
                  {getCardStatus(file) !== 'extracting' && (
                    <div className="ocr-pdf-overlay ocr-pdf-overlay-hover">
                      <MessageCircle size={20} />
                      <span>Extract Text</span>
                    </div>
                  )}
                </div>
                <div className="ocr-card-body">
                  <span className="ocr-filename">{file.original_name}</span>
                  <span className="ocr-file-meta">
                    {formatFileSize(file.size_bytes)} · {formatFileDate(file.created_at)}
                  </span>
                  <div className="ocr-card-meta">
                    <span className={`ocr-status ocr-status--${getCardStatus(file)}`}>
                      {getCardStatus(file) === 'cached' && <Archive size={12} />}
                      {getCardStatus(file) === 'extracted' && <CheckCircle size={12} />}
                      {getCardStatus(file) === 'failed' && <AlertTriangle size={12} />}
                      {getStatusLabel(getCardStatus(file))}
                    </span>
                    <button
                      className="ocr-card-action"
                      disabled={getCardStatus(file) === 'extracting'}
                      onClick={() => handleExtractOCR(file)}
                    >
                      <MessageCircle size={16} />
                      <span>Extract Text</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
