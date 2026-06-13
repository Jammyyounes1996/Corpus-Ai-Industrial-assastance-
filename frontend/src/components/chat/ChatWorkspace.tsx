import { useState, useEffect, useRef, useMemo } from 'react'
import { Search, Camera, Mic, BookOpen, ArrowRight, Layers, Shield, Lightbulb } from 'lucide-react'
import { MessageList } from './MessageList'
import { InputBar } from './InputBar'
import { useChatStream } from '../../hooks/useChatStream'
import { useAttachments } from '../../hooks/useAttachments'
import type { ChatSession } from '../../types/chat'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'
import type { AnswerMode } from '../../types/api'
import corpusOrbWebm from '../../assets/corpus-orb.webm'
import './ChatWorkspace.css'

interface ChatWorkspaceProps {
  session: ChatSession | null
  sessions: UseChatSessionsReturn
  onTabChange?: (tabId: string) => void
}

export function ChatWorkspace({ session, sessions, onTabChange }: ChatWorkspaceProps) {
  const [answerMode, setAnswerMode] = useState<AnswerMode>("general")
  const attachments = useAttachments()

  const streamHandler = useMemo(
    () => (session ? sessions.createStreamEventHandler(session.id) : () => {}),
    [session?.id, sessions.createStreamEventHandler]
  )

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

  const pendingSendHandled = useRef<string | null>(null)

  useEffect(() => {
    if (!session?.pendingSend) return
    if (pendingSendHandled.current === session.id) return
    pendingSendHandled.current = session.id

    const pending = session.pendingSend
    sessions.updateSession(session.id, { pendingSend: undefined })
    sessions.createAssistantPlaceholder(session.id, '')

    const activeSession = sessions.sessions.find((s) => s.id === session.id)
    void send(activeSession?.backendChatId ?? null, {
      query: pending.query,
      attached_files: pending.attachedFileIds,
      task_type: pending.taskType,
    })
  }, [session?.id, session?.pendingSend, sessions, send])

  const handleSend = (text: string) => {
    if (!session) return

    const activeSession = sessions.sessions.find((s) => s.id === session.id)
    if (!activeSession) return

    const uploadedAttachments = attachments.files.filter((file) => file.status === 'uploaded' && file.backendFileId)

    sessions.appendUserMessage(session.id, text, uploadedAttachments.length > 0 ? uploadedAttachments : undefined)
    sessions.createAssistantPlaceholder(session.id, '')

    const uploadedFileIds = uploadedAttachments.map((file) => file.backendFileId as string)
    const attachedAnswerMode: AnswerMode = answerMode === 'groundx'
      ? 'groundx'
      : uploadedAttachments.some((file) => file.metadata.type.startsWith('audio/'))
      ? 'audio'
      : answerMode

    void send(activeSession.backendChatId ?? null, {
      query: text,
      attached_files: uploadedFileIds.length > 0 ? uploadedFileIds : undefined,
      answer_mode: attachedAnswerMode,
    })

    attachments.clearFiles()
  }

  const handleRegenerate = (assistantMessageId: string) => {
    if (!session || isStreaming) return
    const activeSession = sessions.sessions.find((s) => s.id === session.id)
    if (!activeSession) return

    const idx = activeSession.messages.findIndex((m) => m.id === assistantMessageId)
    if (idx < 0) return

    let query = ''
    for (let i = idx - 1; i >= 0; i--) {
      if (activeSession.messages[i].role === 'user') {
        query = activeSession.messages[i].content
        break
      }
    }
    if (!query.trim()) return

    sessions.createAssistantPlaceholder(session.id, '')
    void send(activeSession.backendChatId ?? null, { query })
  }

  const handleEditResend = (_messageId: string, newContent: string) => {
    if (!session || isStreaming) return
    handleSend(newContent)
  }

  const messages = session?.messages ?? []
  const hasNoMessages = messages.length === 0

  return (
    <div className="chat-workspace">
      {hasNoMessages ? (
        <div className="chat-workspace__empty">
          <div className="chat-workspace__orb-stage" aria-hidden="true">
            <video
              className="chat-workspace__orb-video"
              src={corpusOrbWebm}
              autoPlay
              loop
              muted
              playsInline
            />
          </div>
          <h2 className="chat-workspace__empty-title">CORPUS INDUSTRIAL AI AGENT</h2>
          <p className="chat-workspace__empty-subtitle">
            Use General, GroundX, Audio, and OCR workflows from one workspace.
          </p>
          <div className="chat-workspace__cards">
            <button
              type="button"
              className="chat-workspace__card chat-workspace__card--groundx"
              onClick={() => { setAnswerMode('groundx'); onTabChange?.('chat') }}
            >
              <div className="chat-workspace__card-icon">
                <Search size={20} />
              </div>
              <div className="chat-workspace__card-body">
                <span className="chat-workspace__card-title">GroundX Search</span>
                <span className="chat-workspace__card-desc">Search and analyze engineering data</span>
              </div>
              <ArrowRight size={16} className="chat-workspace__card-arrow" />
            </button>
            <button
              type="button"
              className="chat-workspace__card chat-workspace__card--ocr"
              onClick={() => onTabChange?.('ocr')}
            >
              <div className="chat-workspace__card-icon">
                <Camera size={20} />
              </div>
              <div className="chat-workspace__card-body">
                <span className="chat-workspace__card-title">OCR Extract</span>
                <span className="chat-workspace__card-desc">Extract text and tables from documents</span>
              </div>
              <ArrowRight size={16} className="chat-workspace__card-arrow" />
            </button>
            <button
              type="button"
              className="chat-workspace__card chat-workspace__card--audio"
              onClick={() => onTabChange?.('tools')}
            >
              <div className="chat-workspace__card-icon">
                <Mic size={20} />
              </div>
              <div className="chat-workspace__card-body">
                <span className="chat-workspace__card-title">Audio Analyze</span>
                <span className="chat-workspace__card-desc">Transcribe and analyze audio files</span>
              </div>
              <ArrowRight size={16} className="chat-workspace__card-arrow" />
            </button>
            <button
              type="button"
              className="chat-workspace__card chat-workspace__card--documents"
              onClick={() => onTabChange?.('documents')}
            >
              <div className="chat-workspace__card-icon">
                <BookOpen size={20} />
              </div>
              <div className="chat-workspace__card-body">
                <span className="chat-workspace__card-title">Browse Documents</span>
                <span className="chat-workspace__card-desc">Explore your knowledge base</span>
              </div>
              <ArrowRight size={16} className="chat-workspace__card-arrow" />
            </button>
          </div>
          <div className="chat-workspace__features">
            <div className="chat-workspace__feature chat-workspace__feature--workflows">
              <div className="chat-workspace__feature-icon">
                <Layers size={20} />
              </div>
              <div className="chat-workspace__feature-body">
                <span className="chat-workspace__feature-title">Unified Workflows</span>
                <span className="chat-workspace__feature-desc">Combine General, GroundX, Audio, and OCR capabilities in one conversation.</span>
              </div>
              <span className="chat-workspace__feature-link">Learn more →</span>
            </div>
            <div className="chat-workspace__feature chat-workspace__feature--enterprise">
              <div className="chat-workspace__feature-icon">
                <Shield size={20} />
              </div>
              <div className="chat-workspace__feature-body">
                <span className="chat-workspace__feature-title">Enterprise Ready</span>
                <span className="chat-workspace__feature-desc">Secure, local-first workflows built for industrial engineering environments.</span>
              </div>
              <span className="chat-workspace__feature-link">Learn more →</span>
            </div>
            <div className="chat-workspace__feature chat-workspace__feature--insights">
              <div className="chat-workspace__feature-icon">
                <Lightbulb size={20} />
              </div>
              <div className="chat-workspace__feature-body">
                <span className="chat-workspace__feature-title">Actionable Insights</span>
                <span className="chat-workspace__feature-desc">Turn complex technical data into clear, useful engineering decisions.</span>
              </div>
              <span className="chat-workspace__feature-link">Learn more →</span>
            </div>
          </div>
        </div>
      ) : (
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          onRegenerate={handleRegenerate}
          onEditUserMessage={handleEditResend}
        />
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
