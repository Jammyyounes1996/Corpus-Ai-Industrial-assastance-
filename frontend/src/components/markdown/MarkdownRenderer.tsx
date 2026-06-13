import { Component as ReactComponent, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CodeBlock } from './CodeBlock'
import type { Components } from 'react-markdown'
import './MarkdownRenderer.css'

interface MarkdownRendererProps {
  content: string
}

class MarkdownErrorBoundary extends ReactComponent<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return null
    }
    return this.props.children
  }
}

function PlainFallback({ content }: { content: string }) {
  return <div className="md-renderer__fallback">{content}</div>
}

function getPlainText(node: ReactNode): string | null {
  if (typeof node === 'string' || typeof node === 'number') {
    return String(node)
  }

  if (Array.isArray(node)) {
    const parts: string[] = []
    for (const child of node) {
      const text = getPlainText(child)
      if (text === null) {
        return null
      }
      parts.push(text)
    }
    return parts.join('')
  }

  return null
}

function isLabelHeading(text: string): boolean {
  const normalized = text.trim()
  if (!normalized || normalized.includes('\n')) {
    return false
  }

  const wordCount = normalized.split(/\s+/).length
  if (wordCount > 7 || normalized.length > 80) {
    return false
  }

  return /[:：]$|[؟?]$/.test(normalized)
}

const components: Components = {
  p({ children }) {
    const plainText = getPlainText(children)

    if (plainText && isLabelHeading(plainText)) {
      return (
        <p className="md-renderer__label-heading">
          <strong>{children}</strong>
        </p>
      )
    }

    return <p>{children}</p>
  },
  code({ className, children, ...rest }) {
    const codeString = String(children).replace(/\n$/, '')
    const match = /language-(\w+)/.exec(className || '')
    const isInline = !match && !codeString.includes('\n')

    if (isInline) {
      return (
        <code className="md-renderer__inline-code" {...rest}>
          {children}
        </code>
      )
    }

    return <CodeBlock language={match?.[1]}>{codeString}</CodeBlock>
  },
  pre({ children }) {
    return <>{children}</>
  },
  table({ children }) {
    return (
      <div className="md-renderer__table-wrap">
        <table>{children}</table>
      </div>
    )
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    )
  },
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="md-renderer">
      <MarkdownErrorBoundary>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={components}
          allowedElements={[
            'p', 'br', 'strong', 'em', 'del', 'code', 'pre',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li',
            'blockquote',
            'a', 'img',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'hr',
          ]}
        >
          {content}
        </ReactMarkdown>
      </MarkdownErrorBoundary>
      <noscript>
        <PlainFallback content={content} />
      </noscript>
    </div>
  )
}
