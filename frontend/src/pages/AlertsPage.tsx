import { useMemo, useState } from 'react'
import { DetectionsTable } from '../components/alerts/DetectionsTable'
import { DetailDrawer } from '../components/alerts/DetailDrawer'
import { useDetectionsLog, type Detection, type DetectionSource } from '../hooks/useDetectionsLog'

type SourceFilter = 'all' | DetectionSource

export function AlertsPage() {
  const { detections, clearLog, isRecent } = useDetectionsLog()
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Detection | null>(null)
  const [confirmingClear, setConfirmingClear] = useState(false)

  const filtered = useMemo(() => {
    return detections.filter((d) => {
      if (sourceFilter !== 'all' && d.source !== sourceFilter) return false
      if (!search.trim()) return true
      const needle = search.trim().toLowerCase()
      return Object.values(d.payload).some((v) => String(v).toLowerCase().includes(needle))
    })
  }, [detections, sourceFilter, search])

  function handleClear() {
    if (!confirmingClear) {
      setConfirmingClear(true)
      return
    }
    clearLog()
    setConfirmingClear(false)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg text-primary">Detections log</h1>
        <button
          onClick={handleClear}
          onBlur={() => setConfirmingClear(false)}
          className={`rounded-input border px-3 py-1.5 text-xs transition-colors ${
            confirmingClear
              ? 'border-critical text-critical'
              : 'border-hairline text-secondary hover:text-primary'
          }`}
        >
          {confirmingClear ? 'Click again to confirm' : 'Clear log'}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {(['all', 'Inspector', 'Batch'] as SourceFilter[]).map((chip) => (
          <button
            key={chip}
            onClick={() => setSourceFilter(chip)}
            className={`rounded-pill border px-3 py-1 text-xs transition-colors ${
              sourceFilter === chip ? 'border-accent text-accent' : 'border-hairline text-secondary hover:text-primary'
            }`}
          >
            {chip === 'all' ? 'All sources' : chip}
          </button>
        ))}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search field values…"
          className="ml-auto rounded-input border border-hairline bg-panel-raised px-3 py-1.5 text-xs text-primary outline-none focus:border-accent"
        />
      </div>

      <DetectionsTable detections={filtered} isRecent={isRecent} onSelect={setSelected} />

      <DetailDrawer detection={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
