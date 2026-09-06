import { Badge } from '../ui/Badge'
import { ConfidenceGauge } from '../ui/ConfidenceGauge'
import { isAttack, type ApiError, type PredictResponse } from '../../api/types'

interface ResultPanelProps {
  loading: boolean
  result: PredictResponse | null
  error: ApiError | null
  inferenceMs: number | null
  completedAt: Date | null
  onRetry: () => void
}

/** Result panel with the 422 / 503 / 500 error treatments  */
export function ResultPanel({ loading, result, error, inferenceMs, completedAt, onRetry }: ResultPanelProps) {
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center rounded-panel border border-dashed border-hairline text-secondary">
        Running prediction…
      </div>
    )
  }

  if (error) {
    if (error.status === 422) {
      const body = error.body as { detail?: { loc?: string[]; msg?: string }[] } | null
      return (
        <div className="rounded-panel border border-critical/40 bg-critical-bg p-4">
          <p className="text-sm text-critical">One or more fields failed validation.</p>
          <ul className="mt-2 space-y-1 text-xs text-secondary">
            {body?.detail?.map((d, i) => (
              <li key={i} className="font-mono">
                {d.loc?.[d.loc.length - 1] ?? 'field'}: {d.msg ?? 'invalid'}
              </li>
            )) ?? <li>Check the highlighted fields and try again.</li>}
          </ul>
        </div>
      )
    }
    if (error.status === 503) {
      return (
        <div className="rounded-panel border border-warning/40 bg-warning/10 p-4">
          <p className="text-sm text-warning">Model is offline — predictions unavailable.</p>
          <button
            onClick={onRetry}
            className="mt-3 rounded-input border border-warning/50 px-3 py-1.5 text-sm text-warning transition-colors hover:bg-warning/10"
          >
            Retry
          </button>
        </div>
      )
    }
    return (
      <div className="rounded-panel border border-critical/40 bg-critical-bg p-4">
        <p className="text-sm text-critical">Prediction failed. Try again.</p>
        <button
          onClick={onRetry}
          className="mt-3 rounded-input border border-critical/50 px-3 py-1.5 text-sm text-critical transition-colors hover:bg-critical/10"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex h-full items-center justify-center rounded-panel border border-dashed border-hairline p-6 text-center text-sm text-secondary">
        Run a flow to see its classification here.
      </div>
    )
  }


  const attack = isAttack(result)
  const tone = attack ? 'critical' : 'benign'

  return (
    <div className="flex flex-col items-center gap-4 rounded-panel border border-hairline bg-panel p-6">
      <Badge tone={tone} size="lg">
        {attack ? 'Attack' : 'Benign'}
      </Badge>
      <ConfidenceGauge confidence={result.confidence} tone={tone} />
      <div className="flex gap-6 font-mono text-xs text-secondary">
        <span>{inferenceMs}ms inference</span>
        <span>{completedAt?.toLocaleTimeString()}</span>
      </div>
    </div>
  )
}
