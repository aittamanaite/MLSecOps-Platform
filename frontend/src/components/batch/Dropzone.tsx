import Papa from 'papaparse'
import { useRef, useState } from 'react'

export interface ParsedCsv {
  headers: string[]
  rows: Record<string, string>[]
}

interface DropzoneProps {
  onParsed: (csv: ParsedCsv) => void
}


export function Dropzone({ onParsed }: DropzoneProps) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [fileSizeLabel, setFileSizeLabel] = useState<string | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [rowsSoFar, setRowsSoFar] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  function formatSize(bytes: number): string {
    if (bytes > 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`
    if (bytes > 1_000) return `${(bytes / 1_000).toFixed(0)} KB`
    return `${bytes} B`
  }

  function parseFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Only .csv files are supported.')
      return
    }
    setError(null)
    setFileName(file.name)
    setFileSizeLabel(formatSize(file.size))
    setIsParsing(true)
    setRowsSoFar(0)

    let headers: string[] = []
    const rows: Record<string, string>[] = []

    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      worker: true, 
      chunk: (results) => {
        if (headers.length === 0 && results.meta.fields) {
          headers = results.meta.fields
        }

        for (let i = 0; i < results.data.length; i++) {
          rows.push(results.data[i])
        }
        setRowsSoFar(rows.length)
      },
      complete: () => {
        setIsParsing(false)
        onParsed({ headers, rows })
      },
      error: (err) => {
        setIsParsing(false)
        setError(err.message)
      },
    })
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const file = e.dataTransfer.files[0]
          if (file) parseFile(file)
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-panel border border-dashed p-10 text-center transition-colors duration-150 ${
          dragOver ? 'border-accent bg-accent/5' : 'border-hairline'
        }`}
      >
        {isParsing ? (
          <div className="flex flex-col items-center gap-2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <p className="text-sm text-primary">Parsing {fileName}…</p>
            <p className="text-xs text-secondary">{rowsSoFar.toLocaleString()} rows read so far</p>
          </div>
        ) : fileName ? (
          <div className="flex flex-col items-center gap-1">
            <p className="text-sm text-primary">{fileName}</p>
            <p className="text-xs text-secondary">{fileSizeLabel} — click or drop to replace</p>
          </div>
        ) : (
          <>
            <p className="text-sm text-primary">Drop a CSV file here, or click to browse</p>
            <p className="mt-1 text-xs text-secondary">Headers should match the 33 FlowItem fields</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) parseFile(file)
          }}
        />
      </div>
      {error && <p className="mt-2 text-xs text-critical">{error}</p>}
    </div>
  )
}
