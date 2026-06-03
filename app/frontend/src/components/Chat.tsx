import { useEffect, useMemo, useState } from 'react'
import { api, type ChatTurn, type RouteHint } from '../api'
import ToolPreviewCard from './ToolPreviewCard'

interface TabSpec {
  id: RouteHint
  label: string
  blurb: string
  starters: string[]
}

const TABS: TabSpec[] = [
  {
    id: 'auto',
    label: 'Auto',
    blurb: 'Router picks Genie or the Handbook based on your question.',
    starters: [
      "What's my Q4 forfeiture risk?",
      'Top 5 activity types by revenue per co-op dollar in AMER',
      'Can a Silver-tier dealer submit a $25K digital ad claim?',
    ],
  },
  {
    id: 'genie_util',
    label: 'Co-op Utilization & Risk',
    blurb: 'Quantitative — Genie space backed by `coop_program_metrics` + `forfeiture_risk`.',
    starters: [
      'Which AMER East dealers have unused balance > $40K?',
      'FY26 forfeiture risk by region',
      'Top 10 dealers by utilization rate this quarter',
    ],
  },
  {
    id: 'genie_marketing',
    label: 'Marketing Effectiveness',
    blurb: 'Quantitative — Genie space for activity ROI and lift.',
    starters: [
      'Best-performing activity types by revenue per co-op dollar',
      'Programmatic display lift YoY',
      'Which campaigns drove the most sell-through in AMER?',
    ],
  },
  {
    id: 'ka',
    label: 'Handbook (KA)',
    blurb: 'Policy — Agent Bricks Knowledge Assistant over the co-op program handbook.',
    starters: [
      'Can a Silver-tier dealer submit a $25K digital ad claim?',
      'What documentation do I need for an event claim?',
      'How does pre-approval work for over-$10K claims?',
    ],
  },
]

interface SessionState {
  sessionId?: string
  turns: ChatTurn[]
  userTurns: string[]
}

const emptyState = (): SessionState => ({ sessionId: undefined, turns: [], userTurns: [] })

export default function Chat() {
  const [activeTab, setActiveTab] = useState<RouteHint>('auto')
  const [sessions, setSessions] = useState<Record<RouteHint, SessionState>>({
    auto: emptyState(),
    genie_util: emptyState(),
    genie_marketing: emptyState(),
    ka: emptyState(),
  })
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)

  const tab = useMemo(() => TABS.find((t) => t.id === activeTab)!, [activeTab])
  const state = sessions[activeTab]

  async function send(message: string) {
    const m = message.trim()
    if (!m || pending) return
    setDraft('')
    setSessions((s) => ({
      ...s,
      [activeTab]: { ...s[activeTab], userTurns: [...s[activeTab].userTurns, m] },
    }))
    setPending(true)
    try {
      const turn = await api.chat(m, state.sessionId, activeTab)
      setSessions((s) => ({
        ...s,
        [activeTab]: {
          sessionId: turn.session_id,
          userTurns: s[activeTab].userTurns,
          turns: [...s[activeTab].turns, turn],
        },
      }))
    } catch (e) {
      setSessions((s) => ({
        ...s,
        [activeTab]: {
          ...s[activeTab],
          turns: [
            ...s[activeTab].turns,
            {
              session_id: s[activeTab].sessionId || '',
              turn_index: s[activeTab].turns.length,
              route: 'error',
              content: `Request failed: ${e}`,
              citations: [],
            },
          ],
        },
      }))
    } finally {
      setPending(false)
    }
  }

  const items: { role: 'user' | 'assistant'; content: string; turn?: ChatTurn }[] = []
  const max = Math.max(state.userTurns.length, state.turns.length)
  for (let i = 0; i < max; i++) {
    if (state.userTurns[i] !== undefined) items.push({ role: 'user', content: state.userTurns[i] })
    if (state.turns[i] !== undefined)
      items.push({ role: 'assistant', content: state.turns[i].content, turn: state.turns[i] })
  }

  return (
    <div className="pane chat-pane">
      <div className="chat-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`chat-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span className="chat-tab-label">{t.label}</span>
            {sessions[t.id].turns.length > 0 && (
              <span className="chat-tab-count">{sessions[t.id].turns.length}</span>
            )}
          </button>
        ))}
      </div>
      <div className="chat-blurb">{tab.blurb}</div>
      <div className="pane-body chat-body">
        {items.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-title">Try a starter:</div>
            <div className="starter-row">
              {tab.starters.map((s) => (
                <button key={s} className="starter-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="chat-list">
          {items.map((it, i) => (
            <div key={i} className={`bubble ${it.role}`}>
              <div className="bubble-content">{it.content}</div>
              {it.turn && <TurnExtras turn={it.turn} />}
            </div>
          ))}
          {pending && <PendingBubble />}
        </div>
      </div>
      <div className="composer">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(draft)
            }
          }}
          placeholder={
            activeTab === 'ka'
              ? 'Ask a policy or eligibility question…'
              : activeTab === 'auto'
                ? 'Ask anything — utilization, ROI, or policy.'
                : 'Ask a quantitative question…'
          }
          disabled={pending}
        />
        <button onClick={() => send(draft)} disabled={pending || !draft.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}

function PendingBubble() {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [])
  const hint =
    elapsed < 8
      ? 'Thinking…'
      : elapsed < 20
        ? 'Calling Genie / KA — typically 15–25 s.'
        : elapsed < 45
          ? 'Cold warehouse — first Genie query can take ~40 s.'
          : 'Still working… check app logs if this exceeds 60 s.'
  return (
    <div className="bubble assistant pending">
      <div className="bubble-shimmer" />
      <div className="bubble-content">{hint}</div>
      <div className="bubble-elapsed">{elapsed}s</div>
    </div>
  )
}

function TurnExtras({ turn }: { turn: ChatTurn }) {
  return (
    <>
      {turn.tool_preview && (
        <ToolPreviewCard
          tool={turn.tool_preview.tool as string}
          args={(turn.tool_preview.args as Record<string, unknown>) ?? {}}
        />
      )}
      {turn.citations.length > 0 && (
        <div className="citations">
          {turn.citations.map((c) => (
            <span
              key={c.doc_id + (c.section ?? '')}
              className="citation"
              title={c.excerpt ?? ''}
            >
              <span className="citation-dot" />
              {c.doc_id}
              {c.section ? ' ' + c.section : ''}
            </span>
          ))}
        </div>
      )}
      {turn.genie && (turn.genie.query || (turn.genie.rows && turn.genie.rows.length > 0)) && (
        <details className="metric-sql">
          <summary>Show metric & SQL</summary>
          {turn.genie.query && <pre className="sql">{turn.genie.query}</pre>}
          {turn.genie.rows && turn.genie.columns && (
            <table className="result-table">
              <thead>
                <tr>
                  {turn.genie.columns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {turn.genie.rows.slice(0, 20).map((r, i) => (
                  <tr key={i}>
                    {turn.genie!.columns!.map((c) => (
                      <td key={c}>{String(r[c] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </details>
      )}
      {turn.latency_ms != null && (
        <div className="turn-meta">
          <span className={`route-pill route-${turn.route}`}>{turn.route}</span>
          <span>· {turn.latency_ms} ms</span>
          {turn.trace_id && <span>· trace {turn.trace_id.slice(0, 12)}…</span>}
        </div>
      )}
    </>
  )
}
