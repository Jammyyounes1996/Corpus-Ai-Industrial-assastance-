import { useState, useEffect, useCallback } from 'react'
import {
  Gauge,
  Play,
  RefreshCw,
  History,
  AlertCircle,
  Cpu,
} from 'lucide-react'
import { config } from '../../config'
import type { ChatSession } from '../../types/chat'

interface OllamaModel {
  name: string
  size: number
  modified_at: string
}

interface EvaluationResult {
  id: number
  chat_id: string
  message_id: number
  faithfulness: number | null
  answer_relevancy: number | null
  model_used: string | null
  created_at: string
  message_preview: string
}

function formatScore(value: number | null): string {
  if (value === null) return 'N/A'
  return value.toFixed(3)
}

function getScoreColor(score: number | null): string {
  if (score === null) return 'var(--text-muted)'
  if (score >= 0.8) return 'var(--color-success)'
  if (score >= 0.6) return 'var(--color-primary, #6366f1)'
  if (score >= 0.4) return 'var(--color-warning)'
  return 'var(--color-error)'
}

function getScoreLabel(score: number | null): string {
  if (score === null) return 'Not available'
  if (score >= 0.9) return 'Excellent'
  if (score >= 0.8) return 'Good'
  if (score >= 0.6) return 'Fair'
  if (score >= 0.4) return 'Needs improvement'
  return 'Poor'
}

function GaugeCard({ label, score, icon }: { label: string; score: number | null; icon: React.ReactNode }) {
  const pct = score !== null ? Math.round(score * 100) : 0
  const circumference = 2 * Math.PI * 40
  const offset = circumference - (pct / 100) * circumference

  return (
    <div className="tools-gauge-card">
      <div className="tools-gauge-card__header">
        {icon}
        <span>{label}</span>
      </div>
      <div className="tools-gauge-card__viz">
        <svg viewBox="0 0 100 100" className="tools-gauge-svg">
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="var(--surface-border, #333)"
            strokeWidth="8"
          />
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke={getScoreColor(score)}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
            className="tools-gauge-arc"
          />
        </svg>
        <div className="tools-gauge-card__score" style={{ color: getScoreColor(score) }}>
          {formatScore(score)}
        </div>
      </div>
      <div className="tools-gauge-card__label" style={{ color: getScoreColor(score) }}>
        {getScoreLabel(score)}
      </div>
    </div>
  )
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function RagasEvaluator({ activeSession }: { activeSession: ChatSession | null }) {
  const [models, setModels] = useState<OllamaModel[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [modelsLoading, setModelsLoading] = useState(true)
  const [evaluating, setEvaluating] = useState(false)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [latestResult, setLatestResult] = useState<EvaluationResult | null>(null)
  const [history, setHistory] = useState<EvaluationResult[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  const fetchModels = useCallback(async (signal?: AbortSignal) => {
    setModelsLoading(true)
    try {
      const res = await fetch('/ollama-api/api/tags', { signal })
      if (!res.ok) throw new Error('Failed to fetch models')
      const data = await res.json()
      const modelList: OllamaModel[] = (data.models || []).map((m: any) => ({
        name: m.name,
        size: m.size,
        modified_at: m.modified_at,
      }))
      setModels(modelList)
      if (modelList.length > 0 && !selectedModel) {
        setSelectedModel(modelList[0].name)
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setModels([])
    } finally {
      setModelsLoading(false)
    }
  }, [selectedModel])

  const fetchHistory = useCallback(async (signal?: AbortSignal) => {
    setHistoryLoading(true)
    try {
      const params = activeSession?.backendChatId
        ? `?chat_id=${activeSession.backendChatId}`
        : ''
      const res = await fetch(`${config.evaluationEndpoints.evaluations}${params}`, { signal })
      if (!res.ok) throw new Error('Failed to fetch evaluations')
      const data = await res.json()
      const evals: EvaluationResult[] = data.evaluations || []
      setHistory(evals)
      if (evals.length > 0) {
        setLatestResult(evals[0])
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setHistory([])
    } finally {
      setHistoryLoading(false)
    }
  }, [activeSession?.backendChatId])

  useEffect(() => {
    const controller = new AbortController()
    fetchModels(controller.signal)
    fetchHistory(controller.signal)
    return () => controller.abort()
  }, [fetchModels, fetchHistory])

  const handleEvaluate = async () => {
    if (!activeSession?.backendChatId) {
      setEvalError('No active chat session. Send a message first.')
      return
    }

    setEvaluating(true)
    setEvalError(null)

    try {
      const chatRes = await fetch(`/api/chat/${activeSession.backendChatId}`)
      if (!chatRes.ok) throw new Error('Failed to fetch chat messages')
      const chatData = await chatRes.json()
      const messages = chatData.messages || []

      const lastAssistant = [...messages].reverse().find((m: any) => m.role === 'assistant')
      if (!lastAssistant) {
        setEvalError('No assistant message found in this chat.')
        setEvaluating(false)
        return
      }

      const evalRes = await fetch(config.evaluationEndpoints.evaluate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: activeSession.backendChatId,
          message_id: lastAssistant.id,
          judge_model: selectedModel || undefined,
        }),
      })

      if (!evalRes.ok) {
        const errData = await evalRes.json().catch(() => ({}))
        throw new Error(errData.detail || `Evaluation failed (${evalRes.status})`)
      }

      const result = await evalRes.json()
      setLatestResult(result)
      await fetchHistory()
    } catch (err: any) {
      setEvalError(err.message || 'Evaluation failed')
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="tools-ragas">
      <div className="tools-ragas__controls">
        <div className="tools-ragas__model-section">
          <label className="tools-ragas__label">
            <Cpu size={14} />
            Judge Model
          </label>
          {modelsLoading ? (
            <span className="tools-ragas__model-loading">Scanning Ollama...</span>
          ) : models.length === 0 ? (
            <span className="tools-ragas__model-error">No Ollama models found</span>
          ) : (
            <select
              className="tools-ragas__model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          )}
        </div>

        <button
          className="tools-ragas__run-btn"
          onClick={handleEvaluate}
          disabled={evaluating || !activeSession?.backendChatId}
        >
          {evaluating ? (
            <>
              <RefreshCw size={16} className="spin" />
              Evaluating...
            </>
          ) : (
            <>
              <Play size={16} />
              Run Evaluation on Last Chat
            </>
          )}
        </button>
      </div>

      {!activeSession?.backendChatId && (
        <div className="tools-ragas__notice">
          <AlertCircle size={16} />
          <span>No active chat session. Send a message in the Chat tab first.</span>
        </div>
      )}

      {evalError && (
        <div className="tools-ragas__error">
          <AlertCircle size={16} />
          <span>{evalError}</span>
        </div>
      )}

      {latestResult && (
        <div className="tools-ragas__metrics">
          <GaugeCard
            label="Faithfulness"
            score={latestResult.faithfulness}
            icon={<Gauge size={14} />}
          />
          <GaugeCard
            label="Answer Relevancy"
            score={latestResult.answer_relevancy}
            icon={<Gauge size={14} />}
          />
        </div>
      )}

      <div className="tools-ragas__history-section">
        <div className="tools-ragas__history-header">
          <History size={16} />
          <span>Evaluation History</span>
        </div>

        {historyLoading ? (
          <div className="tools-ragas__history-loading">
            <div className="tools-tab__spinner" />
          </div>
        ) : history.length === 0 ? (
          <div className="tools-ragas__history-empty">
            No evaluations yet. Run your first evaluation above.
          </div>
        ) : (
          <div className="tools-ragas__table-wrap">
            <table className="tools-ragas__table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Message Preview</th>
                  <th>Faithfulness</th>
                  <th>Relevancy</th>
                  <th>Model</th>
                </tr>
              </thead>
              <tbody>
                {history.map((ev) => (
                  <tr key={ev.id}>
                    <td className="tools-ragas__td-date">{formatDate(ev.created_at)}</td>
                    <td className="tools-ragas__td-preview">{ev.message_preview || '\u2014'}</td>
                    <td style={{ color: getScoreColor(ev.faithfulness) }}>
                      {formatScore(ev.faithfulness)}
                    </td>
                    <td style={{ color: getScoreColor(ev.answer_relevancy) }}>
                      {formatScore(ev.answer_relevancy)}
                    </td>
                    <td className="tools-ragas__td-model">{ev.model_used || '\u2014'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
