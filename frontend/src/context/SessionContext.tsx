import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export interface SignalPoint {
  isAnomaly: boolean
  confidence: number
  at: number // epoch ms
}

interface SessionStats {
  predictionsCount: number
  attackCount: number
  totalConfidence: number
  totalInferenceMs: number
  signalHistory: SignalPoint[]
}

interface SessionContextValue extends SessionStats {
  recordPrediction: (input: { isAnomaly: boolean; confidence: number; inferenceMs: number }) => void
}

const SIGNAL_HISTORY_LENGTH = 50

const SessionContext = createContext<SessionContextValue | null>(null)


export function SessionProvider({ children }: { children: ReactNode }) {
  const [stats, setStats] = useState<SessionStats>({
    predictionsCount: 0,
    attackCount: 0,
    totalConfidence: 0,
    totalInferenceMs: 0,
    signalHistory: [],
  })

  const recordPrediction = useCallback(
    (input: { isAnomaly: boolean; confidence: number; inferenceMs: number }) => {
      setStats((prev) => ({
        predictionsCount: prev.predictionsCount + 1,
        attackCount: prev.attackCount + (input.isAnomaly ? 1 : 0),
        totalConfidence: prev.totalConfidence + input.confidence,
        totalInferenceMs: prev.totalInferenceMs + input.inferenceMs,
        signalHistory: [
          ...prev.signalHistory,
          { isAnomaly: input.isAnomaly, confidence: input.confidence, at: Date.now() },
        ].slice(-SIGNAL_HISTORY_LENGTH),
      }))
    },
    [],
  )

  const value = useMemo(() => ({ ...stats, recordPrediction }), [stats, recordPrediction])

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within a SessionProvider')
  return ctx
}
