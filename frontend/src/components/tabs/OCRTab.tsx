import './OCRTab.css'
import { useState, useEffect, useCallback } from 'react'
import { Camera, AlertCircle, MessageCircle } from 'lucide-react'
import { config } from '../../config'
import type { FileItem } from '../../types/files'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'

interface OCRTabProps {
  sessions: UseChatSessionsReturn
  onTabChange: (tabId: string) => void
}

export function OCRTab({ sessions, onTabChange }: OCRTabProps) {
  const [files, setFiles] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchImages = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ type: 'image', sort: 'date_desc', limit: '100', offset: '0' })
      const res = await fetch(`${config.fileEndpoints.listFiles}?${params}`, { signal })
      if (!res.ok) throw new Error(`Failed to fetch images (${res.status})`)
      const data = await res.json()
      setFiles(data.files || [])
    } catch (err: any) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err.message || 'Failed to load images')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchImages(controller.signal)
    return () => controller.abort()
  }, [fetchImages])

  const handleOpenInChat = (file: FileItem) => {
    const session = sessions.createNewSession()
    sessions.appendUserMessage(session.id, `Tell me about this image: ${file.original_name}`)
    onTabChange('chat')
  }

  if (loading) {
    return (
      <div className="ocr-loading">
        <Camera size={32} className="spin" />
        <p>Loading images...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="ocr-error">
        <AlertCircle size={32} />
        <p>{error}</p>
        <button onClick={() => fetchImages()}>Retry</button>
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="ocr-empty">
        <Camera size={48} />
        <p>No images analyzed yet. Upload an image to get started.</p>
      </div>
    )
  }

  return (
    <div className="ocr-tab">
      <div className="ocr-grid">
        {files.map((file) => (
          <div
            key={file.id}
            className="ocr-card"
            onClick={() => handleOpenInChat(file)}
          >
            <img
              src={config.fileEndpoints.fileContent.replace(':fileId', String(file.id))}
              alt={file.original_name}
              className="ocr-thumbnail"
              loading="lazy"
            />
            <span className="ocr-filename">{file.original_name}</span>
            <div className="ocr-overlay">
              <MessageCircle size={20} />
              <span>Open in Chat</span>
            </div>
            {file.ocr_summary && (
              <div className="ocr-tooltip" title={file.ocr_summary.text_preview}>
                {file.ocr_summary.text_preview}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
