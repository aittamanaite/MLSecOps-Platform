import { useMemo, useState } from 'react'
import { Dropzone, type ParsedCsv } from '../components/batch/Dropzone'
import { ColumnMapper } from '../components/batch/ColumnMapper'
import { ResultsTable } from '../components/batch/ResultsTable'
import { useBatchPredict } from '../hooks/useBatchPredict'
import { useSession } from '../context/SessionContext'
import { useDetectionsLog } from '../hooks/useDetectionsLog'
import { FLOW_FIELD_GROUPS, isAttack, type FlowItem } from '../api/types'

const ALL_FIELDS = FLOW_FIELD_GROUPS.flatMap((g) => g.fields)

function headersMatch(headers: string[]): boolean {
  const set = new Set(headers.map((h) => h.trim()))
  return ALL_FIELDS.every((f) => set.has(f))
}


function safeNumber(raw: string | undefined): number {
  const n = Number(raw)
  return Number.isFinite(n) ? n : 0
}

function rowsToFlows(rows: Record<string, string>[], mapping: Record<string, keyof FlowItem>): FlowItem[] {
  return rows.map((row) => {
    const flow = {} as FlowItem
    for (const [csvCol, field] of Object.entries(mapping)) {
      flow[field] = safeNumber(row[csvCol])
    }
    return flow
  })
}

function directRowsToFlows(rows: Record<string, string>[]): FlowItem[] {
  return rows.map((row) => {
    const flow = {} as FlowItem
    for (const field of ALL_FIELDS) {
      flow[field] = safeNumber(row[field])
    }
    return flow
  })
}

export function BatchPage() {
  const [csv, setCsv] = useState<ParsedCsv | null>(null)
  const [flows, setFlows] = useState<FlowItem[] | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const batch = useBatchPredict()
  const session = useSession()
  const { addDetection } = useDetectionsLog()

  const needsMapping = useMemo(() => csv !== null && !headersMatch(csv.headers), [csv])

  function handleParsed(parsed: ParsedCsv) {
    setCsv(parsed)
    batch.reset()
    setToast(null)
    if (headersMatch(parsed.headers)) {
      setFlows(directRowsToFlows(parsed.rows))
    } else {
      setFlows(null)
    }
  }

  function handleMappingConfirmed(mapping: Record<string, keyof FlowItem>) {
    if (!csv) return
    setFlows(rowsToFlows(csv.rows, mapping))
  }

  async function handleRun() {
    if (!flows) return
    const results = await batch.run(flows)
    if (!results) return

    let attackCount = 0
    for (let i = 0; i < results.length; i++) {
      const r = results[i]
      // FIX: was `r.is_anomaly` directly (always truthy — see api/types.ts).
      const attack = isAttack(r)
      session.recordPrediction({ isAnomaly: attack, confidence: r.confidence, inferenceMs: 0 })
      if (attack) {
        attackCount += 1
        addDetection({ source: 'Batch', isAnomaly: true, confidence: r.confidence, payload: flows[i] })
      }
    }
    const skippedNote = batch.failedCount > 0 ? ` (${batch.failedCount} rows skipped — invalid data)` : ''
    setToast(`Batch complete: ${results.length} processed, ${attackCount} attacks found.${skippedNote}`)
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg text-primary">Batch analyzer</h1>

      <Dropzone onParsed={handleParsed} />

      {needsMapping && csv && <ColumnMapper csvHeaders={csv.headers} onConfirm={handleMappingConfirmed} />}

      {flows && !batch.results && (
        <div className="flex items-center justify-between rounded-panel border border-hairline bg-panel p-4">
          <span className="text-sm text-secondary">{flows.length} rows parsed</span>
          <button
            onClick={handleRun}
            disabled={batch.running}
            className="rounded-input bg-accent px-4 py-2 text-sm text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          >
            {batch.running ? 'Running batch…' : 'Run batch'}
          </button>
        </div>
      )}

      {batch.running && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel-raised">
          <div
            className="h-full bg-accent transition-all duration-150"
            style={{ width: `${(batch.completed / Math.max(batch.total, 1)) * 100}%` }}
          />
        </div>
      )}

      {batch.error && (
        <div className="rounded-panel border border-critical/40 bg-critical-bg p-4 text-sm text-critical">
          Batch failed: {batch.error.message}
        </div>
      )}

      {batch.results && <ResultsTable results={batch.results} />}

      {toast && (
        <div className="fixed bottom-6 right-6 rounded-panel border border-hairline bg-panel-raised px-4 py-3 text-sm text-primary shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
