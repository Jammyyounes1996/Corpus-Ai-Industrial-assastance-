import './DocumentsTab.css'
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  FileText,
  Headphones,
  ImageIcon,
  Trash2,
  Upload,
  RefreshCw,
  File,
  AlertCircle,
  FolderOpen,
} from 'lucide-react'
import { config } from '../../config'
import type { FileItem } from '../../types/files'
import { uploadFileWithProgress } from '../../services/fileUploadService'

type FileFilter = 'all' | 'pdf' | 'audio' | 'image'
type SortOption = 'date_desc' | 'name' | 'date_asc'

const FILTER_OPTIONS: { value: FileFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pdf', label: 'PDF' },
  { value: 'audio', label: 'Audio' },
  { value: 'image', label: 'Image' },
]

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'date_desc', label: 'Newest first' },
  { value: 'name', label: 'Name A-Z' },
  { value: 'date_asc', label: 'Oldest first' },
]

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'indexed':
      return 'var(--color-success)'
    case 'queued':
    case 'processing':
      return 'var(--color-warning)'
    case 'failed':
      return 'var(--color-error)'
    default:
      return 'var(--text-muted)'
  }
}

function getStatusLabel(file: FileItem): string {
  if (file.status_message) return file.status_message
  switch (file.indexing_status) {
    case 'queued':
      return 'Queued for GroundX indexing'
    case 'processing':
      return 'Processing in GroundX'
    case 'indexed':
      return 'Ready for GroundX retrieval'
    case 'failed':
      return 'GroundX indexing failed'
    default:
      return file.indexing_status
  }
}

function getFileIcon(fileType: string) {
  switch (fileType) {
    case 'pdf':
      return <FileText size={24} />
    case 'audio':
      return <Headphones size={24} />
    case 'image':
      return <ImageIcon size={24} />
    default:
      return <File size={24} />
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function DocumentsTab() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<FileFilter>('all')
  const [sortBy, setSortBy] = useState<SortOption>('date_desc')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(new Map())
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollingTimeoutsRef = useRef<Map<string, number>>(new Map())

  const stopPolling = useCallback((fileId: string) => {
    const timeoutId = pollingTimeoutsRef.current.get(fileId)
    if (timeoutId) {
      window.clearTimeout(timeoutId)
      pollingTimeoutsRef.current.delete(fileId)
    }
  }, [])

  const updateFileInState = useCallback((nextFile: FileItem) => {
    setFiles((prev) => {
      const existingIndex = prev.findIndex((file) => file.id === nextFile.id)
      if (existingIndex === -1) return prev
      const next = [...prev]
      next[existingIndex] = { ...prev[existingIndex], ...nextFile }
      return next
    })
  }, [])

  const pollFileStatus = useCallback(async (fileId: string) => {
    try {
      const endpoint = config.fileEndpoints.fileStatus.replace(':fileId', fileId)
      const res = await fetch(endpoint)
      if (!res.ok) throw new Error(`Failed to fetch file status (${res.status})`)
      const data = await res.json()
      updateFileInState({
        id: data.file_id,
        original_name: data.original_name,
        file_type: data.file_type,
        size_bytes: 0,
        indexing_status: data.indexing_status,
        status_message: data.status_message,
        error_message: data.error_message,
        groundx_process_id: data.groundx_process_id,
        groundx_document_id: data.groundx_document_id,
        groundx_bucket_id: data.groundx_bucket_id,
        ready_for_groundx_retrieval: data.ready_for_groundx_retrieval,
        created_at: null,
      } as FileItem)

      if (data.indexing_status === 'queued' || data.indexing_status === 'processing') {
        stopPolling(fileId)
        const timeoutId = window.setTimeout(() => {
          void pollFileStatus(fileId)
        }, 3000)
        pollingTimeoutsRef.current.set(fileId, timeoutId)
        return
      }

      stopPolling(fileId)
    } catch {
      stopPolling(fileId)
    }
  }, [stopPolling, updateFileInState])

  const ensurePolling = useCallback((file: FileItem) => {
    if (file.file_type !== 'pdf') return
    if (file.indexing_status !== 'queued' && file.indexing_status !== 'processing') {
      stopPolling(file.id)
      return
    }
    if (pollingTimeoutsRef.current.has(file.id)) return
    const timeoutId = window.setTimeout(() => {
      void pollFileStatus(file.id)
    }, 1500)
    pollingTimeoutsRef.current.set(file.id, timeoutId)
  }, [pollFileStatus, stopPolling])

  const fetchFiles = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        type: activeFilter,
        sort: sortBy,
        limit: '100',
        offset: '0',
      })
      const res = await fetch(`${config.fileEndpoints.listFiles}?${params}`, { signal })
      if (!res.ok) throw new Error(`Failed to fetch files (${res.status})`)
      const data = await res.json()
      const nextFiles = data.files || []
      setFiles(nextFiles)
      setTotal(data.total || 0)
      nextFiles.forEach((file: FileItem) => ensurePolling(file))
    } catch (err: any) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [activeFilter, sortBy, ensurePolling])

  useEffect(() => {
    const controller = new AbortController()
    fetchFiles(controller.signal)
    return () => {
      controller.abort()
      pollingTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
      pollingTimeoutsRef.current.clear()
    }
  }, [fetchFiles])

  const handleDelete = async (fileId: string) => {
    if (!window.confirm('Delete this file? This action cannot be undone.')) return
    setDeletingId(fileId)
    try {
      const res = await fetch(config.fileEndpoints.deleteFile.replace(':fileId', String(fileId)), {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Delete failed')
      await fetchFiles()
    } catch {
      alert('Failed to delete file')
    } finally {
      setDeletingId(null)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files
    if (!selected || selected.length === 0) return
    setUploading(true)
    const fileList = Array.from(selected)
    try {
      for (const file of fileList) {
        setUploadProgress((prev) => new Map(prev).set(file.name, 0))
        const uploadResult = await uploadFileWithProgress(file, (percent) => {
          setUploadProgress((prev) => new Map(prev).set(file.name, percent))
        })
        await fetchFiles()
        if (uploadResult.file_id) {
          const uploadedFile = files.find((existing) => existing.id === uploadResult.file_id)
          ensurePolling(uploadedFile || {
            id: uploadResult.file_id,
            original_name: uploadResult.filename,
            file_type: uploadResult.file_type,
            size_bytes: uploadResult.size,
            indexing_status: uploadResult.indexing_status || 'queued',
            status_message: uploadResult.status_message,
            error_message: null,
            groundx_process_id: uploadResult.groundx_process_id,
            groundx_bucket_id: uploadResult.groundx_bucket_id,
            created_at: uploadResult.upload_timestamp.toISOString(),
          } as FileItem)
        }
        setUploadProgress((prev) => {
          const next = new Map(prev)
          next.delete(file.name)
          return next
        })
      }
    } catch (err: any) {
      alert(err.message || 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(new Map())
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="documents-tab">
      <div className="documents-toolbar">
        <div className="documents-filters">
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

        <div className="documents-actions">
          <select
            className="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
          >
            {SORT_OPTIONS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.mp3,.wav,.ogg,.m4a,.webm,.jpg,.jpeg,.png,.webp"
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

      {loading && (
        <div className="documents-loading">
          <RefreshCw size={32} className="spin" />
          <p>Loading documents...</p>
        </div>
      )}

      {error && !loading && (
        <div className="documents-error">
          <AlertCircle size={32} />
          <p>{error}</p>
          <button onClick={() => fetchFiles()}>Retry</button>
        </div>
      )}

      {uploadProgress.size > 0 && (
        <div className="upload-progress-section">
          {Array.from(uploadProgress.entries()).map(([name, percent]) => (
            <div key={name} className="upload-progress-card">
              <div className="upload-progress-info">
                <Upload size={16} />
                <span className="upload-progress-name" title={name}>{name}</span>
                <span className="upload-progress-percent">
                  {percent < 100 ? `Uploading... ${percent}%` : 'Processing'}
                </span>
              </div>
              <div className="upload-progress-bar-track">
                <div
                  className="upload-progress-bar-fill"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && files.length === 0 && uploadProgress.size === 0 && (
        <div className="documents-empty">
          <FolderOpen size={48} />
          <p>No documents yet. Upload your first PDF, audio, or image.</p>
        </div>
      )}

      {!loading && !error && files.length > 0 && (
        <>
          <p className="documents-count">{total} file{total !== 1 ? 's' : ''}</p>
          <div className="documents-grid">
            {files.map((file) => (
              <div key={file.id} className="file-card">
                <button
                  className="file-card-delete"
                  onClick={() => handleDelete(file.id)}
                  disabled={deletingId === file.id}
                  title="Delete file"
                >
                  <Trash2 size={14} />
                </button>
                <div className="file-card-icon">{getFileIcon(file.file_type)}</div>
                <div className="file-card-info">
                  <span className="file-card-name" title={file.original_name}>
                    {file.original_name}
                  </span>
                  <span className="file-card-meta">
                    {formatFileSize(file.size_bytes)} &middot; {formatDate(file.created_at)}
                  </span>
                </div>
                <span
                  className="file-card-status"
                  style={{ color: getStatusColor(file.indexing_status) }}
                >
                  {getStatusLabel(file)}
                </span>
                {file.error_message && file.indexing_status === 'failed' && (
                  <span className="file-card-meta">{file.error_message}</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
