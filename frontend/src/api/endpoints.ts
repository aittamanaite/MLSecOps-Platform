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

export async function predictBatch(
  flows: FlowItem[],
  onProgress?: (completed: number, total: number) => void,
): Promise<PredictBatchOutcome> {
  const results: PredictResponse[] = []
  let failedCount = 0

  for (let i = 0; i < flows.length; i += BATCH_CHUNK_SIZE) {
    const chunk = flows.slice(i, i + BATCH_CHUNK_SIZE)
    try {
      const response = await apiRequest<BatchPredictResponse | PredictResponse[]>('/predict/batch', {
        method: 'POST',
        body: chunk,
      })
      const chunkResults = Array.isArray(response) ? response : response.results
      results.push(...chunkResults)
    } catch {
      failedCount += chunk.length
      for (let j = 0; j < chunk.length; j++) {
        results.push({ is_anomaly: 'BENIGN', confidence: 0 })
      }
    }
    onProgress?.(Math.min(i + BATCH_CHUNK_SIZE, flows.length), flows.length)
  }

  return { results, failedCount }
}
