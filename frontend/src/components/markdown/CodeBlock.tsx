import { useState, useRef, useCallback } from 'react'
import { Copy, Check } from 'lucide-react'
import './CodeBlock.css'

interface CodeBlockProps {
  language?: string
  children: string
}

export function CodeBlock({ language, children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const codeRef = useRef<HTMLPreElement>(null)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(children)
      setCopied(true)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }, [children])

  return (
    <div className="code-block">
      <div className="code-block__header">
        {language && (
          <span className="code-block__lang">{language}</span>
        )}
        <button
          className="code-block__copy-btn"
          onClick={handleCopy}
          aria-label={copied ? 'Copied to clipboard' : 'Copy code to clipboard'}
          type="button"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span className="code-block__copy-label">{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre ref={codeRef} className="code-block__pre">
        <code className={language ? `language-${language}` : ''}>{children}</code>
      </pre>
    </div>
  )
}
