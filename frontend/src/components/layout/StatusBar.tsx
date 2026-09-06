import { useHealth } from '../../hooks/useHealth'
import { getApiBaseUrl } from '../../api/client'

const STATUS_LABEL: Record<string, string> = {
  operational: 'Operational',
  degraded: 'Degraded',
  unreachable: 'Unreachable',
  checking: 'Checking…',
}

const STATUS_DOT: Record<string, string> = {
  operational: 'bg-benign',
  degraded: 'bg-warning',
  unreachable: 'bg-critical',
  checking: 'bg-tertiary',
}


export function StatusBar() {
  const health = useHealth()
  const baseUrl = getApiBaseUrl()

  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-hairline bg-panel px-4">
      <div className="flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${STATUS_DOT[health.status]} ${
            health.status === 'operational' ? 'animate-heartbeat' : ''
          }`}
        />
        <span className="text-sm text-primary">API: {STATUS_LABEL[health.status]}</span>
      </div>
      <div className="flex items-center gap-4 font-mono text-xs text-secondary">
        <span>{baseUrl}</span>
        {health.latencyMs !== null && <span>{health.latencyMs}ms</span>}
      </div>
    </div>
  )
}
