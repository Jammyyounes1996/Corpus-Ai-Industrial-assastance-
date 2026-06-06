/* Attachment Hook */
/*
  State management for file attachments and uploads
  Handles validation, progress, and lifecycle management
*/

import { useState, useCallback } from 'react'
import { uploadFile } from '../services/fileUploadService'
import { 
  AttachedFile, 
  UploadStatus, 
  ValidationError, 
  isSupportedMimeType,
  validateFile,
  MAX_ATTACHED_FILES 
} from '../types/attachments'

interface UseAttachmentsReturn {
  // State
  files: AttachedFile[]
  uploadStatus: UploadStatus
  validationError: ValidationError | null
  
  // File operations
  addFiles: (files: FileList) => void
  removeFile: (fileId: string) => void
  clearFiles: () => void
  retryFile: (fileId: string) => void
  
  // Validation
  validateFiles: (files: FileList) => ValidationError[]
  
  // Upload state
  setUploadProgress: (fileId: string, progress: number) => void
  setUploadComplete: (fileId: string, response: { file_id: string; filename: string }) => void
  setUploadFailed: (fileId: string, error: string) => void
  
  // Getters
  canAddMoreFiles: boolean
  supportedFiles: File[]
  pendingFiles: File[]
  uploadedFiles: Array<{ file_id: string; filename: string; file_type: 'pdf' | 'image' | 'audio'; size: number; upload_timestamp: Date }>
  failedFiles: AttachedFile[]
}

const createAttachedFile = (file: File): AttachedFile => {
  const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  return {
    id: fileId,
    file,
    metadata: {
      name: file.name,
      size: file.size,
      type: file.type as 'application/pdf' | 'image/jpeg' | 'image/jpg' | 'image/png' | 'image/webp' | 'audio/mpeg' | 'audio/wav' | 'audio/ogg',
      lastModified: new Date(file.lastModified)
    },
    status: 'pending',
    progress: 0,
    objectUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
  }
}

export function useAttachments(): UseAttachmentsReturn {
  const [files, setFiles] = useState<AttachedFile[]>([])
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: 'idle',
    progress: 0,
    totalFiles: 0,
    completedFiles: 0,
    failedFiles: 0
  })
  const [validationError, setValidationError] = useState<ValidationError | null>(null)

  // Check if we can add more files
  const canAddMoreFiles = files.filter((file: AttachedFile) => file.status !== 'removed').length < MAX_ATTACHED_FILES

  // Add files with validation
  const addFiles = (newFiles: FileList) => {
    const fileArray = Array.from(newFiles)
    
    // Check if adding these files would exceed the maximum
    const currentFileCount = files.filter((file: AttachedFile) => file.status !== 'removed').length
    if (currentFileCount + fileArray.length > MAX_ATTACHED_FILES) {
      setValidationError({
        code: 'MAX_FILES_EXCEEDED',
        message: `Maximum ${MAX_ATTACHED_FILES} files allowed`
      })
      return
    }

    const validFiles: File[] = []
    const errors: ValidationError[] = []

    fileArray.forEach(file => {
      const validation = validateFile(file)
      if (validation) {
        errors.push(validation)
      } else {
        validFiles.push(file)
      }
    })

    if (errors.length > 0) {
      setValidationError(errors[0]) // Show first error
    } else {
      setValidationError(null)
    }

    if (validFiles.length > 0) {
      const attachedFiles = validFiles.map(createAttachedFile)
      setFiles(prev => [...prev, ...attachedFiles])
      setUploadStatus(prev => ({
        ...prev,
        status: 'uploading',
        totalFiles: prev.totalFiles + attachedFiles.length
      }))
      attachedFiles.forEach((attachedFile) => {
        setUploadProgress(attachedFile.id, 0)
        void uploadFile(attachedFile.file)
          .then((response) => {
            setUploadComplete(attachedFile.id, response)
          })
          .catch((error) => {
            const message = error instanceof Error ? error.message : 'Upload failed'
            setUploadFailed(attachedFile.id, message)
          })
      })
    }
  }

  // Remove a file
  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => 
      prev.map(file => {
        if (file.id === fileId && file.objectUrl) {
          URL.revokeObjectURL(file.objectUrl)
        }
        return file.id === fileId 
          ? { ...file, status: 'removed' as const }
          : file
      })
    )
  }, [])

  // Clear all files
  const clearFiles = useCallback(() => {
    // Revoke all object URLs
    files.forEach((file: AttachedFile) => {
      if (file.objectUrl) {
        URL.revokeObjectURL(file.objectUrl)
      }
    })
    setFiles([])
    setUploadStatus({
      status: 'idle',
      progress: 0,
      totalFiles: 0,
      completedFiles: 0,
      failedFiles: 0
    })
    setValidationError(null)
  }, [files])

  // Retry a failed file
  const retryFile = (fileId: string) => {
    let retryTarget: AttachedFile | undefined
    setFiles(prev =>
      prev.map(file => {
        if (file.id === fileId) {
          retryTarget = file
          return { ...file, status: 'pending' as const, progress: 0, error: undefined }
        }
        return file
      })
    )
    setUploadStatus(prev => ({
      ...prev,
      status: 'uploading',
      failedFiles: Math.max(0, prev.failedFiles - 1)
    }))
    if (retryTarget) {
      setUploadProgress(fileId, 0)
      void uploadFile(retryTarget.file)
        .then((response) => {
          setUploadComplete(fileId, response)
        })
        .catch((error) => {
          const message = error instanceof Error ? error.message : 'Upload failed'
          setUploadFailed(fileId, message)
        })
    }
  }

  // Validate files without adding them
  const validateFiles = useCallback((files: FileList): ValidationError[] => {
    const fileArray = Array.from(files)
    const errors: ValidationError[] = []

    fileArray.forEach(file => {
      const validation = validateFile(file)
      if (validation) {
        errors.push(validation)
      }
    })

    return errors
  }, [])

  // Update upload progress
  const setUploadProgress = useCallback((fileId: string, progress: number) => {
    setFiles(prev => 
      prev.map(file => 
        file.id === fileId 
          ? { ...file, status: 'uploading' as const, progress: Math.min(100, Math.max(0, progress)) }
          : file
      )
    )
    setUploadStatus(prev => ({
      ...prev,
      status: 'uploading'
    }))
  }, [])

  // Mark upload as complete
  const setUploadComplete = useCallback((fileId: string, response: { file_id: string; filename: string }) => {
    setFiles(prev => 
      prev.map(file => 
        file.id === fileId 
          ? {
              ...file,
              status: 'uploaded' as const,
              progress: 100,
              backendFileId: response.file_id,
              metadata: {
                ...file.metadata,
                name: response.filename
              }
            }
          : file
      )
    )
    
    setUploadStatus(prev => ({
      ...prev,
      status: prev.completedFiles + 1 + prev.failedFiles >= prev.totalFiles ? 'completed' : 'uploading',
      completedFiles: prev.completedFiles + 1,
      progress: Math.round(((prev.completedFiles + 1) / prev.totalFiles) * 100)
    }))
  }, [])

  // Mark upload as failed
  const setUploadFailed = useCallback((fileId: string, error: string) => {
    setFiles(prev => 
      prev.map(file => 
        file.id === fileId 
          ? { ...file, status: 'failed' as const, error }
          : file
      )
    )
    
    setUploadStatus(prev => ({
      ...prev,
      status: prev.completedFiles + prev.failedFiles + 1 >= prev.totalFiles ? 'failed' : 'uploading',
      failedFiles: prev.failedFiles + 1,
      progress: Math.round(((prev.completedFiles + prev.failedFiles + 1) / prev.totalFiles) * 100)
    }))
  }, [])

  // Derive computed values
  const supportedFiles = Array.from(files)
    .filter((file: AttachedFile) => isSupportedMimeType(file.file.type) && file.status !== 'removed')
    .map((file: AttachedFile) => file.file)

  const pendingFiles = Array.from(files)
    .filter((file: AttachedFile) => file.status === 'pending')
    .map((file: AttachedFile) => file.file)

  const uploadedFiles = Array.from(files)
    .filter((file: AttachedFile) => file.status === 'uploaded' && Boolean(file.backendFileId))
    .map((file: AttachedFile) => ({
      file_id: file.backendFileId as string,
      filename: file.metadata.name,
      file_type: file.metadata.type.split('/')[0] as 'pdf' | 'image' | 'audio',
      size: file.metadata.size,
      upload_timestamp: new Date()
    }))

  const failedFiles = Array.from(files).filter((file: AttachedFile) => file.status === 'failed')

  return {
    files,
    uploadStatus,
    validationError,
    addFiles,
    removeFile,
    clearFiles,
    retryFile,
    validateFiles,
    setUploadProgress,
    setUploadComplete,
    setUploadFailed,
    canAddMoreFiles,
    supportedFiles,
    pendingFiles,
    uploadedFiles,
    failedFiles
  }
}
