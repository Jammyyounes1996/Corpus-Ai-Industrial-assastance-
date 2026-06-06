/* Message Mutation Helpers */
/*
  Additional utilities for message state management
  Complements useChatSessions hook with specialized operations
*/

import { Message, ThinkingStep, SourceReference } from '../types/chat'
import { AttachedFile } from '../types/attachments'

export function createEmptyUserMessage(content: string): Message {
  return {
    id: `msg-${Date.now()}-user`,
    role: 'user',
    content,
    timestamp: new Date(),
    status: 'complete'
  }
}

export function createStreamingAssistantMessage(content: string): Message {
  return {
    id: `msg-${Date.now()}-assistant`,
    role: 'assistant',
    content,
    timestamp: new Date(),
    status: 'streaming'
  }
}

export function createThinkingStep(
  type: 'reasoning' | 'planning' | 'coding' | 'review',
  content: string
): ThinkingStep {
  return {
    id: `step-${Date.now()}`,
    type,
    content,
    timestamp: new Date(),
    status: 'received'
  }
}

export function createSourceReference(
  file_id: string,
  filename: string,
  file_type: 'pdf' | 'image' | 'audio',
  chunk_index: number,
  excerpt: string,
  score?: number
): SourceReference {
  return {
    file_id,
    filename,
    file_type,
    chunk_index,
    excerpt,
    score
  }
}

export function updateMessageStatus(
  message: Message,
  status: Message['status']
): Message {
  return {
    ...message,
    status,
    timestamp: new Date()
  }
}

export function appendMessageContent(message: Message, content: string): Message {
  return {
    ...message,
    content: message.content + content,
    timestamp: new Date()
  }
}

export function addMessageAttachment(message: Message, attachment: AttachedFile): Message {
  return {
    ...message,
    attachments: [...(message.attachments || []), attachment],
    timestamp: new Date()
  }
}

export function replaceMessageSources(message: Message, sources: SourceReference[]): Message {
  return {
    ...message,
    sources,
    timestamp: new Date()
  }
}

export function setThinkingSteps(message: Message, steps: ThinkingStep[]): Message {
  return {
    ...message,
    thinkingSteps: steps,
    timestamp: new Date()
  }
}

export function completeMessage(message: Message): Message {
  return updateMessageStatus(message, 'complete')
}

export function failMessage(message: Message, error?: string): Message {
  return {
    ...message,
    status: 'failed',
    error,
    timestamp: new Date()
  }
}

export function cancelMessage(message: Message): Message {
  return updateMessageStatus(message, 'cancelled')
}