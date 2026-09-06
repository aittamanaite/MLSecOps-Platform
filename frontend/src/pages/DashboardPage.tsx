import { Link } from 'react-router-dom'
import { StatCard } from '../components/ui/StatCard'
import { Badge } from '../components/ui/Badge'
import { LiveSignalChart } from '../components/charts/LiveSignalChart'
import { useSession } from '../context/SessionContext'
import { useDetectionsLog } from '../hooks/useDetectionsLog'

function relativeTime(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  return `${Math.round(minutes / 60)}h ago`
}

export function DashboardPage() {
  const stats = useSession()
  const { detections } = useDetectionsLog()

  const attackRate = stats.predictionsCount > 0 ? (stats.attackCount / stats.predictionsCount) * 100 : 0
  const avgConfidence = stats.predictionsCount > 0 ? stats.totalConfidence / stats.predictionsCount : 0
  const avgInference = stats.predictionsCount > 0 ? stats.totalInferenceMs / stats.predictionsCount : 0
  const recentAttacks = detections.filter((d) => d.isAnomaly).slice(0, 5)
  const hasTraffic = stats.predictionsCount > 0
  const benignPct = hasTraffic ? 100 - attackRate : 0

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg text-primary">Dashboard</h1>
        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Predictions this session" value={stats.predictionsCount} />
          <StatCard
            label="Attack rate"
            value={attackRate}
            format={(v) => `${v.toFixed(1)}%`}
            valueClassName={attackRate > 0 ? 'text-critical' : 'text-primary'}
          />
          <StatCard label="Avg. confidence" value={avgConfidence * 100} format={(v) => `${v.toFixed(1)}%`} />
          <StatCard label="Avg. inference time" value={avgInference} format={(v) => `${Math.round(v)}ms`} />
        </div>
        <p className="mt-2 text-[11px] text-tertiary">
          Accumulated this session only — there's no persistent history endpoint yet, so a refresh resets these.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm text-secondary">Live signal</h2>
          <LiveSignalChart points={stats.signalHistory} />
        </div>
        <div>
          <h2 className="mb-2 text-sm text-secondary">Recent detections</h2>
          {recentAttacks.length === 0 ? (
            <div className="flex h-40 items-center justify-center rounded-panel border border-dashed border-hairline p-4 text-center text-sm text-secondary">
              No traffic scored yet — run a flow in Inspector or upload a batch to populate this dashboard.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {recentAttacks.map((d) => (
                <Link
                  key={d.id}
                  to="/alerts"
                  className="flex items-center justify-between rounded-panel border border-hairline bg-panel px-3 py-2 transition-colors hover:bg-panel-raised"
                >
                  <div className="flex items-center gap-3">
                    <Badge tone="critical">Attack</Badge>
                    <span className="font-mono text-xs text-secondary">{(d.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <span className="font-mono text-xs text-tertiary">{relativeTime(d.timestamp)}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-sm text-secondary">Traffic mix</h2>
        {hasTraffic ? (
          <div className="flex h-3 overflow-hidden rounded-full bg-panel-raised">
            <div className="bg-benign" style={{ width: `${benignPct}%` }} />
            <div className="bg-critical" style={{ width: `${attackRate}%` }} />
          </div>
        ) : (
          <div className="flex h-16 items-center justify-center rounded-panel border border-dashed border-hairline text-sm text-secondary">
            No traffic scored yet — run a flow in Inspector or upload a batch to populate this dashboard.
          </div>
        )}
      </div>
    </div>
  )
}
