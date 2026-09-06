import { Badge } from '../ui/Badge'
import type { Detection } from '../../hooks/useDetectionsLog'

interface DetectionsTableProps {
  detections: Detection[]
  isRecent: (isoTimestamp: string) => boolean
  onSelect: (detection: Detection) => void
}

function relativeTime(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  return `${hours}h ago`
}

/** Newest-first detections table. New rows flash --signal-critical-bg and fade (§8.5). */
export function DetectionsTable({ detections, isRecent, onSelect }: DetectionsTableProps) {
  if (detections.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-panel border border-dashed border-hairline p-10 text-center">
        <p className="text-sm text-secondary">No detections yet — run a flow in Inspector or a batch to populate this log.</p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-panel border border-hairline">
      <table className="w-full text-left text-sm">
        <thead className="bg-panel-raised text-xs text-secondary">
          <tr>
            <th className="px-3 py-2">Source</th>
            <th className="px-3 py-2">Outcome</th>
            <th className="px-3 py-2">Confidence</th>
            <th className="px-3 py-2">Time</th>
          </tr>
        </thead>
        <tbody>
          {detections.map((d) => (
            <tr
              key={d.id}
              onClick={() => onSelect(d)}
              className={`cursor-pointer border-t border-hairline bg-panel transition-colors hover:bg-panel-raised ${
                isRecent(d.timestamp) ? 'animate-row-flash' : ''
              }`}
            >
              <td className="px-3 py-2 text-secondary">{d.source}</td>
              <td className="px-3 py-2">
                <Badge tone={d.isAnomaly ? 'critical' : 'benign'}>{d.isAnomaly ? 'Attack' : 'Benign'}</Badge>
              </td>
              <td className="px-3 py-2 font-mono text-secondary">{(d.confidence * 100).toFixed(1)}%</td>
              <td className="px-3 py-2 font-mono text-xs text-tertiary">{relativeTime(d.timestamp)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
