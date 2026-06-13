import { useState } from 'react'
import { User, File, Image, Music, Pencil, Check, X } from 'lucide-react'
import type { Message } from '../../types/chat'
import { formatTimestamp } from '../../services/timeService'
import { getTextDirection } from '../../utils/textDirection'
import './UserMessageCard.css'

interface UserMessageCardProps {
  message: Message
  onEditResend?: (messageId: string, newContent: string) => void
}

const USER_AVATAR_URL = `${import.meta.env.BASE_URL}assets/mohamed-ali-avatar.png`

function AttachmentChip({ name, type }: { name: string; type?: string }) {
  const getIcon = () => {
    if (type?.startsWith('image/')) return <Image size={12} />
    if (type?.startsWith('audio/')) return <Music size={12} />
    return <File size={12} />
  }

  return (
    <span className="user-msg__chip" title={name}>
      {getIcon()}
      <span className="user-msg__chip-name">{name}</span>
    </span>
  )
}

export function UserMessageCard({ message, onEditResend }: UserMessageCardProps) {
  const [avatarFailed, setAvatarFailed] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState(message.content)

  const dir = getTextDirection(message.content)

  const startEdit = () => {
    setDraft(message.content)
    setIsEditing(true)
  }

  const cancelEdit = () => {
    setIsEditing(false)
    setDraft(message.content)
  }

  const saveEdit = () => {
    const trimmed = draft.trim()
    if (!trimmed || !onEditResend || trimmed === message.content) {
      setIsEditing(false)
      return
    }
    setIsEditing(false)
    onEditResend(message.id, trimmed)
  }

  return (
    <div className="user-msg" role="article" aria-label={`User message at ${formatTimestamp(message.timestamp)}`}>
      <div className="user-msg__avatar" aria-hidden="true">
        {avatarFailed ? (
          <User size={16} />
        ) : (
          <img
            className="user-msg__avatar-img"
            src={USER_AVATAR_URL}
            alt="Mohamed Ali"
            onError={() => setAvatarFailed(true)}
          />
        )}
      </div>
      <div className="user-msg__body">
        <div className="user-msg__meta">
          <span className="user-msg__role">Mohamed Ali</span>
          <time className="user-msg__time" dateTime={message.timestamp.toISOString()}>
            {formatTimestamp(message.timestamp)}
          </time>
          {!isEditing && onEditResend && (
            <button
              type="button"
              className="user-msg__edit-btn"
              onClick={startEdit}
              aria-label="Edit message"
              title="Edit"
            >
              <Pencil size={12} />
              <span className="user-msg__edit-label">Edit</span>
            </button>
          )}
        </div>

        {isEditing ? (
          <div className="user-msg__edit">
            <textarea
              className="user-msg__edit-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              dir={getTextDirection(draft)}
              rows={2}
              autoFocus
              aria-label="Edit message content"
            />
            <div className="user-msg__edit-actions">
              <button type="button" className="user-msg__edit-save" onClick={saveEdit}>
                <Check size={12} />
                <span>Save &amp; Resend</span>
              </button>
              <button type="button" className="user-msg__edit-cancel" onClick={cancelEdit}>
                <X size={12} />
                <span>Cancel</span>
              </button>
            </div>
          </div>
        ) : (
          <div className={`user-msg__content user-msg__content--${dir}`} dir={dir}>
            {message.content}
          </div>
        )}

        {message.attachments && message.attachments.length > 0 && (
          <div className="user-msg__chips">
            {message.attachments.map((att) => (
              <AttachmentChip
                key={att.id}
                name={att.metadata.name}
                type={att.metadata.type}
              />
            ))}
          </div>
        )}
        {message.status === 'failed' && message.error && (
          <div className="user-msg__error" role="alert">
            {message.error}
          </div>
        )}
      </div>
    </div>
  )
}
