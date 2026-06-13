import { useState } from 'react'
import { LogoMark } from '../ui/LogoMark'
import { ChatSearch } from './ChatSearch'
import {
  Bot,
  FileText,
  Inbox,
  Folder,
  Database,
  Briefcase,
  Users,
  Workflow,
  Share2,
  BarChart3,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  MessageSquare,
  PlugZap,
  Puzzle,
  Cpu,
  Activity,
  HardDrive,
  Boxes,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ChatSession } from '../../types/chat'
import './Sidebar.css'

interface SidebarProps {
  sessions: ChatSession[]
  activeSessionId: string | null
  onCreateSession: () => void
  onSelectSession: (sessionId: string) => void
  searchQuery: string
  onSearchChange: (query: string) => void
  activeTab: string
  onTabChange: (tabId: string) => void
}

interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  disabled?: boolean
}

interface NavGroup {
  title: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: 'CHAT',
    items: [
      { id: 'chat', label: 'Chat', icon: MessageSquare },
      { id: 'agents', label: 'Agents', icon: Bot, disabled: true },
      { id: 'templates', label: 'Templates', icon: FileText, disabled: true },
      { id: 'conversations', label: 'Conversations', icon: Inbox, disabled: true },
    ],
  },
  {
    title: 'WORKSPACE',
    items: [
      { id: 'documents', label: 'Documents', icon: Folder },
      { id: 'ocr', label: 'OCR', icon: FileText },
      { id: 'knowledge', label: 'Knowledge', icon: Database, disabled: true },
      { id: 'projects', label: 'Projects', icon: Briefcase, disabled: true },
      { id: 'team', label: 'Team', icon: Users, disabled: true },
      { id: 'connectors', label: 'Connectors', icon: PlugZap, disabled: true },
      { id: 'plugins', label: 'Plugins', icon: Puzzle, disabled: true },
      { id: 'opcua', label: 'OPC-UA', icon: Cpu, disabled: true },
    ],
  },
  {
    title: 'TOOLS',
    items: [
      { id: 'tools', label: 'Tools', icon: Workflow },
      { id: 'integrations', label: 'Integrations', icon: Share2, disabled: true },
      { id: 'analysis', label: 'Analytics', icon: BarChart3 },
      { id: 'settings', label: 'Settings', icon: Settings, disabled: true },
      { id: 'timeseries', label: 'Time Series Model', icon: Activity, disabled: true },
      { id: 'maximo', label: 'Maximo Connector', icon: HardDrive, disabled: true },
      { id: 'sap', label: 'SAP Connector', icon: Boxes, disabled: true },
    ],
  },
]

function formatCompactDate(date: Date): string {
  const now = new Date()
  const d = new Date(date)
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  if (diffDays < 7) {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    return days[d.getDay()]
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function Sidebar({
  sessions,
  activeSessionId,
  onCreateSession,
  onSelectSession,
  searchQuery,
  onSearchChange,
  activeTab,
  onTabChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  const handleToggle = () => setCollapsed((c) => !c)

  return (
    <aside className={`sidebar${collapsed ? ' sidebar--collapsed' : ''}`}>
      <div className="sidebar__header">
        <LogoMark showText={!collapsed} />
        <button
          className="sidebar__collapse-btn"
          onClick={handleToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          type="button"
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <div className="sidebar__actions">
        <button
          className="sidebar__new-chat"
          onClick={onCreateSession}
          aria-label="Start new chat"
          type="button"
        >
          <Plus size={18} />
          {!collapsed && <span>New Chat</span>}
          {!collapsed && (
            <span className="sidebar__new-chat-shortcut">Ctrl K</span>
          )}
        </button>
      </div>

      {!collapsed && (
        <div className="sidebar__search">
          <ChatSearch
            searchQuery={searchQuery}
            onSearchChange={onSearchChange}
          />
        </div>
      )}

      <nav className="sidebar__nav">
        {NAV_GROUPS.map((group) => (
          <div className="sidebar__nav-group" key={group.title}>
            {!collapsed && (
              <div className="sidebar__nav-group-title">{group.title}</div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon
              const isActive = activeTab === item.id
              const isChatItem = item.id === 'chat'
              return (
                <button
                  key={item.id}
                  className={[
                    'sidebar__nav-item',
                    isChatItem ? 'sidebar__nav-item--chat' : '',
                    isActive ? 'sidebar__nav-item--active' : '',
                    item.disabled ? 'sidebar__nav-item--disabled' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  onClick={item.disabled ? undefined : () => onTabChange(item.id)}
                  aria-disabled={item.disabled ? 'true' : undefined}
                  aria-current={isActive && !item.disabled ? 'page' : undefined}
                  title={item.disabled ? `${item.label} — Coming soon` : (collapsed ? item.label : undefined)}
                  type="button"
                >
                  {isChatItem ? (
                    <span className="sidebar__nav-brandmark" aria-hidden="true">
                      <LogoMark showText={false} className="sidebar__nav-brandmark-logo" />
                    </span>
                  ) : (
                    <Icon size={18} />
                  )}
                  {!collapsed && <span>{item.label}</span>}
                  {!collapsed && item.disabled && (
                    <span className="sidebar__nav-badge">Soon</span>
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {!collapsed && (
        <>
          <div className="sidebar__divider" />

          <div className="sidebar__recent">
            <div className="sidebar__recent-header">
              <span className="sidebar__recent-title">Recent Chats</span>
              <button className="sidebar__recent-see-all" type="button">
                See all
              </button>
            </div>

            {sessions.length === 0 ? (
              <div className="sidebar__recent-empty">
                <MessageSquare size={16} />
                <span>No conversations yet</span>
              </div>
            ) : (
              <div className="sidebar__recent-list">
                {sessions.slice(0, 8).map((session) => (
                  <button
                    key={session.id}
                    className={`sidebar__recent-item${
                      session.id === activeSessionId
                        ? ' sidebar__recent-item--active'
                        : ''
                    }`}
                    onClick={() => onSelectSession(session.id)}
                    type="button"
                  >
                    <MessageSquare size={14} className="sidebar__recent-icon" />
                    <span className="sidebar__recent-name">{session.title}</span>
                    <span className="sidebar__recent-time">
                      {formatCompactDate(session.updatedAt)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  )
}
