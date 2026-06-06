
import { LogoMark } from '../ui/LogoMark'
import { ChatSearch } from './ChatSearch'
import { ChatList } from './ChatList'
import { SidebarSection } from './SidebarSection'
import type { ChatSession } from '../../types/chat'
import './Sidebar.css'

interface SidebarProps {
  sessions: ChatSession[]
  activeSessionId: string | null
  onCreateSession: () => void
  onSelectSession: (sessionId: string) => void
  searchQuery: string
  onSearchChange: (query: string) => void
}

export function Sidebar({ 
  sessions, 
  activeSessionId, 
  onCreateSession, 
  onSelectSession, 
  searchQuery, 
  onSearchChange 
}: SidebarProps) {
  return (
    <aside className="sidebar">
      {/* Header with logo */}
      <div className="sidebar-header">
        <LogoMark showText />
        <button 
          className="new-chat-button"
          onClick={onCreateSession}
          aria-label="Start new chat"
        >
          <span>+</span>
          <span>New Chat</span>
        </button>
      </div>
      
      {/* Chat search */}
      <div className="sidebar-search">
        <ChatSearch 
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
        />
      </div>
      
      {/* Chat list */}
      <div className="sidebar-chat-list">
        <ChatList 
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={onSelectSession}
        />
      </div>
      
      {/* Footer sections */}
      <div className="sidebar-footer">
        <SidebarSection title="Projects">
          <div className="placeholder-item">Project 1</div>
          <div className="placeholder-item">Project 2</div>
        </SidebarSection>
        
        <SidebarSection title="Knowledge Bases">
          <div className="placeholder-item">KB 1</div>
          <div className="placeholder-item">KB 2</div>
        </SidebarSection>
        
        <SidebarSection title="Tools">
          <div className="placeholder-item">Tool 1</div>
          <div className="placeholder-item">Tool 2</div>
        </SidebarSection>
        
        <SidebarSection title="Settings">
          <div className="placeholder-item">Preferences</div>
          <div className="placeholder-item">Account</div>
        </SidebarSection>
      </div>
    </aside>
  )
}