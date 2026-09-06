import { useEffect, useRef, useState } from 'react'
import { getHealth } from '../api/endpoints'
import type { HealthResponse } from '../api/types'

export type HealthStatus = 'operational' | 'degraded' | 'unreachable' | 'checking'

export interface HealthPoll {
  status: HealthStatus
  modelLoaded: boolean | null
  latencyMs: number | null
  lastCheckedAt: Date | null
  latencyHistory: number[]
}

const POLL_INTERVAL_MS = 10_000
const HISTORY_LENGTH = 30

/** Polls GET /health every 10s. Used by StatusBar  and the Status page  */
export function useHealth(): HealthPoll {
  const [state, setState] = useState<HealthPoll>({
    status: 'checking',
    modelLoaded: null,
    latencyMs: null,
    lastCheckedAt: null,
    latencyHistory: [],
  })
  const historyRef = useRef<number[]>([])

  useEffect(() => {
    let cancelled = false

    async function poll() {
      const start = performance.now()
      try {
        const health: HealthResponse = await getHealth()
        const latency = Math.round(performance.now() - start)
        if (cancelled) return

        historyRef.current = [...historyRef.current, latency].slice(-HISTORY_LENGTH)
        setState({
          status: health.model_loaded ? 'operational' : 'degraded',
          modelLoaded: health.model_loaded,
          latencyMs: latency,
          lastCheckedAt: new Date(),
          latencyHistory: historyRef.current,
        })
      } catch {
        if (cancelled) return
        setState((prev) => ({
          ...prev,
          status: 'unreachable',
          modelLoaded: null,
          lastCheckedAt: new Date(),
        }))
      }
    }

    poll()
    const interval = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return state
}
