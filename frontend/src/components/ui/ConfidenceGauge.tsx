import { useEffect, useState } from 'react'

interface ConfidenceGaugeProps {
  confidence: number // 0..1
  tone: 'benign' | 'critical'
}

const SIZE = 140
const STROKE = 10
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const FILL_MS = 500

/** Radial gauge that fills 0→confidence over 500ms when a result arrives (§8.3). */
export function ConfidenceGauge({ confidence, tone }: ConfidenceGaugeProps) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    setProgress(0)
    const start = performance.now()
    let raf: number
    function tick(now: number) {
      const elapsed = now - start
      const t = Math.min(elapsed / FILL_MS, 1)
      // ease-out
      setProgress(confidence * (1 - Math.pow(1 - t, 3)))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [confidence])

  const dashOffset = CIRCUMFERENCE * (1 - progress)
  const color = tone === 'critical' ? 'var(--signal-critical)' : 'var(--signal-benign)'

  return (
    <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Confidence">
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        stroke="var(--border-hairline)"
        strokeWidth={STROKE}
      />
      <circle
        cx={SIZE / 2}
        cy={SIZE / 2}
        r={RADIUS}
        fill="none"
        stroke={color}
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
      />
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        className="font-mono"
        fill="var(--text-primary)"
        fontSize="22"
      >
        {(progress * 100).toFixed(1)}%
      </text>
    </svg>
  )
}
