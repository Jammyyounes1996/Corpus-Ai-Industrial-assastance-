/* Attachment Types */
/*
  TypeScript interfaces for file uploads, attachments, and upload handling
  Based on backend contracts in contracts/file-upload.md
*/

export type SupportedMimeType = 
  | 'application/pdf'
  | 'image/jpeg'
  | 'image/jpg' 
  | 'image/png'
  | 'image/webp'
  | 'audio/mpeg'
  | 'audio/wav'
  | 'audio/ogg'

export interface FileMetadata {
  name: string
  size: number
  type: SupportedMimeType
  lastModified: Date
}

export interface AttachedFile {
  id: string
  backendFileId?: string
  file: File
  metadata: FileMetadata
  status: 'pending' | 'uploading' | 'uploaded' | 'failed' | 'removed'
  progress: number // 0-100
  error?: string
  objectUrl?: string
}

export interface UploadedAttachmentReference {
  file_id: string
  filename: string
  file_type: 'pdf' | 'image' | 'audio'
  size: number
  upload_timestamp: Date
}

export interface UploadStatus {
  status: 'idle' | 'validating' | 'uploading' | 'completed' | 'failed'
  progress: number
  totalFiles: number
  completedFiles: number
  failedFiles: number
}

export interface ValidationError {
  code: 'UNSUPPORTED_TYPE' | 'FILE_TOO_LARGE' | 'MAX_FILES_EXCEEDED' | 'UNKNOWN_ERROR'
  message: string
  file?: string
}

export const MAX_ATTACHED_FILES = 10
export const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

export const SUPPORTED_MIME_TYPES: SupportedMimeType[] = [
  'application/pdf',
  'image/jpeg',
  'image/jpg',
  'image/png', 
  'image/webp',
  'audio/mpeg',
  'audio/wav',
  'audio/ogg'
]

export const MIME_TYPE_CATEGORY = {
  PDF: 'application/pdf',
  IMAGE: ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'],
  AUDIO: ['audio/mpeg', 'audio/wav', 'audio/ogg']
} as const

export function getFileCategory(mimeType: SupportedMimeType): 'pdf' | 'image' | 'audio' {
  if (mimeType === MIME_TYPE_CATEGORY.PDF) return 'pdf'
  if (mimeType.startsWith('image/')) return 'image'
  if (mimeType.startsWith('audio/')) return 'audio'
  throw new Error(`Unsupported MIME type: ${mimeType}`)
}

export function isSupportedMimeType(mimeType: string): mimeType is SupportedMimeType {
  return SUPPORTED_MIME_TYPES.includes(mimeType as SupportedMimeType)
}

export function validateFile(file: File): ValidationError | null {
  if (!isSupportedMimeType(file.type)) {
    return {
      code: 'UNSUPPORTED_TYPE',
      message: `File type "${file.type}" is not supported. Supported types: PDF, JPG, PNG, WebP images, MP3, WAV, OGG audio.`,
      file: file.name
    }
  }

  if (file.size > MAX_FILE_SIZE) {
    return {
      code: 'FILE_TOO_LARGE',
      message: `File "${file.name}" is too large. Maximum size is ${Math.round(MAX_FILE_SIZE / (1024 * 1024))}MB.`,
      file: file.name
    }
  }

  return null
}
