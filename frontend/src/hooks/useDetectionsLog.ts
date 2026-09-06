import { useCallback, useEffect, useState } from 'react'
import type { FlowItem } from '../api/types'

export type DetectionSource = 'Inspector' | 'Batch'

export interface Detection {
  id: string
  source: DetectionSource
  isAnomaly: boolean
  confidence: number
  timestamp: string
  payload: FlowItem
}

const STORAGE_KEY = 'mlsecops:detections'
const NEW_DETECTION_WINDOW_MS = 5_000

function readLog(): Detection[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Detection[]) : []
  } catch {
    return []
  }
}

function writeLog(entries: Detection[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
}


export function useDetectionsLog() {
  const [detections, setDetections] = useState<Detection[]>(() => readLog())

  useEffect(() => {
    function onExternalUpdate() {
      setDetections(readLog())
    }
    window.addEventListener('mlsecops:detections-updated', onExternalUpdate)
    return () => window.removeEventListener('mlsecops:detections-updated', onExternalUpdate)
  }, [])

  const addDetection = useCallback(
    (entry: Omit<Detection, 'id' | 'timestamp'>) => {
      const record: Detection = {
        ...entry,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date().toISOString(),
      }
      const next = [record, ...readLog()]
      writeLog(next)
      setDetections(next)
      window.dispatchEvent(new Event('mlsecops:detections-updated'))
      return record
    },
    [],
  )

  const clearLog = useCallback(() => {
    writeLog([])
    setDetections([])
    window.dispatchEvent(new Event('mlsecops:detections-updated'))
  }, [])

  const isRecent = useCallback((isoTimestamp: string) => {
    return Date.now() - new Date(isoTimestamp).getTime() < NEW_DETECTION_WINDOW_MS
  }, [])

  return { detections, addDetection, clearLog, isRecent }
}
