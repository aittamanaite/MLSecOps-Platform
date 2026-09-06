import { useEffect, useState } from 'react'
import { FLOW_FIELD_GROUPS, type FlowItem } from '../../api/types'

interface FlowJsonEditorProps {
  value: FlowItem
  onValidChange: (value: FlowItem) => void
}


const REQUIRED_FIELDS = FLOW_FIELD_GROUPS.flatMap((group) => group.fields)

function validate(raw: string): { value: FlowItem | null; error: string | null } {
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return { value: null, error: 'Invalid JSON.' }
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return { value: null, error: 'Expected a single JSON object.' }
  }
  const obj = parsed as Record<string, unknown>
  const missing = REQUIRED_FIELDS.filter((field) => typeof obj[field] !== 'number')
  if (missing.length > 0) {
    return { value: null, error: `Missing or non-numeric field(s): ${missing.slice(0, 3).join(', ')}${missing.length > 3 ? '…' : ''}` }
  }
  return { value: obj as unknown as FlowItem, error: null }
}

/** Raw-JSON tab for power users/debugging. Validated against the 33-field schema before Submit enables. */
export function FlowJsonEditor({ value, onValidChange }: FlowJsonEditorProps) {
  const [raw, setRaw] = useState(() => JSON.stringify(value, null, 2))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRaw(JSON.stringify(value, null, 2))
  }, [value])

  function handleChange(next: string) {
    setRaw(next)
    const { value: parsed, error: validationError } = validate(next)
    setError(validationError)
    if (parsed) onValidChange(parsed)
  }

  return (
    <div className="flex flex-col gap-2">
      <textarea
        value={raw}
        onChange={(e) => handleChange(e.target.value)}
        rows={20}
        spellCheck={false}
        className="w-full rounded-panel border border-hairline bg-panel-raised p-3 font-mono text-xs text-primary outline-none focus:border-accent"
      />
      {error && <p className="text-xs text-critical">{error}</p>}
    </div>
  )
}
