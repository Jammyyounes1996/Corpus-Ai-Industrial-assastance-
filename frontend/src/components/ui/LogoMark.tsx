
import './LogoMark.css'

interface LogoMarkProps {
  showText?: boolean
  className?: string
}

export function LogoMark({ showText = false, className = '' }: LogoMarkProps) {
  return (
    <div className={`logo-mark-text ${className}`}>
      <div className="logo-mark"></div>
      {showText && <span>CORPUS</span>}
    </div>
  )
}