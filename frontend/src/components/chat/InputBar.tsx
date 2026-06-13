import { useState, useRef, useCallback } from 'react'
import {
  Mic,
  ChevronDown,
  ArrowUp,
  Square,
} from 'lucide-react'
import { FileAttachButton } from './FileAttachButton'
import { AttachmentTray } from './AttachmentTray'
import type { AttachedFile, ValidationError } from '../../types/attachments'
import type { AnswerMode } from '../../types/api'
import { InlineError } from '../ui/InlineError'
import { getTextDirection } from '../../utils/textDirection'
import './InputBar.css'

const ANSWER_MODE_OPTIONS: { value: AnswerMode; label: string; tooltip: string }[] = [
  { value: 'groundx', label: 'GroundX Mode', tooltip: 'Answers from GroundX-indexed PDF/documents only.' },
  { value: 'audio', label: 'Audio Mode', tooltip: 'Answers from audio transcripts stored in the vector database only.' },
  { value: 'general', label: 'General Mode', tooltip: "Answers from the model's general knowledge only." },
]

export interface ModelOption {
  id: string
  label: string
  provider: string
}

const DEFAULT_MODELS: ModelOption[] = [
  { id: 'default', label: 'Default Model', provider: 'ollama' },
]

interface InputBarProps {
  onSend: (text: string) => void
  onCancel?: () => void
  isStreaming?: boolean
  disabled?: boolean
  models?: ModelOption[]
  selectedModelId?: string
  onModelChange?: (modelId: string) => void
  answerMode?: AnswerMode
  onAnswerModeChange?: (mode: AnswerMode) => void
  onAttachFiles: (files: FileList) => void
  onRemoveAttachment: (fileId: string) => void
  onRetryAttachment: (fileId: string) => void
  validateAttachmentFiles: (files: FileList) => ValidationError[]
  canAddMoreFiles: boolean
  attachments: AttachedFile[]
  failedAttachments: AttachedFile[]
  errorText?: string | null
  onRetrySend?: () => void
  canRetrySend?: boolean
  onDismissError?: () => void
}

export function InputBar({
  onSend,
  onCancel,
  isStreaming = false,
  disabled = false,
  models = DEFAULT_MODELS,
  selectedModelId,
  onModelChange,
  answerMode = 'general',
  onAnswerModeChange,
  onAttachFiles,
  onRemoveAttachment,
  onRetryAttachment,
  validateAttachmentFiles,
  canAddMoreFiles,
  attachments,
  failedAttachments,
  errorText,
  onRetrySend,
  canRetrySend = false,
  onDismissError
}: InputBarProps) {
  const [text, setText] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [isModelOpen, setIsModelOpen] = useState(false)
  const [isModeOpen, setIsModeOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const modelMenuRef = useRef<HTMLDivElement>(null)
  const modeMenuRef = useRef<HTMLDivElement>(null)

  const trimmedText = text.trim()
  const inputDir = getTextDirection(text)
  const hasBlockingAttachments = attachments.some((file) =>
    file.status === 'pending' || file.status === 'uploading' || file.status === 'failed'
  )
  const canSend = trimmedText.length > 0 && !disabled && !hasBlockingAttachments

  const handleSend = useCallback(() => {
    if (!canSend || isStreaming) return
    onSend(trimmedText)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [canSend, isStreaming, onSend, trimmedText])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (isComposing) return
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [isComposing, handleSend]
  )

  const handleCompositionStart = useCallback(() => {
    setIsComposing(true)
  }, [])

  const handleCompositionEnd = useCallback(() => {
    setIsComposing(false)
  }, [])

  const handleTextareaInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value)
      const el = e.target
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    },
    []
  )

  const handleCancel = useCallback(() => {
    onCancel?.()
  }, [onCancel])

  const toggleModelMenu = useCallback(() => {
    setIsModelOpen((prev) => !prev)
  }, [])

  const selectModel = useCallback(
    (model: ModelOption) => {
      onModelChange?.(model.id)
      setIsModelOpen(false)
    },
    [onModelChange]
  )

  const toggleModeMenu = useCallback(() => {
    setIsModeOpen((prev) => !prev)
  }, [])

  const selectMode = useCallback(
    (mode: AnswerMode) => {
      onAnswerModeChange?.(mode)
      setIsModeOpen(false)
    },
    [onAnswerModeChange]
  )

  const currentModeOption = ANSWER_MODE_OPTIONS.find((o) => o.value === answerMode) ?? ANSWER_MODE_OPTIONS[2]

  const currentModel =
    models.find((m) => m.id === selectedModelId) ?? models[0]

  return (
    <div className="input-bar">
      <AttachmentTray
        files={attachments}
        failedFiles={failedAttachments}
        onRemove={onRemoveAttachment}
        onRetry={onRetryAttachment}
      />

      {errorText ? (
        <InlineError
          message={errorText}
          onRetry={canRetrySend ? onRetrySend : undefined}
          onDismiss={onDismissError}
          retryLabel="Retry send"
        />
      ) : null}

      <div className="input-bar__row">
        <textarea
          ref={textareaRef}
          className={`input-bar__textarea input-bar__textarea--${inputDir}`}
          placeholder="What's in your mind Mohamed?"
          value={text}
          onChange={handleTextareaInput}
          onKeyDown={handleKeyDown}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
          disabled={disabled}
          dir={inputDir}
          style={inputDir === 'rtl' ? { textAlign: 'right' } : undefined}
          rows={1}
          aria-label="Message input"
        />

        <div className="input-bar__controls">
          <div className="input-bar__controls-left">
            <div className="input-bar__mode-selector" ref={modeMenuRef}>
              <button
                className="input-bar__selector-pill"
                onClick={toggleModeMenu}
                disabled={disabled || isStreaming}
                aria-label="Select answer mode"
                title={currentModeOption.tooltip}
                aria-expanded={isModeOpen}
                aria-haspopup="listbox"
              >
                <span className="input-bar__selector-label">
                  {currentModeOption.label}
                </span>
                <ChevronDown size={14} />
              </button>

              {isModeOpen && (
                <ul className="input-bar__selector-menu" role="listbox">
                  {ANSWER_MODE_OPTIONS.map((opt) => (
                    <li key={opt.value} role="none">
                      <button
                        type="button"
                        className={`input-bar__selector-option ${
                          opt.value === answerMode ? 'active' : ''
                        }`}
                        role="option"
                        aria-selected={opt.value === answerMode}
                        title={opt.tooltip}
                        onClick={() => selectMode(opt.value)}
                      >
                        {opt.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="input-bar__model-selector" ref={modelMenuRef}>
              <button
                className="input-bar__selector-pill"
                onClick={toggleModelMenu}
                disabled={disabled || isStreaming}
                aria-label="Select model"
                aria-expanded={isModelOpen}
                aria-haspopup="listbox"
              >
                <span className="input-bar__selector-label">
                  {currentModel.label}
                </span>
                <ChevronDown size={14} />
              </button>

              {isModelOpen && (
                <ul className="input-bar__selector-menu" role="listbox">
                  {models.map((model) => (
                    <li
                      key={model.id}
                      role="none"
                    >
                      <button
                        type="button"
                        className={`input-bar__selector-option ${
                          model.id === currentModel.id ? 'active' : ''
                        }`}
                        role="option"
                        aria-selected={model.id === currentModel.id}
                        onClick={() => selectModel(model)}
                      >
                        {model.label}
                        <span className="input-bar__selector-provider">
                          {model.provider}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="input-bar__controls-right">
            <FileAttachButton
              disabled={disabled || isStreaming}
              onSelectFiles={onAttachFiles}
              canAddMoreFiles={canAddMoreFiles}
              validateFiles={validateAttachmentFiles}
            />

            <button
              className="input-bar__icon-btn"
              disabled={disabled || isStreaming}
              aria-label="Audio file"
              title="Audio file"
            >
              <Mic size={16} />
            </button>

            {isStreaming ? (
              <button
                className="input-bar__send-btn input-bar__send-btn--cancel"
                onClick={handleCancel}
                aria-label="Cancel streaming"
                title="Cancel"
              >
                <Square size={16} />
              </button>
            ) : (
              <button
                className={`input-bar__send-btn ${
                  canSend ? 'input-bar__send-btn--active' : ''
                }`}
                onClick={handleSend}
                disabled={!canSend}
                aria-label="Send message"
                title="Send"
              >
                <ArrowUp size={18} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
