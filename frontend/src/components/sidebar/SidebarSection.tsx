import React from 'react'
import './SidebarSection.css'

interface SidebarSectionProps {
  title: string
  children: React.ReactNode
  className?: string
}

export function SidebarSection({ 
  title, 
  children, 
  className = '' 
}: SidebarSectionProps) {
  return (
    <div className={`sidebar-section ${className}`}>
      <div className="sidebar-section-title">{title}</div>
      <div className="sidebar-section-content">
        {children}
      </div>
    </div>
  )
}