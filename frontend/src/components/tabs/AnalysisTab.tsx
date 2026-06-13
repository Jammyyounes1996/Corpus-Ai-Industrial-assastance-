import './AnalysisTab.css'
import { useState, useEffect, useCallback } from 'react'
import { BarChart, AlertCircle, Clock, FileText, ChevronDown, ChevronRight, Search, Code } from 'lucide-react'
import type { ChatSession } from '../../types/chat'

interface ThinkingStepRaw {
  step: string
  status: string
  node: string
  duration_ms: number | null
}

interface RetrievedContextRaw {
  file_id: string
  filename: string
  file_type: string
  chunk_index: number
  score: number
  excerpt: string
}

interface BackendMessage {
  id: string
  role: string
  content: string
  thinking_steps: string | null
  retrieved_context: string | null
  created_at: string | null
}

interface ChatDetailResponse {
  model_name: string
  model_provider: string
  messages: BackendMessage[]
}

interface AnalysisTabProps {
  activeSession: ChatSession | null
}

export function AnalysisTab({ activeSession }: AnalysisTabProps) {
  const [chatData, setChatData] = useState<ChatDetailResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)

  const fetchChatDetail = useCallback(async (signal?: AbortSignal) => {
    if (!activeSession?.backendChatId) {
      setChatData(null)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/chat/${activeSession.backendChatId}`, { signal })
      if (!res.ok) throw new Error(`Failed to fetch chat (${res.status})`)
      const data: ChatDetailResponse = await res.json()
      setChatData(data)
    } catch (err: any) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err.message || 'Failed to load analysis')
    } finally {
      setLoading(false)
    }
  }, [activeSession?.backendChatId])

  useEffect(() => {
    const controller = new AbortController()
    fetchChatDetail(controller.signal)
    return () => controller.abort()
  }, [fetchChatDetail])

  if (!activeSession) {
    return (
      <div className="analysis-tab analysis-tab--empty">
        <div className="analysis-tab__empty-icon">
          <BarChart size={48} strokeWidth={1.5} />
        </div>
        <h3>No active conversation</h3>
        <p>Start a conversation to see analysis</p>
      </div>
    )
  }

  if (!activeSession.backendChatId) {
    return (
      <div className="analysis-tab analysis-tab--empty">
        <div className="analysis-tab__empty-icon">
          <BarChart size={48} strokeWidth={1.5} />
        </div>
        <h3>Send a message first</h3>
        <p>Send a message in chat to generate analysis data</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="analysis-tab analysis-tab--loading">
        <div className="analysis-tab__spinner" />
        <p>Loading analysis...</p>
      </div>
    )
  }

  const lastSessionAssistantMsg = [...activeSession.messages]
    .reverse()
    .find(m => m.role === 'assistant')

  if (error && !lastSessionAssistantMsg) {
    return (
      <div className="analysis-tab analysis-tab--error">
        <AlertCircle size={24} />
        <p>{error}</p>
        <button className="analysis-tab__retry" onClick={() => fetchChatDetail()}>Retry</button>
      </div>
    )
  }

  if (!chatData && !lastSessionAssistantMsg) return null

  const lastAssistantMsg = chatData ? [...chatData.messages]
    .reverse()
    .find(m => m.role === 'assistant') : null
  const usage = lastSessionAssistantMsg?.usage

  if (!lastAssistantMsg && !lastSessionAssistantMsg) {
    return (
      <div className="analysis-tab analysis-tab--empty">
        <div className="analysis-tab__empty-icon">
          <BarChart size={48} strokeWidth={1.5} />
        </div>
        <h3>No assistant response yet</h3>
        <p>Wait for the AI to respond to see analysis</p>
      </div>
    )
  }

  let thinkingSteps: ThinkingStepRaw[] = []
  try {
    thinkingSteps = lastAssistantMsg?.thinking_steps
      ? JSON.parse(lastAssistantMsg.thinking_steps)
      : []
  } catch { thinkingSteps = [] }

  let retrievedContext: RetrievedContextRaw[] = []
  try {
    retrievedContext = lastAssistantMsg?.retrieved_context
      ? JSON.parse(lastAssistantMsg.retrieved_context)
      : []
  } catch { retrievedContext = [] }

  const modelName = chatData?.model_name || 'Unknown'
  const modelDisplay = modelName.includes('/') ? modelName.split('/').pop()! : modelName
  const assistantContent = lastAssistantMsg?.content ?? lastSessionAssistantMsg?.content ?? ''

  return (
    <div className="analysis-tab">
      <div className="analysis-tab__header">
        <h2 className="analysis-tab__title">
          <BarChart size={20} />
          Response Analysis
        </h2>
        <span className="analysis-tab__model-badge">{modelDisplay}</span>
      </div>

      <div className="analysis-tab__sections">
        <section className="analysis-section">
          <h3 className="analysis-section__title">
            <Clock size={16} />
            Thinking Steps
            <span className="analysis-section__count">{thinkingSteps.length}</span>
          </h3>
          {thinkingSteps.length === 0 ? (
            <p className="analysis-section__empty">No thinking steps recorded for this response.</p>
          ) : (
            <div className="analysis-timeline">
              {thinkingSteps.map((step, idx) => (
                <div
                  key={idx}
                  className={`analysis-timeline__node analysis-timeline__node--${step.status}`}
                >
                  <div className="analysis-timeline__connector">
                    <span className="analysis-timeline__dot" />
                    {idx < thinkingSteps.length - 1 && <span className="analysis-timeline__line" />}
                  </div>
                  <div className="analysis-timeline__content">
                    <button
                      className="analysis-timeline__step-header"
                      onClick={() => setExpandedStep(expandedStep === `${idx}` ? null : `${idx}`)}
                    >
                      <span className="analysis-timeline__step-text">{step.step}</span>
                      <div className="analysis-timeline__meta">
                        {step.duration_ms !== null && (
                          <span className="analysis-timeline__duration">{step.duration_ms}ms</span>
                        )}
                        <span className={`analysis-timeline__status analysis-timeline__status--${step.status}`}>
                          {step.status}
                        </span>
                        {expandedStep === `${idx}` ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </div>
                    </button>
                    {expandedStep === `${idx}` && (
                      <div className="analysis-timeline__detail">
                        <span className="analysis-timeline__node-name">Node: {step.node}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="analysis-section">
          <h3 className="analysis-section__title">
            <Search size={16} />
            Retrieved Context
            <span className="analysis-section__count">{retrievedContext.length}</span>
          </h3>
          {retrievedContext.length === 0 ? (
            <p className="analysis-section__empty">No context was retrieved for this response.</p>
          ) : (
            <div className="analysis-sources">
              {retrievedContext.map((ctx, idx) => (
                <div key={idx} className="analysis-source-card">
                  <div className="analysis-source-card__header">
                    <FileText size={14} />
                    <span className="analysis-source-card__filename">{ctx.filename}</span>
                    <span className="analysis-source-card__type">{ctx.file_type}</span>
                  </div>
                  <div className="analysis-source-card__meta">
                    <span className="analysis-source-card__chunk">Chunk #{ctx.chunk_index}</span>
                    <span className="analysis-source-card__score">
                      Score: {(ctx.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="analysis-source-card__excerpt">"{ctx.excerpt}"</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="analysis-section">
          <h3 className="analysis-section__title">
            <Code size={16} />
            {modelDisplay} Reasoning Output
          </h3>
          <div className="analysis-reasoning__meta">
            <span className="analysis-reasoning__stat">Prompt tokens: {usage?.prompt_tokens ?? '—'}</span>
            <span className="analysis-reasoning__stat">Completion tokens: {usage?.completion_tokens ?? '—'}</span>
            <span className="analysis-reasoning__stat">Total tokens: {usage?.total_tokens ?? '—'}</span>
            <span className="analysis-reasoning__stat">Generation time: {usage ? `${usage.generation_time_ms}ms` : '—'}</span>
          </div>
          <div className="analysis-reasoning">
            <pre className="analysis-reasoning__text">{assistantContent}</pre>
          </div>
        </section>

        {thinkingSteps.length === 0 && retrievedContext.length === 0 && (
          <div className="analysis-tab__no-data">
            <p>This response has no analysis data. This may happen for simple greetings or non-RAG queries.</p>
          </div>
        )}
      </div>
    </div>
  )
}
