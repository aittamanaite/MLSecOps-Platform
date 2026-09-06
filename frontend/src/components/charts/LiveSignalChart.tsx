import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts'
import type { SignalPoint } from '../../context/SessionContext'

interface LiveSignalChartProps {
  points: SignalPoint[]
}

function CustomDot(props: { cx?: number; cy?: number; payload?: SignalPoint }) {
  const { cx, cy, payload } = props
  if (cx === undefined || cy === undefined || !payload) return null
  return (
    <circle
      cx={cx}
      cy={cy}
      r={payload.isAnomaly ? 3.5 : 2}
      fill={payload.isAnomaly ? 'var(--signal-critical)' : 'var(--signal-benign)'}
    />
  )
}


export function LiveSignalChart({ points }: LiveSignalChartProps) {
  const data = points.map((p) => ({ ...p, value: p.isAnomaly ? 1 : p.confidence }))

  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-panel border border-dashed border-hairline text-sm text-secondary">
        No traffic scored yet — run a flow in Inspector or upload a batch to populate this dashboard.
      </div>
    )
  }

  return (
    <div className="h-40 rounded-panel border border-hairline bg-panel p-3">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <YAxis hide domain={[0, 1]} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--signal-benign)"
            strokeWidth={1.5}
            dot={<CustomDot />}
            isAnimationActive
            animationDuration={600}
            animationEasing="ease-out"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
