
import './PlaceholderView.css'

interface PlaceholderViewProps {
  icon: string
  title: string
  description: string
  badge?: string
  className?: string
}

export function PlaceholderView({ 
  icon, 
  title, 
  description, 
  badge = 'Coming soon',
  className = '' 
}: PlaceholderViewProps) {
  return (
    <div className={`placeholder-view ${className}`}>
      <div className="placeholder-content">
        <div className="placeholder-icon">{icon}</div>
        <h2 className="placeholder-title">{title}</h2>
        <p className="placeholder-description">{description}</p>
        <div className="placeholder-badge">
          <span className="placeholder-badge-icon">🚀</span>
          <span>{badge}</span>
        </div>
      </div>
    </div>
  )
}