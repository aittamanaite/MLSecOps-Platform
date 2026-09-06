import { useCallback, useState } from 'react'
import { predict } from '../api/endpoints'
import { ApiError, type FlowItem, type PredictResponse } from '../api/types'

export interface PredictState {
  loading: boolean
  result: PredictResponse | null
  error: ApiError | null
  inferenceMs: number | null
  completedAt: Date | null
}


export function usePredict() {
  const [state, setState] = useState<PredictState>({
    loading: false,
    result: null,
    error: null,
    inferenceMs: null,
    completedAt: null,
  })

  const run = useCallback(async (flow: FlowItem) => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    const start = performance.now()
    try {
      const result = await predict(flow)
      const inferenceMs = Math.round(performance.now() - start)
      setState({
        loading: false,
        result,
        error: null,
        inferenceMs,
        completedAt: new Date(),
      })
      return { result, inferenceMs }
    } catch (err) {
      const apiError =
        err instanceof ApiError ? err : new ApiError('Unexpected error', 0, null)
      setState({
        loading: false,
        result: null,
        error: apiError,
        inferenceMs: null,
        completedAt: null,
      })
      return { result: null, inferenceMs: null }
    }
  }, [])

  const reset = useCallback(() => {
    setState({ loading: false, result: null, error: null, inferenceMs: null, completedAt: null })
  }, [])

  return { ...state, run, reset }
}
