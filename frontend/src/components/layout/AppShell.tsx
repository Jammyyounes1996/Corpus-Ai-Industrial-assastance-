
import { WorkspaceHeader } from './WorkspaceHeader'
import { WorkspaceContent } from './WorkspaceContent'
import { Sidebar } from '../sidebar/Sidebar'
import type { ChatSession } from '../../types/chat'
import type { UseChatSessionsReturn } from '../../hooks/useChatSessions'
import './AppShell.css'

interface AppShellProps {
  activeTab: string
  onTabChange: (tabId: string) => void
  activeSession: ChatSession | null
  sessions: UseChatSessionsReturn
}

export function AppShell({ activeTab, onTabChange, activeSession, sessions }: AppShellProps) {
  return (
    <div className="AppShell">
      <Sidebar 
        sessions={sessions.filteredSessions}
        activeSessionId={sessions.activeSessionId}
        onCreateSession={sessions.createNewSession}
        onSelectSession={sessions.setActiveSession}
        searchQuery={sessions.searchQuery}
        onSearchChange={sessions.setSearchQuery}
        activeTab={activeTab}
        onTabChange={onTabChange}
      />
      
      <div className="workspace">
        <WorkspaceHeader 
          activeTab={activeTab}
          onTabChange={onTabChange}
        />
        <WorkspaceContent
          activeTab={activeTab}
          activeSession={activeSession}
          sessions={sessions}
          onTabChange={onTabChange}
        />
      </div>
    </div>
  )
}