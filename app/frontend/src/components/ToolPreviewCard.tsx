import { useState } from 'react'
import { api } from '../api'

interface Props {
  tool: string
  args: Record<string, unknown>
}

type Status = 'idle' | 'running' | 'done' | 'error'

const TOOL_TITLE: Record<string, string> = {
  advance_claim: 'Claim decision',
  create_nudge_campaign: 'Draft nudge campaign',
  save_view: 'Save view',
}

const TOOL_ICON: Record<string, string> = {
  advance_claim: '✓',
  create_nudge_campaign: '✉',
  save_view: '★',
}

export default function ToolPreviewCard({ tool, args }: Props) {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function confirm() {
    setStatus('running')
    setError(null)
    try {
      if (tool === 'advance_claim') {
        const r = await api.advanceClaim(
          args.claim_id as string,
          args.decision as 'Approve' | 'Reject',
          args.note as string | undefined,
          args.rejection_code as string | undefined,
        )
        setResult(`${r.claim_id} → ${r.status}`)
      } else if (tool === 'create_nudge_campaign') {
        const r = await api.createNudgeCampaign(
          args.template_id as string,
          (args.dealer_ids as string[]) ?? [],
          args.deadline as string | undefined,
          args.notes as string | undefined,
        )
        setResult(`Drafted ${r.campaign_code ?? r.campaign_id.slice(0, 8)} (${r.recipient_count} recipients)`)
      } else if (tool === 'save_view') {
        const r = await api.saveView(
          args.name as string,
          (args.filter_payload as Record<string, unknown>) ?? {},
          args.description as string | undefined,
          args.pinned as boolean | undefined,
        )
        setResult(`Saved as '${r.name}'`)
      } else {
        throw new Error(`Unknown tool: ${tool}`)
      }
      setStatus('done')
    } catch (e) {
      setError(String(e))
      setStatus('error')
    }
  }

  function cancel() {
    setStatus('done')
    setResult('Cancelled.')
  }

  const title = TOOL_TITLE[tool] ?? tool
  const icon = TOOL_ICON[tool] ?? '⚙'

  return (
    <div className="tool-preview">
      <div className="tool-preview-head">
        <span className="tool-preview-icon">{icon}</span>
        <span className="tool-preview-title">{title}</span>
        <span className="tool-preview-badge">action</span>
      </div>
      <table className="tool-preview-args">
        <tbody>
          {Object.entries(args).map(([k, v]) => (
            <tr key={k}>
              <td className="tool-preview-key">{k}</td>
              <td className="tool-preview-val">
                {Array.isArray(v) ? v.join(', ') : typeof v === 'object' && v !== null
                  ? JSON.stringify(v)
                  : String(v)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {status === 'idle' && (
        <div className="tool-preview-actions">
          <button className="primary" onClick={confirm}>Confirm</button>
          <button onClick={cancel}>Cancel</button>
        </div>
      )}
      {status === 'running' && <div className="tool-preview-status">Executing…</div>}
      {status === 'done' && result && <div className="tool-preview-status done">✓ {result}</div>}
      {status === 'error' && error && <div className="tool-preview-status err">✗ {error}</div>}
    </div>
  )
}
