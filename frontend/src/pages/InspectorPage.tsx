import { useState } from 'react'
import { FlowForm } from '../components/inspector/FlowForm'
import { FlowJsonEditor } from '../components/inspector/FlowJsonEditor'
import { ResultPanel } from '../components/inspector/ResultPanel'
import { usePredict } from '../hooks/usePredict'
import { useSession } from '../context/SessionContext'
import { useDetectionsLog } from '../hooks/useDetectionsLog'
import { SAMPLE_ATTACK_FLOW, SAMPLE_BENIGN_FLOW } from '../data/sampleFlows'
import { isAttack, type FlowItem } from '../api/types'

type Tab = 'form' | 'json'

export function InspectorPage() {
  const [tab, setTab] = useState<Tab>('form')
  const [flow, setFlow] = useState<FlowItem>(SAMPLE_BENIGN_FLOW)
  const [jsonValid, setJsonValid] = useState(true)
  const predict = usePredict()
  const session = useSession()
  const { addDetection } = useDetectionsLog()

  async function handleSubmit() {

    const { result, inferenceMs } = await predict.run(flow)
    if (!result) return

    const attack = isAttack(result)
    session.recordPrediction({
      isAnomaly: attack,
      confidence: result.confidence,
      inferenceMs: inferenceMs ?? 0,
    })
    if (attack) {
      addDetection({ source: 'Inspector', isAnomaly: true, confidence: result.confidence, payload: flow })
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg text-primary">Flow inspector</h1>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-3">
          <div className="flex gap-2">
            <button
              onClick={() => setFlow(SAMPLE_BENIGN_FLOW)}
              className="rounded-input border border-hairline px-3 py-1.5 text-xs text-secondary transition-colors hover:text-primary"
            >
              Load sample: Benign
            </button>
            <button
              onClick={() => setFlow(SAMPLE_ATTACK_FLOW)}
              className="rounded-input border border-hairline px-3 py-1.5 text-xs text-secondary transition-colors hover:text-primary"
            >
              Load sample: Attack
            </button>
          </div>

          <div className="flex gap-1 border-b border-hairline text-sm">
            {(['form', 'json'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-2 ${tab === t ? 'border-b-2 border-accent text-primary' : 'text-secondary'}`}
              >
                {t === 'form' ? 'Form' : 'Raw JSON'}
              </button>
            ))}
          </div>

          {tab === 'form' ? (
            <FlowForm value={flow} onChange={setFlow} />
          ) : (
            <FlowJsonEditor
              value={flow}
              onValidChange={(v) => {
                setJsonValid(true)
                setFlow(v)
              }}
            />
          )}

          <button
            onClick={handleSubmit}
            disabled={predict.loading || (tab === 'json' && !jsonValid)}
            className="mt-2 w-full rounded-input bg-accent py-2.5 text-sm text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          >
            {predict.loading ? 'Running…' : 'Run prediction'}
          </button>
        </div>

        <ResultPanel
          loading={predict.loading}
          result={predict.result}
          error={predict.error}
          inferenceMs={predict.inferenceMs}
          completedAt={predict.completedAt}
          onRetry={handleSubmit}
        />
      </div>
    </div>
  )
}
