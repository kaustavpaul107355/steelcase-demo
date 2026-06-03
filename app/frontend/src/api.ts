/* Tiny typed fetch client for the COMPASS BFF. */

export type Mode = 'lite' | 'standard' | 'full'
export type Role = 'channel_mgr' | 'rmd' | 'director' | 'finance' | 'dealer' | 'guest'
export type RouteHint = 'auto' | 'genie_util' | 'genie_marketing' | 'ka'

export interface Me {
  user_id: string
  email: string
  display_name: string
  role: Role
  region_id: string | null
  default_tier_filter: string | null
  dealer_id: string | null
  mode: Mode
}

export interface Config {
  mode: Mode
  features: Record<string, boolean>
  genie_spaces: Record<string, string>
  ka_endpoint: string
  allow_persona_switch: boolean
}

export interface Persona {
  user_id: string
  email: string
  display_name: string
  role: Role
  region_id?: string | null
  dealer_id?: string | null
}

export interface HomeTile {
  key: string
  label: string
  value: number | string | null
  sub_label?: string | null
  format: 'currency' | 'percent' | 'count' | 'text'
  intent: 'neutral' | 'good' | 'warn' | 'bad'
}

export interface HomeRow {
  primary: string
  secondary?: string | null
  metric?: string | null
  intent: 'neutral' | 'good' | 'warn' | 'bad'
}

export interface HomeResponse {
  role: string
  scope_label: string
  headline: string
  tiles: HomeTile[]
  rows: HomeRow[]
}

export interface Citation {
  doc_id: string
  section?: string | null
  excerpt?: string | null
}

export interface GenieResult {
  space_id: string
  query?: string | null
  rows?: Record<string, unknown>[] | null
  columns?: string[] | null
  description?: string | null
}

export interface ChatTurn {
  session_id: string
  turn_index: number
  route: 'genie' | 'ka' | 'tool' | 'refuse' | 'error'
  content: string
  citations: Citation[]
  genie?: GenieResult | null
  tool_preview?: Record<string, unknown> | null
  trace_id?: string | null
  latency_ms?: number | null
}

export interface ClaimReviewRow {
  claim_id: string
  dealer_id: string
  dealer_name?: string | null
  status: 'Pending' | 'Approved' | 'Rejected' | 'PaidStaged'
  created_at: string
  updated_at: string
}

export interface NudgeCampaignRow {
  campaign_id: string
  campaign_code?: string | null
  created_by: string
  created_at: string
  template_id: string
  deadline?: string | null
  status: 'Draft' | 'Queued' | 'Sent' | 'Cancelled'
  notes?: string | null
  recipient_count: number
}

export interface SavedViewRow {
  view_id: string
  user_id: string
  name: string
  description?: string | null
  filter_payload: Record<string, unknown>
  pinned: boolean
}

const PERSONA_KEY = 'compass.persona.email'

export const personaStore = {
  get(): string | null {
    try { return localStorage.getItem(PERSONA_KEY) } catch { return null }
  },
  set(email: string | null) {
    try {
      if (email) localStorage.setItem(PERSONA_KEY, email)
      else localStorage.removeItem(PERSONA_KEY)
    } catch { /* no-op */ }
  },
}

async function http<T>(input: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init?.headers as Record<string, string>) || {}),
  }
  const persona = personaStore.get()
  if (persona) headers['X-Compass-As-User'] = persona

  const res = await fetch(input, {
    credentials: 'same-origin',
    headers,
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return (await res.json()) as T
}

export const api = {
  me: () => http<Me>('/api/me'),
  config: () => http<Config>('/api/config'),
  personas: () => http<Persona[]>('/api/personas'),
  home: () => http<HomeResponse>('/api/home'),
  latestSession: () => http<{ session_id: string | null }>('/api/session/latest'),
  chat: (message: string, session_id?: string, route_hint?: RouteHint) =>
    http<ChatTurn>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id, route_hint }),
    }),
  approvals: () => http<ClaimReviewRow[]>('/api/approvals'),
  advanceClaim: (
    claim_id: string,
    decision: 'Approve' | 'Reject',
    note?: string,
    rejection_code?: string,
  ) =>
    http<{ claim_id: string; status: string }>(
      `/api/approvals/${encodeURIComponent(claim_id)}/advance`,
      { method: 'POST', body: JSON.stringify({ decision, note, rejection_code }) },
    ),
  nudges: () => http<NudgeCampaignRow[]>('/api/nudge-campaigns'),
  createNudgeCampaign: (
    template_id: string,
    dealer_ids: string[],
    deadline?: string,
    notes?: string,
  ) =>
    http<NudgeCampaignRow>('/api/nudge-campaigns', {
      method: 'POST',
      body: JSON.stringify({ template_id, dealer_ids, deadline, notes }),
    }),
  queueNudge: (campaign_id: string) =>
    http<{ status: string }>(`/api/nudge-campaigns/${encodeURIComponent(campaign_id)}/queue`, {
      method: 'POST',
    }),
  savedViews: () => http<SavedViewRow[]>('/api/saved-views'),
  saveView: (
    name: string,
    filter_payload: Record<string, unknown>,
    description?: string,
    pinned?: boolean,
  ) =>
    http<SavedViewRow>('/api/saved-views', {
      method: 'POST',
      body: JSON.stringify({ name, filter_payload, description, pinned: !!pinned }),
    }),
}
