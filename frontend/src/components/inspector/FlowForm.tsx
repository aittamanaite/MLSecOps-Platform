import { useState } from 'react'
import { FIELD_UNITS, FLOW_FIELD_GROUPS, type FlowItem } from '../../api/types'

interface FlowFormProps {
  value: FlowItem
  onChange: (value: FlowItem) => void
}

function fieldLabel(field: string): string {
  return field
    .replace(/_/g, ' ')
    .replace(/\bs\b$/, '/s')
    .replace(/^./, (c) => c.toUpperCase())
}

/** Grouped accordion form for the 33 FlowItem fields (§8.3). */
export function FlowForm({ value, onChange }: FlowFormProps) {
  const [openGroup, setOpenGroup] = useState<string>(FLOW_FIELD_GROUPS[0].label)

  function updateField(field: keyof FlowItem, raw: string) {
    const parsed = raw === '' ? 0 : Number(raw)
    onChange({ ...value, [field]: Number.isNaN(parsed) ? 0 : parsed })
  }

  return (
    <div className="flex flex-col gap-2">
      {FLOW_FIELD_GROUPS.map((group) => {
        const isOpen = openGroup === group.label
        return (
          <div key={group.label} className="rounded-panel border border-hairline bg-panel">
            <button
              type="button"
              onClick={() => setOpenGroup(isOpen ? '' : group.label)}
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm text-primary"
            >
              <span>{group.label}</span>
              <span className="text-secondary">{isOpen ? '−' : '+'}</span>
            </button>
            {isOpen && (
              <div className="grid grid-cols-1 gap-3 border-t border-hairline p-4 sm:grid-cols-2">
                {group.fields.map((field) => (
                  <label key={field} className="flex flex-col gap-1 text-xs text-secondary">
                    {fieldLabel(field)}
                    <input
                      type="number"
                      step="any"
                      value={value[field]}
                      onChange={(e) => updateField(field, e.target.value)}
                      placeholder={FIELD_UNITS[field] ?? '0'}
                      className="rounded-input border border-hairline bg-panel-raised px-3 py-2 font-mono text-sm text-primary outline-none focus:border-accent"
                    />
                  </label>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
