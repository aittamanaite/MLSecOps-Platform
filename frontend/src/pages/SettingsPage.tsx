import { useState } from 'react'
import { getApiBaseUrl, setApiBaseUrl } from '../api/client'
import { getHealth } from '../api/endpoints'

export function SettingsPage() {
  const [url, setUrl] = useState(getApiBaseUrl())
  const [testResult, setTestResult] = useState<'idle' | 'testing' | 'pass' | 'fail'>('idle')
  const [saved, setSaved] = useState(false)

  async function handleTest() {
    setTestResult('testing')
    try {
      await getHealth()
      setTestResult('pass')
    } catch {
      setTestResult('fail')
    }
  }

  function handleSave() {
    setApiBaseUrl(url)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="flex max-w-md flex-col gap-4">
      <h1 className="text-lg text-primary">Settings</h1>

      <label className="flex flex-col gap-1 text-xs text-secondary">
        API base URL
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="http://localhost:8000"
          className="rounded-input border border-hairline bg-panel-raised px-3 py-2 font-mono text-sm text-primary outline-none focus:border-accent"
        />
      </label>

      <div className="flex items-center gap-3">
        <button
          onClick={handleTest}
          className="rounded-input border border-hairline px-3 py-2 text-sm text-secondary transition-colors hover:text-primary"
        >
          Test connection
        </button>
        {testResult === 'testing' && <span className="text-xs text-secondary">Testing…</span>}
        {testResult === 'pass' && <span className="text-xs text-benign">Connected</span>}
        {testResult === 'fail' && <span className="text-xs text-critical">Could not reach API</span>}
      </div>

      <button
        onClick={handleSave}
        className="w-full rounded-input bg-accent py-2.5 text-sm text-white transition-colors"
      >
        {saved ? 'Saved' : 'Save changes'}
      </button>
    </div>
  )
}
