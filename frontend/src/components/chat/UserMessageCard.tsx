import { User } from 'lucide-react'
import { File, Image, Music } from 'lucide-react'
import type { Message } from '../../types/chat'
import { formatTimestamp } from '../../services/timeService'
import './UserMessageCard.css'

interface UserMessageCardProps {
  message: Message
}

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

export function UserMessageCard({ message }: UserMessageCardProps) {
  return (
    <div className="user-msg" role="article" aria-label={`User message at ${formatTimestamp(message.timestamp)}`}>
      <div className="user-msg__avatar" aria-hidden="true">
        <User size={16} />
      </div>
      <div className="user-msg__body">
        <div className="user-msg__meta">
          <span className="user-msg__role">You</span>
          <time className="user-msg__time" dateTime={message.timestamp.toISOString()}>
            {formatTimestamp(message.timestamp)}
          </time>
        </div>
        <div className="user-msg__content">{message.content}</div>
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
