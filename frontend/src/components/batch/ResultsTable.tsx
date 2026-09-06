import { useMemo, useState } from 'react'
import { Badge } from '../ui/Badge'
import { isAttack, type PredictResponse } from '../../api/types'

interface ResultsTableProps {
  results: PredictResponse[]
}

type FilterChip = 'all' | 'attacks' | 'benign'
type SortKey = 'row' | 'confidence'

function ConfidenceBar({ confidence, isAnomaly }: { confidence: number; isAnomaly: boolean }) {
  return (
    <div className="h-1.5 w-24 rounded-full bg-panel-raised">
      <div
        className={`h-full rounded-full ${isAnomaly ? 'bg-critical' : 'bg-benign'}`}
        style={{ width: `${Math.round(confidence * 100)}%` }}
      />
    </div>
  )
}

function toCsv(results: PredictResponse[]): string {
  const header = 'row,is_anomaly,confidence\n'
  const rows = results.map((r, i) => `${i + 1},${r.is_anomaly},${r.confidence}`).join('\n')
  return header + rows
}

function downloadCsv(csv: string) {
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'batch-results.csv'
  a.click()
  URL.revokeObjectURL(url)
}

/** Sortable/filterable batch results table with inline confidence bars (§8.4). */
export function ResultsTable({ results }: ResultsTableProps) {
  const [filter, setFilter] = useState<FilterChip>('all')
  const [sortKey, setSortKey] = useState<SortKey>('row')
  const [sortAsc, setSortAsc] = useState(true)

  const indexed = useMemo(() => results.map((r, i) => ({ ...r, row: i + 1 })), [results])

  const filtered = useMemo(() => {
    const byFilter = indexed.filter((r) => {
      if (filter === 'attacks') return isAttack(r)
      if (filter === 'benign') return !isAttack(r)
      return true
    })
    const sorted = [...byFilter].sort((a, b) => {
      const diff = sortKey === 'row' ? a.row - b.row : a.confidence - b.confidence
      return sortAsc ? diff : -diff
    })
    return sorted
  }, [indexed, filter, sortKey, sortAsc])

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((prev) => !prev)
    else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex gap-2">
          {(['all', 'attacks', 'benign'] as FilterChip[]).map((chip) => (
            <button
              key={chip}
              onClick={() => setFilter(chip)}
              className={`rounded-pill border px-3 py-1 text-xs capitalize transition-colors ${
                filter === chip
                  ? 'border-accent text-accent'
                  : 'border-hairline text-secondary hover:text-primary'
              }`}
            >
              {chip}
            </button>
          ))}
        </div>
        <button
          onClick={() => downloadCsv(toCsv(indexed))}
          className="rounded-input border border-hairline px-3 py-1.5 text-xs text-secondary transition-colors hover:text-primary"
        >
          Export results as CSV
        </button>
      </div>
      <div className="overflow-hidden rounded-panel border border-hairline">
        <table className="w-full text-left text-sm">
          <thead className="bg-panel-raised text-xs text-secondary">
            <tr>
              <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort('row')}>
                Row
              </th>
              <th className="px-3 py-2">Outcome</th>
              <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort('confidence')}>
                Confidence
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const attack = isAttack(r)
              return (
              <tr
                key={r.row}
                className="border-t border-hairline bg-panel"
                style={{
                  borderLeft: `3px solid ${attack ? 'var(--signal-critical)' : 'var(--signal-benign)'}`,
                }}
              >
                <td className="px-3 py-2 font-mono text-secondary">{r.row}</td>
                <td className="px-3 py-2">
                  <Badge tone={attack ? 'critical' : 'benign'}>{attack ? 'Attack' : 'Benign'}</Badge>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <ConfidenceBar confidence={r.confidence} isAnomaly={attack} />
                    <span className="font-mono text-xs text-secondary">{(r.confidence * 100).toFixed(1)}%</span>
                  </div>
                </td>
              </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
