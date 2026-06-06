import './AudioTranscriber.css'
import { useState, useEffect, useCallback } from 'react'
import { Mic, Copy, Check, ChevronDown, ChevronRight, AlertCircle } from 'lucide-react'
import { config } from '../../config'
import type { FileItem } from '../../types/files'

function formatDuration(seconds: number | null): string {
  if (seconds === null) return 'Unknown'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function AudioTranscriber() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const fetchAudioFiles = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ type: 'audio', limit: '100', offset: '0' })
      const res = await fetch(`${config.fileEndpoints.listFiles}?${params}`, { signal })
      if (!res.ok) throw new Error('Failed to fetch audio files')
      const data = await res.json()
      setFiles(data.files || [])
    } catch (err: any) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err.message || 'Failed to load audio files')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchAudioFiles(controller.signal)
    return () => controller.abort()
  }, [fetchAudioFiles])

  const handleCopy = async (fileId: number, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(fileId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      // clipboard API may fail in some contexts
    }
  }

  return (
    <div className="tools-audio">
      {loading && (
        <div className="tools-audio__loading">
          <div className="tools-tab__spinner" />
          <p>Loading audio files...</p>
        </div>
      )}

      {error && (
        <div className="tools-audio__error">
          <AlertCircle size={32} />
          <p>{error}</p>
          <button className="tools-audio__retry" onClick={() => fetchAudioFiles()}>Retry</button>
        </div>
      )}

      {!loading && !error && files.length === 0 && (
        <div className="tools-audio__empty">
          <Mic size={48} />
          <h3>No audio transcriptions yet</h3>
          <p>Upload an audio file in the Documents tab to get started.</p>
        </div>
      )}

      {!loading && !error && files.length > 0 && (
        <div className="tools-audio__list">
          {files.map((file) => {
            const isExpanded = expandedId === file.id
            const transcriptText = file.transcript_summary?.text || null

            return (
              <div key={file.id} className="tools-audio__item">
                <button
                  className="tools-audio__item-header"
                  onClick={() => setExpandedId(isExpanded ? null : file.id)}
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <Mic size={16} className="tools-audio__item-icon" />
                  <span className="tools-audio__item-name">{file.original_name}</span>
                  {file.transcript_summary && (
                    <span className="tools-audio__item-duration">
                      {formatDuration(file.transcript_summary.duration_seconds)}
                    </span>
                  )}
                  {file.transcript_summary?.language && (
                    <span className="tools-audio__item-lang">
                      {file.transcript_summary.language}
                    </span>
                  )}
                  <span className="tools-audio__item-date">{formatDate(file.created_at)}</span>
                </button>

                {isExpanded && (
                  <div className="tools-audio__item-body">
                    {file.indexing_status === 'indexed' ? (
                      <>
                        <div className="tools-audio__transcript">
                          {transcriptText ? (
                            <pre className="tools-audio__transcript-text">{transcriptText}</pre>
                          ) : (
                            <p className="tools-audio__transcript-placeholder">
                              No transcript text available. Use the Chat tab to ask questions about this audio content.
                            </p>
                          )}
                        </div>
                        {transcriptText && (
                          <button
                            className="tools-audio__copy-btn"
                            onClick={() => handleCopy(file.id, transcriptText)}
                          >
                            {copiedId === file.id ? <Check size={14} /> : <Copy size={14} />}
                            {copiedId === file.id ? 'Copied!' : 'Copy transcript'}
                          </button>
                        )}
                      </>
                    ) : (
                      <p className="tools-audio__transcript-status">
                        Status: {file.indexing_status}
                        {file.error_message && ` \u2014 ${file.error_message}`}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
