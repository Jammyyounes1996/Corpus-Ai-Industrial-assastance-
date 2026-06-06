import { useState } from 'react'
import { FileText, FileImage, FileAudio, File } from 'lucide-react'
import type { SourceReference } from '../../types/chat'
import './SourceChips.css'

const VISIBLE_LIMIT = 3

function getFileIcon(fileType: SourceReference['file_type']) {
  switch (fileType) {
    case 'pdf':
    case 'text':
      return <FileText size={14} />
    case 'image':
      return <FileImage size={14} />
    case 'audio':
      return <FileAudio size={14} />
    default:
      return <File size={14} />
  }
}

function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`
}

interface SourceChipProps {
  source: SourceReference
}

function SourceChip({ source }: SourceChipProps) {
  return (
    <div
      className="source-chip"
      role="listitem"
      title={source.excerpt || source.filename}
      tabIndex={0}
    >
      <span className="source-chip__icon" aria-hidden="true">
        {getFileIcon(source.file_type)}
      </span>
      <span className="source-chip__name">{source.filename}</span>
      {source.score != null && (
        <span className="source-chip__score">{formatScore(source.score)}</span>
      )}
    </div>
  )
}

interface SourceChipsProps {
  sources: SourceReference[]
}

export function SourceChips({ sources }: SourceChipsProps) {
  const [expanded, setExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  const visibleSources = expanded ? sources : sources.slice(0, VISIBLE_LIMIT)
  const hiddenCount = sources.length - VISIBLE_LIMIT

  return (
    <div className="source-chips" role="list" aria-label="Sources">
      {visibleSources.map((source) => (
        <SourceChip key={`${source.file_id}-${source.chunk_index}`} source={source} />
      ))}
      {!expanded && hiddenCount > 0 && (
        <button
          className="source-chip source-chip--more"
          onClick={() => setExpanded(true)}
          aria-label={`Show ${hiddenCount} more sources`}
          type="button"
        >
          +{hiddenCount} more
        </button>
      )}
      {expanded && sources.length > VISIBLE_LIMIT && (
        <button
          className="source-chip source-chip--less"
          onClick={() => setExpanded(false)}
          aria-label="Show fewer sources"
          type="button"
        >
          Show less
        </button>
      )}
    </div>
  )
}
