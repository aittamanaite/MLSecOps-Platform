import { useEffect, useRef, useState } from 'react'

interface StatCardProps {
  label: string
  value: number
  format?: (value: number) => string
  valueClassName?: string
  caption?: string
}

const COUNT_UP_MS = 400

/** Dashboard KPI card. Value counts up from 0 on first mount (§8.2). */
export function StatCard({ label, value, format, valueClassName, caption }: StatCardProps) {
  const [display, setDisplay] = useState(0)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    let raf: number
    function tick(now: number) {
      if (startRef.current === null) startRef.current = now
      const elapsed = now - startRef.current
      const progress = Math.min(elapsed / COUNT_UP_MS, 1)
      setDisplay(value * progress)
      if (progress < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // Intentionally only re-runs when the target value changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  const formatted = format ? format(display) : Math.round(display).toString()

  return (
    <div className="rounded-panel border border-hairline bg-panel p-4">
      <div className="text-xs text-secondary">{label}</div>
      <div className={`mt-1 font-mono text-2xl ${valueClassName ?? 'text-primary'}`}>{formatted}</div>
      {caption && <div className="mt-2 text-[11px] text-tertiary">{caption}</div>}
    </div>
  )
}
