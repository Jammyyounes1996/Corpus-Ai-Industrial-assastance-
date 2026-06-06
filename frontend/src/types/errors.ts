/* Error Types */
/*
  Unified error handling for frontend applications
  Provides consistent error types and normalization utilities
*/

export type ErrorCategory = 
  | 'unsupported_media'
  | 'payload_too_large'
  | 'validation'
  | 'network'
  | 'backend'
  | 'unknown'

export interface FrontendError {
  category: ErrorCategory
  message: string
  code?: string
  details?: Record<string, unknown>
  timestamp: Date
}

// Error code constants
export const ERROR_CODES = {
  UNSUPPORTED_MEDIA: 'UNSUPPORTED_MEDIA',
  PAYLOAD_TOO_LARGE: 'PAYLOAD_TOO_LARGE',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  NETWORK_ERROR: 'NETWORK_ERROR',
  BACKEND_ERROR: 'BACKEND_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'
} as const

// Create frontend error with category
export function createFrontendError(
  category: ErrorCategory,
  message: string,
  code?: string,
  details?: Record<string, unknown>
): FrontendError {
  return {
    category,
    message,
    code,
    details,
    timestamp: new Date()
  }
}

// Create specific error types
export function createUnsupportedMediaError(message: string, details?: Record<string, unknown>): FrontendError {
  return createFrontendError('unsupported_media', message, ERROR_CODES.UNSUPPORTED_MEDIA, details)
}

export function createPayloadTooLargeError(message: string, details?: Record<string, unknown>): FrontendError {
  return createFrontendError('payload_too_large', message, ERROR_CODES.PAYLOAD_TOO_LARGE, details)
}

export function createValidationError(message: string, details?: Record<string, unknown>): FrontendError {
  return createFrontendError('validation', message, ERROR_CODES.VALIDATION_ERROR, details)
}

export function createNetworkError(message: string, details?: Record<string, unknown>): FrontendError {
  return createFrontendError('network', message, ERROR_CODES.NETWORK_ERROR, details)
}

export function createBackendError(message: string, details?: Record<string, unknown>): FrontendError {
  return createFrontendError('backend', message, ERROR_CODES.BACKEND_ERROR, details)
}

export function createUnknownError(message: string, details?: Record<string, unknown>): FrontendError {
  return createFrontendError('unknown', message, ERROR_CODES.UNKNOWN_ERROR, details)
}

// Normalize various error types into FrontendError
export function normalizeError(error: unknown): FrontendError {
  // Check if it's already a FrontendError by checking the category field
  if (typeof error === 'object' && error !== null && 'category' in error) {
    return error as FrontendError
  }

  if (error instanceof Error) {
    // Handle known error types from our services
    if (error.message.includes('Unsupported file type')) {
      return createUnsupportedMediaError(error.message)
    }
    
    if (error.message.includes('too large')) {
      return createPayloadTooLargeError(error.message)
    }
    
    if (error.message.includes('validation')) {
      return createValidationError(error.message)
    }
    
    if (error.message.includes('Network Error') || error.message.includes('fetch')) {
      return createNetworkError('Network connection failed. Please try again.')
    }
    
    if (error.message.includes('Upload failed') || error.message.includes('status')) {
      return createBackendError(error.message)
    }
  }

  // Handle non-Error objects
  if (typeof error === 'object' && error !== null) {
    const errorMessage = (error as { message?: string }).message || 'Unknown error occurred'
    return createUnknownError(errorMessage)
  }

  // Handle primitive values
  const errorMessage = error instanceof Error ? error.message : String(error)
  return createUnknownError(errorMessage || 'An unknown error occurred')
}

// Helper to extract user-safe message from FrontendError
export function getUserSafeMessage(error: FrontendError): string {
  switch (error.category) {
    case 'unsupported_media':
      return 'This file type is not supported'
    case 'payload_too_large':
      return 'File is too large. Please try a smaller file.'
    case 'validation':
      return error.message || 'Validation failed'
    case 'network':
      return 'Network error. Please check your connection and try again.'
    case 'backend':
      return 'Server error. Please try again later.'
    case 'unknown':
    default:
      return 'An unexpected error occurred'
  }
}