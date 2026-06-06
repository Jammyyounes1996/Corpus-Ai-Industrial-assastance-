/* File Attach Button Component */
/*
  Button and hidden file input for selecting attachments
*/

import React, { useCallback, useRef } from 'react'
import { Paperclip } from 'lucide-react'
import './FileAttachButton.css'

interface FileAttachButtonProps {
  className?: string
  disabled?: boolean
  multiple?: boolean
  maxFiles?: number
  accept?: string
  onSelectFiles: (files: FileList) => void
  canAddMoreFiles: boolean
  validateFiles: (files: FileList) => Array<{ code: string; message: string }>
}

export function FileAttachButton({ 
  className = '',
  disabled = false,
  multiple = true,
  maxFiles = 10,
  onSelectFiles,
  canAddMoreFiles,
  validateFiles
}: FileAttachButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    // Check if we can add more files
    if (!canAddMoreFiles) {
      // Show error or handle appropriately
      return
    }

    // Validate files first
    const errors = validateFiles(files)
    if (errors.length > 0) {
      // You could show a toast or inline error here
      console.log('File validation errors:', errors)
      return
    }

    // Add valid files
    onSelectFiles(files)

    // Reset the input value so the same files can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [canAddMoreFiles, onSelectFiles, validateFiles])

  const handleClick = useCallback(() => {
    if (disabled || !fileInputRef.current) return
    
    fileInputRef.current.click()
  }, [disabled])

  const handleKeyPress = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleClick()
    }
  }, [handleClick])

  const getAcceptString = useCallback(() => {
    const types = [
      'application/pdf',
      'image/jpeg', 
      'image/jpg',
      'image/png',
      'image/webp',
      'audio/mpeg',
      'audio/wav',
      'audio/ogg'
    ]
    
    return types.join(',')
  }, [])

  return (
    <div className={`file-attach-button ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept={getAcceptString()}
        multiple={multiple}
        onChange={handleFileSelect}
        disabled={disabled}
        className="file-input"
        aria-label="Attach files"
        title="Attach files (PDF, images, audio)"
      />
      
      <button
        onClick={handleClick}
        onKeyDown={handleKeyPress}
        disabled={disabled || !canAddMoreFiles}
        className={`attach-button ${disabled ? 'disabled' : ''} ${!canAddMoreFiles ? 'max-files' : ''}`}
        aria-label="Attach files"
        title={disabled ? 'Attach files is disabled' : 
               !canAddMoreFiles ? `Maximum ${maxFiles} files attached` : 
               'Attach files (PDF, images, audio)'}
      >
        <Paperclip size={16} />
        <span>Attach</span>
        {multiple && canAddMoreFiles && (
          <span className="file-count">
            ({maxFiles})
          </span>
        )}
      </button>
    </div>
  )
}
