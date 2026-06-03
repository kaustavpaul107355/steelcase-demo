import { useEffect, useState } from 'react'
import {
  api,
  type ClaimReviewRow,
  type Config,
  type Me,
  type NudgeCampaignRow,
  type SavedViewRow,
} from '../api'

type TabId = 'approvals' | 'nudges' | 'saved_views'

interface Props {
  me: Me
  config: Config
}

// Per-role default tab + visible set. Director/Finance get a read-only tour;
// dealers see only saved views; channel_mgr/rmd see the full workbench.
const ROLE_TABS: Record<string, TabId[]> = {
  channel_mgr: ['approvals', 'nudges', 'saved_views'],
  rmd: ['approvals', 'nudges', 'saved_views'],
  director: ['approvals', 'saved_views'],
  finance: ['approvals', 'saved_views'],
  dealer: ['saved_views'],
  guest: ['saved_views'],
}

export default function RightPane({ me, config }: Props) {
  const visibleTabs = (ROLE_TABS[me.role] ?? ROLE_TABS.guest).filter((t) => {
    if (t === 'approvals') return true // gated below by feature flag
    if (t === 'nudges') return true
    return true
  })

  const allTabs: { id: TabId; label: string; gate: keyof Config['features']; phase: string }[] = [
    { id: 'approvals', label: 'Approval Queue', gate: 'approvals', phase: 'Phase 5 (Lakebase)' },
    { id: 'nudges', label: 'Nudges', gate: 'nudges', phase: 'Phase 5 (Lakebase)' },
    { id: 'saved_views', label: 'Saved Views', gate: 'saved_views', phase: '—' },
  ]
  const tabs = allTabs.filter((t) => visibleTabs.includes(t.id))

  const firstEnabled = tabs.find((t) => config.features[t.gate])?.id ?? tabs[0]?.id ?? 'saved_views'
  const [active, setActive] = useState<TabId>(firstEnabled)

  // Reset to first available tab when the visible set changes (persona switch).
  useEffect(() => setActive(firstEnabled), [me.role])

  const readOnly = me.role === 'director' || me.role === 'finance' || me.role === 'dealer'

  return (
    <div className="pane workbench-pane">
      <div className="pane-header">
        Workbench
        {readOnly && <span className="readonly-badge">read-only</span>}
      </div>
      <div className="tabs">
        {tabs.map((t) => {
          const enabled = config.features[t.gate]
          return (
            <div
              key={t.id}
              className={`tab ${active === t.id ? 'active' : ''} ${enabled ? '' : 'disabled'}`}
              onClick={() => enabled && setActive(t.id)}
            >
              {t.label}
            </div>
          )
        })}
      </div>
      <div className="pane-body">
        {active === 'approvals' &&
          (config.features.approvals ? (
            <Approvals readOnly={readOnly} />
          ) : (
            <CoachmarkDisabled phase="Phase 5 (Lakebase)" mode={config.mode} />
          ))}
        {active === 'nudges' &&
          (config.features.nudges ? (
            <Nudges readOnly={readOnly} />
          ) : (
            <CoachmarkDisabled phase="Phase 5 (Lakebase)" mode={config.mode} />
          ))}
        {active === 'saved_views' && (
          <SavedViews persistent={config.features.saved_views_persistent} />
        )}
      </div>
    </div>
  )
}

function CoachmarkDisabled({ phase, mode }: { phase: string; mode: string }) {
  return (
    <div className="coachmark">
      This tab requires <strong>{phase}</strong>. Currently running in <code>{mode}</code>.
    </div>
  )
}

function Approvals({ readOnly }: { readOnly: boolean }) {
  const [rows, setRows] = useState<ClaimReviewRow[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    api.approvals().then(setRows).catch((e) => setErr(String(e)))
  }, [])
  if (err) return <div className="coachmark">{err}</div>
  if (!rows) return <SkeletonList />
  if (rows.length === 0) return <div className="empty">No pending approvals.</div>

  const REJECTION_CODES = [
    'MISSING_PREAPPROVAL',
    'TIER_INELIGIBLE',
    'OFF_BRAND',
    'OUT_OF_REGION',
    'DOC_INCOMPLETE',
    'DOUBLE_DIP',
    'OTHER',
  ]

  async function advance(claim_id: string, decision: 'Approve' | 'Reject') {
    let rejection_code: string | undefined
    if (decision === 'Reject') {
      const input = window.prompt(
        `Rejection code (one of: ${REJECTION_CODES.join(', ')})`,
        'OTHER',
      )
      if (input === null) return
      rejection_code = REJECTION_CODES.includes(input) ? input : 'OTHER'
    }
    await api.advanceClaim(claim_id, decision, undefined, rejection_code)
    api.approvals().then(setRows)
  }

  return (
    <>
      {rows.map((r) => (
        <div key={r.claim_id} className="list-row">
          <div className="row-head">
            <span className="title">{r.claim_id}</span>
            <span className="muted">·</span>
            <span className="muted">{r.dealer_name ?? r.dealer_id}</span>
            <span className={`status-pill status-${r.status.toLowerCase()}`}>{r.status}</span>
          </div>
          <div className="row-meta">created {new Date(r.created_at).toLocaleString()}</div>
          {!readOnly && (
            <div className="row-actions">
              <button className="primary" onClick={() => advance(r.claim_id, 'Approve')}>
                Approve
              </button>
              <button className="danger" onClick={() => advance(r.claim_id, 'Reject')}>
                Reject
              </button>
            </div>
          )}
        </div>
      ))}
    </>
  )
}

function Nudges({ readOnly }: { readOnly: boolean }) {
  const [rows, setRows] = useState<NudgeCampaignRow[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    api.nudges().then(setRows).catch((e) => setErr(String(e)))
  }, [])
  if (err) return <div className="coachmark">{err}</div>
  if (!rows) return <SkeletonList />
  if (rows.length === 0) return <div className="empty">No drafts yet. Ask the agent to generate one.</div>

  async function queue(id: string) {
    await api.queueNudge(id)
    api.nudges().then(setRows)
  }

  return (
    <>
      {rows.map((r) => (
        <div key={r.campaign_id} className="list-row">
          <div className="row-head">
            <span className="title">{r.campaign_code ?? r.campaign_id.slice(0, 8)}</span>
            <span className="muted">·</span>
            <span className="muted">{r.template_id}</span>
            <span className="muted">·</span>
            <span className="muted">{r.recipient_count} recipients</span>
          </div>
          <div className="row-meta">
            <span className={`status-pill status-${r.status.toLowerCase()}`}>{r.status}</span>
            {r.deadline ? ` · deadline ${r.deadline}` : ''}
          </div>
          {r.status === 'Draft' && !readOnly && (
            <div className="row-actions">
              <button className="primary" onClick={() => queue(r.campaign_id)}>
                Queue
              </button>
            </div>
          )}
        </div>
      ))}
    </>
  )
}

function SavedViews({ persistent }: { persistent: boolean }) {
  const [rows, setRows] = useState<SavedViewRow[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    api.savedViews().then(setRows).catch((e) => setErr(String(e)))
  }, [])
  if (err) return <div className="coachmark">{err}</div>
  if (!rows) return <SkeletonList />
  return (
    <>
      {!persistent && (
        <div className="coachmark" style={{ marginBottom: 12 }}>
          Lite mode — saved views are not persisted to Lakebase (Phase 5).
        </div>
      )}
      {rows.length === 0 && <div className="empty">No saved views yet.</div>}
      {rows.map((r) => (
        <div key={r.view_id} className="list-row">
          <div className="row-head">
            <span className="title">{r.name}</span>
            {r.pinned && <span className="badge">pinned</span>}
          </div>
          {r.description && <div className="row-meta">{r.description}</div>}
        </div>
      ))}
    </>
  )
}

function SkeletonList() {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div key={i} className="list-row skeleton-row">
          <div className="skeleton-text wide" />
          <div className="skeleton-text narrow" />
        </div>
      ))}
    </>
  )
}
