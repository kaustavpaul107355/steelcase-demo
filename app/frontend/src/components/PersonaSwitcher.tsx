import { useEffect, useRef, useState } from 'react'
import { api, type Persona } from '../api'

interface Props {
  currentEmail: string
  onChange: (email: string) => void
}

const ROLE_LABEL: Record<string, string> = {
  channel_mgr: 'Channel Mgr',
  director: 'Director',
  rmd: 'RMD',
  finance: 'Finance',
  dealer: 'Dealer',
  guest: 'Guest',
}

export default function PersonaSwitcher({ currentEmail, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [personas, setPersonas] = useState<Persona[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    api.personas().then(setPersonas).catch((e) => setErr(String(e)))
  }, [])

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current) return
      if (!ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  const current = personas?.find((p) => p.email === currentEmail)
  const label = current ? current.display_name : 'Sign in'

  return (
    <div className="persona-switcher" ref={ref}>
      <button
        className="persona-switcher-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="persona-avatar">{initials(label)}</span>
        <span className="persona-label">
          <span className="persona-name">{label}</span>
          {current && (
            <span className="persona-sub">
              {ROLE_LABEL[current.role] ?? current.role}
              {current.region_id ? ` · ${current.region_id}` : ''}
            </span>
          )}
        </span>
        <span className="persona-caret">▾</span>
      </button>
      {open && (
        <div className="persona-menu">
          <div className="persona-menu-header">Act as…</div>
          {err && <div className="persona-menu-err">{err}</div>}
          {!personas && !err && <div className="persona-menu-empty">Loading…</div>}
          {personas && personas.length === 0 && (
            <div className="persona-menu-empty">No personas seeded.</div>
          )}
          {personas?.map((p) => (
            <button
              key={p.user_id}
              className={`persona-row ${p.email === currentEmail ? 'active' : ''}`}
              onClick={() => {
                onChange(p.email)
                setOpen(false)
              }}
            >
              <span className="persona-avatar small">{initials(p.display_name)}</span>
              <span className="persona-row-text">
                <span className="persona-row-name">{p.display_name}</span>
                <span className="persona-row-sub">
                  <span className={`role-chip role-${p.role}`}>
                    {ROLE_LABEL[p.role] ?? p.role}
                  </span>
                  {p.region_id && <span className="region-chip">{p.region_id}</span>}
                  {p.dealer_id && <span className="dealer-chip">{p.dealer_id}</span>}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
