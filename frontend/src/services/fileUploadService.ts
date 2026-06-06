/* File Upload Service */
/*
  Service for handling file uploads to backend endpoints
  Based on backend contracts in contracts/file-upload.md
*/

import { config } from '../config'
import type { UploadResponse, UploadErrorResponse } from '../types/api'
import type { UploadedAttachmentReference, ValidationError } from '../types/attachments'
import { 
  normalizeError, 
  FrontendError
} from '../types/errors'

// Endpoint mapping by MIME type
const ENDPOINTS: Record<string, string> = {
  'application/pdf': config.chatEndpoints.ingestPdf,
  'image/jpeg': config.chatEndpoints.ingestImage,
  'image/jpg': config.chatEndpoints.ingestImage,
  'image/png': config.chatEndpoints.ingestImage,
  'image/webp': config.chatEndpoints.ingestImage,
  'audio/mpeg': config.chatEndpoints.ingestAudio,
  'audio/wav': config.chatEndpoints.ingestAudio,
  'audio/ogg': config.chatEndpoints.ingestAudio
}

// Check if MIME type is supported
export function getUploadEndpoint(mimeType: string): string | null {
  return ENDPOINTS[mimeType] || null
}

export function isSupportedMimeType(mimeType: string): boolean {
  return mimeType in ENDPOINTS
}

export function getUploadEndpointByFile(file: File): string | null {
  return getUploadEndpoint(file.type)
}

// Validate file before upload
export function validateFileForUpload(file: File): ValidationError | null {
  if (!isSupportedMimeType(file.type)) {
    return {
      code: 'UNSUPPORTED_TYPE',
      message: `Unsupported file type: ${file.type}`,
      file: file.name
    }
  }

  // Check file size (max 50MB based on common limits)
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    return {
      code: 'FILE_TOO_LARGE',
      message: `File too large. Maximum size is ${maxSize / (1024 * 1024)}MB`,
      file: file.name
    }
  }

  return null
}

// Upload a single file
export async function uploadFile(file: File): Promise<UploadedAttachmentReference> {
  const endpoint = getUploadEndpointByFile(file)
  
  if (!endpoint) {
    const frontendError = normalizeError(new Error(`Unsupported file type: ${file.type}`))
    throw frontendError
  }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const errorData: UploadErrorResponse = await response.json()
      const error = new Error(errorData.error || `Upload failed with status ${response.status}`)
      const frontendError = normalizeError(error)
      throw frontendError
    }

    const result: UploadResponse = await response.json()
    
    return {
      file_id: result.file_id,
      filename: result.filename,
      file_type: result.file_type,
      size: result.size,
      upload_timestamp: new Date(result.upload_timestamp)
    }
  } catch (error) {
    throw normalizeError(error)
  }
}

// Upload multiple files with individual error handling
export async function uploadFiles(files: File[]): Promise<{
  successes: UploadedAttachmentReference[]
  errors: Array<{ file: File; error: FrontendError }>
}> {
  const successes: UploadedAttachmentReference[] = []
  const errors: Array<{ file: File; error: FrontendError }> = []

  // Process uploads sequentially to track individual failures
  for (const file of files) {
    try {
      const result = await uploadFile(file)
      successes.push(result)
    } catch (error) {
      const frontendError = normalizeError(error)
      errors.push({
        file,
        error: frontendError
      })
    }
  }

  return { successes, errors }
}

// Validate file and throw FrontendError if invalid
export function validateAndThrow(file: File): void {
  const validationError = validateFileForUpload(file)
  if (validationError) {
    const frontendError = normalizeError(new Error(validationError.message))
    throw frontendError
  }
}