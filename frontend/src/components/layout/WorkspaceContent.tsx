import { ChatWorkspace } from '../chat/ChatWorkspace'
import { DocumentsTab } from '../tabs/DocumentsTab'
import { OCRTab } from '../tabs/OCRTab'
import { AnalysisTab } from '../tabs/AnalysisTab'
import { ToolsTab } from '../tabs/ToolsTab'
import type { ChatSession } from '../../types/chat'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'

interface WorkspaceContentProps {
  activeTab: string
  activeSession: ChatSession | null
  sessions: UseChatSessionsReturn
  onTabChange: (tabId: string) => void
}

export function WorkspaceContent({ activeTab, activeSession, sessions, onTabChange }: WorkspaceContentProps) {
  switch (activeTab) {
    case 'chat':
      return (
        <main className="workspace-content">
          <ChatWorkspace session={activeSession} sessions={sessions} />
        </main>
      )
    case 'documents':
      return (
        <main className="workspace-content">
          <DocumentsTab />
        </main>
      )
    case 'ocr':
      return (
        <main className="workspace-content">
          <OCRTab sessions={sessions} onTabChange={onTabChange} />
        </main>
      )
    case 'analysis':
      return (
        <main className="workspace-content">
          <AnalysisTab activeSession={activeSession} />
        </main>
      )
    case 'tools':
      return (
        <main className="workspace-content">
          <ToolsTab activeSession={activeSession} />
        </main>
      )
    default:
      return <main className="workspace-content" />
  }
}
