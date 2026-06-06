import { config } from '../config'
import {
  ConnectionStatus,
  HealthResponse,
  BackendStatus,
  getConnectionStatus,
  getStatusDetails
} from '../types/status'

export interface StatusCheckResult {
  connection: ConnectionStatus
  health: HealthResponse | null
  details: ReturnType<typeof getStatusDetails>
  lastUpdated: Date
  error: string | null
}

const UNAVAILABLE_DETAILS = {
  version: 'Unavailable',
  database: 'Unavailable',
  qdrant: 'Unavailable',
  ollama: 'Unavailable',
  model: 'Unavailable',
  provider: 'Unavailable',
  rag: 'Unavailable',
  ocr: 'Unavailable',
  gpu: 'Unavailable'
} as const

function mapBackendValue(value: string | undefined | null): 'ok' | 'degraded' | 'error' | 'unknown' {
  if (!value) return 'unknown'
  if (value === 'connected' || value === 'ok') return 'ok'
  if (value === 'disconnected' || value === 'error') return 'error'
  if (value === 'collection_missing' || value === 'degraded') return 'degraded'
  return 'unknown'
}

function parseHealthResponse(raw: Record<string, unknown>): HealthResponse {
  return {
    status: (raw.status as 'ok' | 'degraded') || 'degraded',
    version: typeof raw.version === 'string' ? raw.version : 'Unknown',
    database: mapBackendValue(raw.database as string | undefined),
    qdrant: mapBackendValue(raw.qdrant as string | undefined),
    ollama: mapBackendValue(raw.ollama as string | undefined),
    model: typeof raw.model === 'string' ? raw.model : undefined,
    provider: typeof raw.provider === 'string' ? raw.provider : undefined,
    rag_enabled: typeof raw.rag_enabled === 'boolean' ? raw.rag_enabled : undefined,
    ocr_available: typeof raw.ocr_available === 'boolean' ? raw.ocr_available : undefined,
    gpu_available: typeof raw.gpu_available === 'boolean' ? raw.gpu_available : undefined
  }
}

export async function fetchHealthStatus(): Promise<StatusCheckResult> {
  const lastUpdated = new Date()

  try {
    const url = `${config.backendBaseUrl}${config.chatEndpoints.health}`
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    })

    if (!response.ok) {
      return {
        connection: 'disconnected',
        health: null,
        details: UNAVAILABLE_DETAILS,
        lastUpdated,
        error: `Server returned ${response.status}`
      }
    }

    const raw = await response.json() as Record<string, unknown>
    const health = parseHealthResponse(raw)
    const connection = getConnectionStatus(health)

    return {
      connection,
      health,
      details: getStatusDetails(health),
      lastUpdated,
      error: null
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network error'
    return {
      connection: 'disconnected',
      health: null,
      details: UNAVAILABLE_DETAILS,
      lastUpdated,
      error: message
    }
  }
}

export function createInitialStatus(): BackendStatus {
  return {
    connection: 'loading',
    health: null,
    lastUpdated: new Date(),
    error: null
  }
}
