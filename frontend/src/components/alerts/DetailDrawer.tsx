import { Badge } from '../ui/Badge'
import type { Detection } from '../../hooks/useDetectionsLog'

interface DetailDrawerProps {
  detection: Detection | null
  onClose: () => void
}

/** Slide-in detail drawer from the right, showing the full 33-field payload  */
export function DetailDrawer({ detection, onClose }: DetailDrawerProps) {
  if (!detection) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-md overflow-y-auto border-l border-hairline bg-panel-raised p-5"
      >
        <div className="flex items-center justify-between">
          <Badge tone={detection.isAnomaly ? 'critical' : 'benign'} size="lg">
            {detection.isAnomaly ? 'Attack' : 'Benign'}
          </Badge>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            Close
          </button>
        </div>
        <div className="mt-3 flex gap-4 font-mono text-xs text-secondary">
          <span>{detection.source}</span>
          <span>{(detection.confidence * 100).toFixed(1)}% confidence</span>
          <span>{new Date(detection.timestamp).toLocaleString()}</span>
        </div>
        <div className="mt-5 rounded-panel border border-hairline">
          <table className="w-full text-left text-xs">
            <tbody>
              {Object.entries(detection.payload).map(([key, val]) => (
                <tr key={key} className="border-b border-hairline last:border-b-0">
                  <td className="px-3 py-1.5 font-mono text-secondary">{key}</td>
                  <td className="px-3 py-1.5 font-mono text-primary">{String(val)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
