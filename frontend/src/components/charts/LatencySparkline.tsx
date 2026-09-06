import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts'

interface LatencySparklineProps {
  values: number[] // last 30 /health round-trip times, ms
}

/** Round-trip latency sparkline, last 30 polls (§8.6). */
export function LatencySparkline({ values }: LatencySparklineProps) {
  if (values.length === 0) {
    return <div className="h-16 rounded-panel border border-dashed border-hairline" />
  }

  const data = values.map((v, i) => ({ i, v }))

  return (
    <div className="h-16 rounded-panel border border-hairline bg-panel p-2">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <YAxis hide domain={['auto', 'auto']} />
          <Line
            type="monotone"
            dataKey="v"
            stroke="var(--accent)"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
