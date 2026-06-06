import { useState, useEffect, useCallback, useRef } from 'react'
import { BackendStatus } from '../types/status'
import { fetchHealthStatus, createInitialStatus, StatusCheckResult } from '../services/statusService'

const REFRESH_INTERVAL_MS = 30_000

export function useConnectionStatus() {
  const [status, setStatus] = useState<BackendStatus>(createInitialStatus)
  const mountedRef = useRef(true)

  const checkStatus = useCallback(async () => {
    try {
      const result: StatusCheckResult = await fetchHealthStatus()
      if (mountedRef.current) {
        setStatus({
          connection: result.connection,
          health: result.health,
          lastUpdated: result.lastUpdated,
          error: result.error
        })
      }
    } catch {
      if (mountedRef.current) {
        setStatus(prev => ({
          ...prev,
          connection: 'disconnected',
          lastUpdated: new Date(),
          error: 'Unexpected error'
        }))
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    checkStatus()

    const interval = setInterval(checkStatus, REFRESH_INTERVAL_MS)
    return () => {
      mountedRef.current = false
      clearInterval(interval)
    }
  }, [checkStatus])

  const refresh = useCallback(() => {
    checkStatus()
  }, [checkStatus])

  return { status, refresh }
}
