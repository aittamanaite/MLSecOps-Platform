import { apiRequest } from './client'
import type { BatchPredictResponse, FlowItem, HealthResponse, PredictResponse } from './types'

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health')
}

export function predict(flow: FlowItem): Promise<PredictResponse> {
  return apiRequest<PredictResponse>('/predict', { method: 'POST', body: flow })
}

const BATCH_CHUNK_SIZE = 500

export interface PredictBatchOutcome {
  results: PredictResponse[]
  failedCount: number
}

/**
 * FIX: the real batch response shape is
 *   {"predictions": [...], "total_processed": N, "anomalies_found": N}
 * — NOT {"results": [...]} and NOT a bare array. `response.results` was
 * always undefined, so every chunk threw on `results.push(...undefined)`
 * and landed in the catch block below, which silently filled in
 * placeholder BENIGN/0 rows. That's the actual cause of "always benign,
 * always 0 confidence" — not the CSV, not the wrapping fix from before.
 */
export async function predictBatch(
  flows: FlowItem[],
  onProgress?: (completed: number, total: number) => void,
  signal?: AbortSignal,
): Promise<PredictBatchOutcome> {
  const results: PredictResponse[] = []
  let failedCount = 0

  for (let i = 0; i < flows.length; i += BATCH_CHUNK_SIZE) {
    const chunk = flows.slice(i, i + BATCH_CHUNK_SIZE)
    try {
      const response = await apiRequest<BatchPredictResponse>('/predict/batch', {
        method: 'POST',
        body: { flows: chunk },
        signal,
      })
      results.push(...response.predictions)
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') throw err
      failedCount += chunk.length
      for (let j = 0; j < chunk.length; j++) {
        results.push({ is_anomaly: 'BENIGN', confidence: 0 })
      }
    }
    onProgress?.(Math.min(i + BATCH_CHUNK_SIZE, flows.length), flows.length)
  }

  return { results, failedCount }
}
