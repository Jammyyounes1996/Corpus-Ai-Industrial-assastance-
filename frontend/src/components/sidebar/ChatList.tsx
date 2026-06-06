import type { ChatSession } from '../../types/chat'
import './ChatList.css'

interface ChatListProps {
  sessions: ChatSession[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  className?: string
}

export function ChatList({ sessions, activeSessionId, onSelectSession, className = '' }: ChatListProps) {
  const handleChatClick = (sessionId: string) => {
    onSelectSession(sessionId)
  }

  // Format date for display
  const formatDate = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - new Date(date).getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    
    return new Date(date).toLocaleDateString()
  }

  // Get message preview
  const getMessagePreview = (session: ChatSession) => {
    if (session.messages.length === 0) return 'No messages yet'
    
    const lastMessage = session.messages[session.messages.length - 1]
    const preview = lastMessage.content.length > 80 
      ? lastMessage.content.substring(0, 80) + '...' 
      : lastMessage.content
    
    return preview
  }

  if (sessions.length === 0) {
    return (
      <div className={`empty-state ${className}`}>
        <div className="empty-state-icon">💬</div>
        <div className="empty-state-title">No conversations yet</div>
        <div className="empty-state-description">
          Start a new chat to begin your conversation with the AI assistant.
        </div>
      </div>
    )
  }

  return (
    <div className={`chat-list ${className}`}>
      {sessions.map(session => (
        <div
          key={session.id}
          className={`chat-item ${session.id === activeSessionId ? 'active' : ''}`}
          onClick={() => handleChatClick(session.id)}
          role="button"
          tabIndex={0}
          aria-current={session.id === activeSessionId ? 'page' : undefined}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              handleChatClick(session.id)
            }
          }}
        >
          <div className="chat-item-content">
            <div className="chat-title">{session.title}</div>
            <div className="chat-time">{formatDate(session.updatedAt)}</div>
            <div className="chat-preview">{getMessagePreview(session)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}