import { useCallback, useRef, useState } from 'react'
import { predictBatch } from '../api/endpoints'
import { ApiError, type FlowItem, type PredictResponse } from '../api/types'

export interface BatchPredictState {
  running: boolean
  completed: number
  total: number
  results: PredictResponse[] | null
  failedCount: number
  error: ApiError | null
  cancelled: boolean
}

/** Batch prediction hook. Chunks under the hood, and now supports real cancellation via AbortController. */
export function useBatchPredict() {
  const [state, setState] = useState<BatchPredictState>({
    running: false,
    completed: 0,
    total: 0,
    results: null,
    failedCount: 0,
    error: null,
    cancelled: false,
  })
  const controllerRef = useRef<AbortController | null>(null)

  const run = useCallback(async (flows: FlowItem[]) => {
    const controller = new AbortController()
    controllerRef.current = controller

    setState({
      running: true,
      completed: 0,
      total: flows.length,
      results: null,
      failedCount: 0,
      error: null,
      cancelled: false,
    })

    try {
      const { results, failedCount } = await predictBatch(
        flows,
        (completed, total) => setState((prev) => ({ ...prev, completed, total })),
        controller.signal,
      )
      setState({
        running: false,
        completed: flows.length,
        total: flows.length,
        results,
        failedCount,
        error: null,
        cancelled: false,
      })
      return results
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setState((prev) => ({ ...prev, running: false, cancelled: true }))
        return null
      }
      const apiError = err instanceof ApiError ? err : new ApiError('Unexpected error', 0, null)
      setState((prev) => ({ ...prev, running: false, error: apiError }))
      return null
    } finally {
      controllerRef.current = null
    }
  }, [])

  /** Cancels the in-flight batch — actually aborts the current chunk's request, not just a UI reset. */
  const cancel = useCallback(() => {
    controllerRef.current?.abort()
  }, [])

  const reset = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current = null
    setState({ running: false, completed: 0, total: 0, results: null, failedCount: 0, error: null, cancelled: false })
  }, [])

  return { ...state, run, cancel, reset }
}