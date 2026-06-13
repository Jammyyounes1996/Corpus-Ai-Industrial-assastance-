import { useConnectionStatus } from '../../hooks/useConnectionStatus'
import { ConnectionStatusBadge } from '../status/ConnectionStatusBadge'
import { ConnectionStatusMenu } from '../status/ConnectionStatusMenu'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import './WorkspaceHeader.css'

const TAB_TITLES: Record<string, string> = {
  chat: 'Chat',
  documents: 'Documents',
  ocr: 'OCR',
  analysis: 'Analysis',
  tools: 'Tools',
}

interface WorkspaceHeaderProps {
  activeTab: string
  onTabChange: (tabId: string) => void
}

export function WorkspaceHeader({ activeTab, onTabChange }: WorkspaceHeaderProps) {
  const { status, refresh } = useConnectionStatus()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="workspace-header">
      <div className="workspace-header-left">
        {activeTab !== 'chat' && (
          <button
            type="button"
            className="workspace-header__back"
            onClick={() => onTabChange('chat')}
            aria-label="Back to Chat"
          >
            <ArrowLeft size={16} />
            <span>Back to Chat</span>
          </button>
        )}
        <h1 className="workspace-header__title">
          {TAB_TITLES[activeTab] ?? 'Chat'}
        </h1>
      </div>

      <div className="workspace-header-right">
        <div className="workspace-status" onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setMenuOpen(false)
          }
        }}>
          <ConnectionStatusBadge
            status={status.connection}
            onClick={() => setMenuOpen((prev) => !prev)}
            ariaExpanded={menuOpen}
            ariaHasPopup="dialog"
          />
          <ConnectionStatusMenu
            status={status}
            open={menuOpen}
            onRefresh={refresh}
          />
        </div>
      </div>
    </header>
  )
}
