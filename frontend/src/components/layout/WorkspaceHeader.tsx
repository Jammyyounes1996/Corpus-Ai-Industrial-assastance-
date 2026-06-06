import { WorkspaceTabs } from '../tabs/WorkspaceTabs'
import { useState } from 'react'
import { useConnectionStatus } from '../../hooks/useConnectionStatus'
import { ConnectionStatusBadge } from '../status/ConnectionStatusBadge'
import { ConnectionStatusMenu } from '../status/ConnectionStatusMenu'
import './WorkspaceHeader.css'

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
        <WorkspaceTabs 
          activeTab={activeTab}
          onTabChange={onTabChange}
        />
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
