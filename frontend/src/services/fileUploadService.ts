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

function getUploadErrorMessage(errorData: UploadErrorResponse & { detail?: { message?: string } }): string {
  return errorData.detail?.message || errorData.error || 'Upload failed'
}

// Endpoint mapping by MIME type
const ENDPOINTS: Record<string, string> = {
  'application/pdf': config.chatEndpoints.ingestPdf,
  'image/jpeg': config.chatEndpoints.ingestImage,
  'image/jpg': config.chatEndpoints.ingestImage,
  'image/png': config.chatEndpoints.ingestImage,
  'image/webp': config.chatEndpoints.ingestImage,
  'audio/mpeg': config.chatEndpoints.ingestAudio,
  'audio/mp3': config.chatEndpoints.ingestAudio,
  'audio/mp4': config.chatEndpoints.ingestAudio,
  'audio/m4a': config.chatEndpoints.ingestAudio,
  'audio/x-m4a': config.chatEndpoints.ingestAudio,
  'audio/wav': config.chatEndpoints.ingestAudio,
  'audio/ogg': config.chatEndpoints.ingestAudio,
  'audio/webm': config.chatEndpoints.ingestAudio,
  'video/mp4': config.chatEndpoints.ingestAudio
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
      const error = new Error(getUploadErrorMessage(errorData))
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

export type ProgressCallback = (percent: number) => void

export interface UploadProgressResult extends UploadedAttachmentReference {
  indexing_status?: string
  status_message?: string | null
  groundx_process_id?: string | null
  groundx_bucket_id?: string | null
}

export function uploadFileToEndpoint(
  file: File,
  endpoint: string,
  onProgress: ProgressCallback
): Promise<UploadProgressResult> {
  const formData = new FormData()
  formData.append('file', file)

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', endpoint)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const result: UploadResponse = JSON.parse(xhr.responseText)
          resolve({
            file_id: result.file_id,
            filename: result.filename,
            file_type: result.file_type,
            size: result.size,
            upload_timestamp: new Date(result.upload_timestamp),
            indexing_status: (result as UploadResponse & { indexing_status?: string }).indexing_status,
            status_message: (result as UploadResponse & { status_message?: string | null }).status_message,
            groundx_process_id: (result as UploadResponse & { groundx_process_id?: string | null }).groundx_process_id,
            groundx_bucket_id: (result as UploadResponse & { groundx_bucket_id?: string | null }).groundx_bucket_id,
          })
        } catch {
          reject(normalizeError(new Error('Invalid response from server')))
        }
      } else {
        try {
          const errorData: UploadErrorResponse & { detail?: { message?: string } } = JSON.parse(xhr.responseText)
          reject(normalizeError(new Error(getUploadErrorMessage(errorData))))
        } catch {
          reject(normalizeError(new Error(`Upload failed with status ${xhr.status}`)))
        }
      }
    }

    xhr.onerror = () => reject(normalizeError(new Error('Network error during upload')))
    xhr.send(formData)
  })
}

// Upload a single file with progress tracking via XHR
export function uploadFileWithProgress(
  file: File,
  onProgress: ProgressCallback
): Promise<UploadProgressResult> {
  const endpoint = getUploadEndpointByFile(file)

  if (!endpoint) {
    return Promise.reject(normalizeError(new Error(`Unsupported file type: ${file.type}`)))
  }

  return uploadFileToEndpoint(file, endpoint, onProgress)
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
