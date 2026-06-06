import React from 'react'
import { WORKSPACE_TABS } from './WorkspaceData'
import './WorkspaceTabs.css'

interface WorkspaceTabsProps {
  activeTab: string
  onTabChange: (tabId: string) => void
}

export function WorkspaceTabs({ activeTab, onTabChange }: WorkspaceTabsProps) {
  const handleTabClick = (tabId: string) => {
    onTabChange(tabId)
  }

  

  const handleKeyDownArrow = (e: React.KeyboardEvent, index: number) => {
    const tabs = WORKSPACE_TABS
    
    if (e.key === 'ArrowRight') {
      e.preventDefault()
      const nextIndex = (index + 1) % tabs.length
      onTabChange(tabs[nextIndex].id)
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      const prevIndex = index === 0 ? tabs.length - 1 : index - 1
      onTabChange(tabs[prevIndex].id)
    }
  }

  return (
    <nav className="workspace-tabs" role="tablist" aria-label="Workspace navigation">
      {WORKSPACE_TABS.map((tab, index) => {
        const Icon = tab.icon
        return (
<button
          key={tab.id}
          className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => handleTabClick(tab.id)}
          onKeyDown={(e) => handleKeyDownArrow(e, index)}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`panel-${tab.id}`}
          tabIndex={activeTab === tab.id ? 0 : -1}
        >
            <Icon className="tab-icon" aria-hidden="true" />
            <span className="tab-label">{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}