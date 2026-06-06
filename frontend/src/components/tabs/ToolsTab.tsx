import './ToolsTab.css'
import { useState } from 'react'
import { Gauge, Mic } from 'lucide-react'
import type { ChatSession } from '../../types/chat'
import { RagasEvaluator } from './RagasEvaluator'
import { AudioTranscriber } from './AudioTranscriber'

type ToolView = 'ragas' | 'audio'

interface ToolsTabProps {
  activeSession: ChatSession | null
}

export function ToolsTab({ activeSession }: ToolsTabProps) {
  const [activeView, setActiveView] = useState<ToolView>('ragas')

  return (
    <div className="tools-tab">
      <div className="tools-tab__toggle">
        <button
          className={`tools-tab__toggle-btn ${activeView === 'ragas' ? 'active' : ''}`}
          onClick={() => setActiveView('ragas')}
        >
          <Gauge size={16} />
          RAGAS Evaluator
        </button>
        <button
          className={`tools-tab__toggle-btn ${activeView === 'audio' ? 'active' : ''}`}
          onClick={() => setActiveView('audio')}
        >
          <Mic size={16} />
          Audio Transcriber
        </button>
      </div>

      {activeView === 'ragas' ? (
        <RagasEvaluator activeSession={activeSession} />
      ) : (
        <AudioTranscriber />
      )}
    </div>
  )
}
