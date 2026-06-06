/* Status Types */
/*
  TypeScript interfaces for backend health status and connection state
  Based on contracts/status.md and backend capabilities
*/

export type ConnectionStatus = 'connected' | 'degraded' | 'disconnected' | 'loading'

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  database: 'ok' | 'degraded' | 'error' | 'unknown'
  qdrant: 'ok' | 'degraded' | 'error' | 'unknown'
  ollama: 'ok' | 'degraded' | 'error' | 'unknown'
  // Optional fields that may be missing in backend response
  model?: string
  provider?: string
  rag_enabled?: boolean
  ocr_available?: boolean
  gpu_available?: boolean
}

export interface BackendStatus {
  connection: ConnectionStatus
  health: HealthResponse | null
  lastUpdated: Date
  error: string | null
}

export const StatusDisplay = {
  connected: { text: 'Connected', color: 'green' },
  degraded: { text: 'Degraded', color: 'orange' }, 
  disconnected: { text: 'Disconnected', color: 'red' },
  loading: { text: 'Loading...', color: 'gray' }
} as const

export function getConnectionStatus(health: HealthResponse | null): ConnectionStatus {
  if (!health) return 'disconnected'
  
  if (health.status === 'degraded') return 'degraded'
  if (health.database === 'error' || health.qdrant === 'error' || health.ollama === 'error') {
    return 'degraded'
  }
  
  return 'connected'
}

export function getStatusDetails(health: HealthResponse | null): {
  version: string
  database: string
  qdrant: string  
  ollama: string
  model: string
  provider: string
  rag: string
  ocr: string
  gpu: string
} {
  return {
    version: health?.version || 'Unknown',
    database: health?.database ? (health.database === 'ok' ? 'Available' : 'Unavailable') : 'Unknown',
    qdrant: health?.qdrant ? (health.qdrant === 'ok' ? 'Available' : 'Unavailable') : 'Unknown',
    ollama: health?.ollama ? (health.ollama === 'ok' ? 'Available' : 'Unavailable') : 'Unknown',
    model: health?.model || 'Unknown',
    provider: health?.provider || 'Unknown', 
    rag: health?.rag_enabled !== undefined ? (health.rag_enabled ? 'Enabled' : 'Disabled') : 'Unknown',
    ocr: health?.ocr_available !== undefined ? (health.ocr_available ? 'Available' : 'Unavailable') : 'Unknown',
    gpu: health?.gpu_available !== undefined ? (health.gpu_available ? 'Available' : 'Unavailable') : 'Unknown'
  }
}