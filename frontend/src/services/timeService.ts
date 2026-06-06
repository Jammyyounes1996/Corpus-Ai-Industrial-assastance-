/* Time Service */
/*
  Utility functions for time formatting and generation
  Used for chat titles and timestamps
*/

// No external date library needed - using native Date methods

export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  })
}

export function formatFullTimestamp(date: Date): string {
  return date.toLocaleDateString('en-US', { 
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false 
  })
}

export function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMinutes < 1) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  
  return formatFullTimestamp(date)
}

export function generateChatTitle(message: string): string {
  const trimmed = message.trim()
  
  if (!trimmed) {
    return 'New chat'
  }
  
  // Take first 50 characters and trim to last word boundary
  const truncated = trimmed.length > 50 ? trimmed.substring(0, 50) : trimmed
  
  // Try to end at word boundary
  const lastSpace = truncated.lastIndexOf(' ')
  const finalText = lastSpace > 30 ? truncated.substring(0, lastSpace) : truncated
  
  return finalText || 'New chat'
}

export function getChatCreatedAtTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  })
}