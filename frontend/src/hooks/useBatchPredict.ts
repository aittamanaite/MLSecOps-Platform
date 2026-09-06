import { useCallback, useState } from 'react'
import { predictBatch } from '../api/endpoints'
import { ApiError, type FlowItem, type PredictResponse } from '../api/types'

export interface BatchPredictState {
  running: boolean
  completed: number
  total: number
  results: PredictResponse[] | null

  failedCount: number
  error: ApiError | null
}

/** Batch prediction hook used by the Batch Analyzer page . Chunks under the hood. */
export function useBatchPredict() {
  const [state, setState] = useState<BatchPredictState>({
    running: false,
    completed: 0,
    total: 0,
    results: null,
    failedCount: 0,
    error: null,
  })

  const run = useCallback(async (flows: FlowItem[]) => {
    setState({ running: true, completed: 0, total: flows.length, results: null, failedCount: 0, error: null })
    try {
      const { results, failedCount } = await predictBatch(flows, (completed, total) => {
        setState((prev) => ({ ...prev, completed, total }))
      })
      setState({ running: false, completed: flows.length, total: flows.length, results, failedCount, error: null })
      return results
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError('Unexpected error', 0, null)
      setState((prev) => ({ ...prev, running: false, error: apiError }))
      return null
    }
  }, [])

  const reset = useCallback(() => {
    setState({ running: false, completed: 0, total: 0, results: null, failedCount: 0, error: null })
  }, [])

  return { ...state, run, reset }
}
