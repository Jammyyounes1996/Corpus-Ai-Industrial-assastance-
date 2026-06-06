import { useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import { useChatStream } from '../../hooks/useChatStream'
import { useAttachments } from '../../hooks/useAttachments'
import type { ChatSession } from '../../types/chat'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'
import type { AnswerMode } from '../../types/api'
import './ChatWorkspace.css'

interface ChatWorkspaceProps {
  session: ChatSession | null
  sessions: UseChatSessionsReturn
}

export function ChatWorkspace({ session, sessions }: ChatWorkspaceProps) {
  const [answerMode, setAnswerMode] = useState<AnswerMode>("general")
  const attachments = useAttachments()

  const streamHandler = session
    ? sessions.createStreamEventHandler(session.id)
    : () => {}

  const { isStreaming, send, cancel, error, canRetry, retryLast, clearError } = useChatStream({
    onEvent: streamHandler,
    onBackendChatCreated: (backendChatId: string) => {
      if (session) {
        sessions.updateSession(session.id, { backendChatId })
      }
    },
    onCancel: () => {
      if (session) {
        sessions.cancelStreamingMessage(session.id)
      }
    },
  })

  const handleSend = (text: string) => {
    if (!session) return

    const activeSession = sessions.sessions.find((s) => s.id === session.id)
    if (!activeSession) return

    sessions.appendUserMessage(session.id, text, attachments.files.length > 0 ? attachments.files : undefined)
    sessions.createAssistantPlaceholder(session.id, '')

    const uploadedFileIds = attachments.uploadedFiles.map((f) => f.file_id)

    void send(activeSession.backendChatId ?? null, {
      query: text,
      attached_files: uploadedFileIds.length > 0 ? uploadedFileIds : undefined,
      answer_mode: answerMode,
    })

    attachments.clearFiles()
  }

  const messages = session?.messages ?? []
  const hasNoMessages = messages.length === 0

  return (
    <div className="chat-workspace">
      {hasNoMessages ? (
        <div className="chat-workspace__empty">
          <MessageSquare size={40} className="chat-workspace__empty-icon" />
          <h2 className="chat-workspace__empty-title">CORPUS</h2>
          <p className="chat-workspace__empty-subtitle">
            Ask questions about your uploaded documents, manuals, and knowledge sources.
          </p>
        </div>
      ) : (
        <MessageList messages={messages} isStreaming={isStreaming} />
      )}

      <InputBar
        onSend={handleSend}
        onCancel={cancel}
        isStreaming={isStreaming}
        disabled={!session}
        answerMode={answerMode}
        onAnswerModeChange={setAnswerMode}
        onAttachFiles={attachments.addFiles}
        onRemoveAttachment={attachments.removeFile}
        onRetryAttachment={attachments.retryFile}
        validateAttachmentFiles={attachments.validateFiles}
        canAddMoreFiles={attachments.canAddMoreFiles}
        attachments={attachments.files}
        failedAttachments={attachments.failedFiles}
        errorText={error}
        onRetrySend={() => {
          void retryLast()
        }}
        canRetrySend={canRetry}
        onDismissError={clearError}
      />
    </div>
  )
}
