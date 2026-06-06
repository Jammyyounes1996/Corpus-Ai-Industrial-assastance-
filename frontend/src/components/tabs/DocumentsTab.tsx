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
import { uploadFile } from '../../services/fileUploadService'

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
    case 'processing':
      return 'var(--color-warning)'
    case 'failed':
      return 'var(--color-error)'
    default:
      return 'var(--text-muted)'
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
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
      setFiles(data.files || [])
      setTotal(data.total || 0)
    } catch (err: any) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [activeFilter, sortBy])

  useEffect(() => {
    const controller = new AbortController()
    fetchFiles(controller.signal)
    return () => controller.abort()
  }, [fetchFiles])

  const handleDelete = async (fileId: number) => {
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
    try {
      for (const file of Array.from(selected)) {
        await uploadFile(file)
      }
      await fetchFiles()
    } catch (err: any) {
      alert(err.message || 'Upload failed')
    } finally {
      setUploading(false)
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
            accept=".pdf,.mp3,.wav,.ogg,.jpg,.jpeg,.png,.webp"
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

      {!loading && !error && files.length === 0 && (
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
                  {file.indexing_status}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
