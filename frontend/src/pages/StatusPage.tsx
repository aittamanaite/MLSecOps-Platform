import { useState } from 'react'
import { useHealth } from '../hooks/useHealth'
import { LatencySparkline } from '../components/charts/LatencySparkline'
import { apiRequest, getApiBaseUrl } from '../api/client'

const STATUS_COPY: Record<string, { label: string; color: string }> = {
  operational: { label: 'Operational', color: 'text-benign' },
  degraded: { label: 'Degraded', color: 'text-warning' },
  unreachable: { label: 'Unreachable', color: 'text-critical' },
  checking: { label: 'Checking…', color: 'text-secondary' },
}

export function StatusPage() {
  const health = useHealth()
  const [metrics, setMetrics] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [loadingMetrics, setLoadingMetrics] = useState(false)

  // const base = getApiBaseUrl().replace(/\/$/, '').replace(/^https?:\/\//, '')
  const apiBase = getApiBaseUrl() || 'http://localhost:8000'
  const base = apiBase.replace(/\/$/, '').replace(/^https?:\/\//, '')
  const host = base.split(':')[0]

  async function handleExpand() {
    const next = !expanded
    setExpanded(next)
    if (next && metrics === null) {
      setLoadingMetrics(true)
      try {
        const text = await apiRequest<string>('/metrics')
        setMetrics(text)
      } catch {
        setMetrics('Failed to load /metrics.')
      } finally {
        setLoadingMetrics(false)
      }
    }
  }

  const copy = STATUS_COPY[health.status]

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg text-primary">System status</h1>

      <div className="rounded-panel border border-hairline bg-panel p-6">
        <div className="flex items-center gap-3">
          <span
            className={`h-3 w-3 rounded-full ${
              health.status === 'operational'
                ? 'bg-benign animate-heartbeat'
                : health.status === 'degraded'
                  ? 'bg-warning'
                  : 'bg-critical'
            }`}
          />
          <span className={`text-2xl ${copy.color}`}>{copy.label}</span>
        </div>
        <div className="mt-3 flex gap-6 font-mono text-xs text-secondary">
          <span>model_loaded: {String(health.modelLoaded)}</span>
          <span>last check: {health.lastCheckedAt?.toLocaleTimeString() ?? '—'}</span>
        </div>
        <div className="mt-4">
          <p className="mb-1 text-xs text-secondary">Round-trip latency (last 30 polls)</p>
          <LatencySparkline values={health.latencyHistory} />
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs text-secondary">Ops tools — not part of this app</p>
        <div className="flex gap-3">
          <a
            href={`http://${host}:9090`}
            target="_blank"
            rel="noreferrer"
            className="flex-1 rounded-panel border border-hairline bg-panel p-4 text-sm text-primary transition-colors hover:bg-panel-raised"
          >
            Prometheus
            <div className="mt-1 font-mono text-xs text-secondary">:9090</div>
          </a>
          <a
            href={`http://${host}:3001`}
            target="_blank"
            rel="noreferrer"
            className="flex-1 rounded-panel border border-hairline bg-panel p-4 text-sm text-primary transition-colors hover:bg-panel-raised"
          >
            Grafana
            <div className="mt-1 font-mono text-xs text-secondary">:3001</div>
          </a>
        </div>
      </div>

      <div>
        <button onClick={handleExpand} className="text-xs text-secondary hover:text-primary">
          {expanded ? '▾' : '▸'} Raw metrics (GET /metrics)
        </button>
        {expanded && (
          <pre className="mt-2 max-h-80 overflow-auto rounded-panel border border-hairline bg-panel-raised p-3 text-[11px] text-secondary">
            {loadingMetrics ? 'Loading…' : metrics}
          </pre>
        )}
      </div>
    </div>
  )
}
