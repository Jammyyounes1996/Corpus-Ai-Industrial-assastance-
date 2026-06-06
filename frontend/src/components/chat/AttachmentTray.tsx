/* Attachment Tray Component */
/*
  Displays selected files with upload status, thumbnails, and controls
*/

import React from 'react'
import { X, Upload, File, Image, Music, AlertCircle, CheckCircle } from 'lucide-react'
import { AttachedFile } from '../../types/attachments'
import './AttachmentTray.css'

interface AttachmentTrayProps {
  className?: string
  files: AttachedFile[]
  failedFiles: AttachedFile[]
  onRemove: (id: string) => void
  onRetry: (id: string) => void
}

function getFileIcon(file: File): React.ReactNode {
  const type = file.type
  if (type.startsWith('image/')) {
    return <Image size={16} className="file-icon image" />
  } else if (type.startsWith('audio/')) {
    return <Music size={16} className="file-icon audio" />
  } else {
    return <File size={16} className="file-icon pdf" />
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${Math.round(bytes / (1024 * 1024))} MB`
}

function AttachmentFile({ file, onRemove, onRetry }: {
  file: AttachedFile
  onRemove: (id: string) => void
  onRetry: (id: string) => void
}) {
  const getStatusIcon = () => {
    switch (file.status) {
      case 'uploaded':
        return <CheckCircle size={16} className="status-icon uploaded" />
      case 'failed':
        return <AlertCircle size={16} className="status-icon failed" />
      case 'uploading':
        return <Upload size={16} className="status-icon uploading" />
      default:
        return null
    }
  }

  const getStatusText = () => {
    switch (file.status) {
      case 'uploaded':
        return 'Uploaded'
      case 'failed':
        return file.error || 'Failed'
      case 'uploading':
        return `${file.progress}%`
      default:
        return 'Pending'
    }
  }

  return (
    <div className={`attachment-file ${file.status}`}>
      <div className="file-preview">
        {file.file.type.startsWith('image/') ? (
          <img 
            src={file.objectUrl} 
            alt={file.file.name}
            className="file-thumbnail"
          />
        ) : (
          getFileIcon(file.file)
        )}
      </div>
      
      <div className="file-info">
        <div className="file-name" title={file.file.name}>
          {file.file.name}
        </div>
        <div className="file-meta">
          <span className="file-size">{formatFileSize(file.file.size)}</span>
          <span className="file-status">Status: {getStatusText()}</span>
        </div>
      </div>
      
      <div className="file-actions">
        {getStatusIcon()}
        {file.status === 'failed' ? (
          <button
            type="button"
            onClick={() => onRetry(file.id)}
            className="retry-button"
            aria-label={`Retry upload for ${file.file.name}`}
          >
            Retry
          </button>
        ) : null}
        <button 
          type="button"
          onClick={() => onRemove(file.id)}
          className="remove-button"
          aria-label={`Remove ${file.file.name}`}
        >
          <X size={16} />
        </button>
      </div>
    </div>
  )
}

export function AttachmentTray({ className = '', files, failedFiles, onRemove, onRetry }: AttachmentTrayProps) {

  const visibleFiles = files.filter(file => file.status !== 'removed')

  if (visibleFiles.length === 0) {
    return null
  }

  return (
    <div className={`attachment-tray ${className}`}>
      <div className="attachment-header">
        <h3 className="attachment-title">
          Files ({visibleFiles.length})
          {failedFiles.length > 0 && (
            <span className="failed-count">
              ({failedFiles.length} failed)
            </span>
          )}
        </h3>
      </div>
      
      <div className="attachment-list">
        {visibleFiles.map(file => (
          <AttachmentFile 
            key={file.id} 
            file={file} 
            onRemove={onRemove}
            onRetry={onRetry}
          />
        ))}
      </div>
      
      {failedFiles.length > 0 && (
        <div className="upload-errors">
          <div className="error-summary">
            <AlertCircle size={14} />
            <span>Some files failed to upload. Please remove or retry them.</span>
          </div>
        </div>
      )}
    </div>
  )
}
