import { useState } from 'react'
import { FLOW_FIELD_GROUPS, type FlowItem } from '../../api/types'

const ALL_FIELDS = FLOW_FIELD_GROUPS.flatMap((g) => g.fields)

interface ColumnMapperProps {
  csvHeaders: string[]
  onConfirm: (mapping: Record<string, keyof FlowItem>) => void
}

function guessMapping(headers: string[]): Record<string, string> {
  const mapping: Record<string, string> = {}
  for (const header of headers) {
    const normalized = header.trim().toLowerCase().replace(/[^a-z0-9]/g, '_')
    const match = ALL_FIELDS.find((field) => field.toLowerCase() === normalized)
    if (match) mapping[header] = match
  }
  return mapping
}

/** Column-mapping step shown when CSV headers don't exactly match the 33 field names */
export function ColumnMapper({ csvHeaders, onConfirm }: ColumnMapperProps) {
  const [mapping, setMapping] = useState<Record<string, string>>(() => guessMapping(csvHeaders))

  const mappedCount = Object.values(mapping).filter(Boolean).length

  function handleConfirm() {
    onConfirm(mapping as Record<string, keyof FlowItem>)
  }

  return (
    <div className="rounded-panel border border-hairline bg-panel p-4">
      <p className="text-sm text-primary">Map CSV columns to FlowItem fields</p>
      <p className="mt-1 text-xs text-secondary">
        {mappedCount} of {ALL_FIELDS.length} required fields mapped
      </p>
      <div className="mt-3 max-h-80 overflow-y-auto rounded-input border border-hairline">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-panel-raised text-secondary">
            <tr>
              <th className="px-3 py-2">CSV column</th>
              <th className="px-3 py-2">Target field</th>
            </tr>
          </thead>
          <tbody>
            {csvHeaders.map((header) => (
              <tr key={header} className="border-t border-hairline">
                <td className="px-3 py-2 font-mono text-secondary">{header}</td>
                <td className="px-3 py-2">
                  <select
                    value={mapping[header] ?? ''}
                    onChange={(e) => setMapping((prev) => ({ ...prev, [header]: e.target.value }))}
                    className="w-full rounded-input border border-hairline bg-panel-raised px-2 py-1 font-mono text-primary"
                  >
                    <option value="">— skip —</option>
                    {ALL_FIELDS.map((field) => (
                      <option key={field} value={field}>
                        {field}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        onClick={handleConfirm}
        disabled={mappedCount < ALL_FIELDS.length}
        className="mt-3 rounded-input bg-accent px-4 py-2 text-sm text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
      >
        Confirm mapping
      </button>
    </div>
  )
}
