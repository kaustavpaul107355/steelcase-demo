import { useEffect, useState } from 'react'
import { api, type HomeResponse, type HomeTile } from '../api'

interface Props {
  /** When this changes (persona switch), refetch. */
  reloadKey: string
}

export default function Home({ reloadKey }: Props) {
  const [home, setHome] = useState<HomeResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setHome(null)
    setErr(null)
    api.home().then(setHome).catch((e) => setErr(String(e)))
  }, [reloadKey])

  if (err) {
    return (
      <div className="home">
        <div className="coachmark">Home failed to load: {err}</div>
      </div>
    )
  }
  if (!home) {
    return (
      <div className="home">
        <div className="home-header">
          <div className="home-headline skeleton-text wide" />
          <div className="home-scope skeleton-text narrow" />
        </div>
        <div className="kpi-row">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="kpi-tile skeleton" />
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="home">
      <div className="home-header">
        <div className="home-headline">{home.headline}</div>
        <div className="home-scope">Scope: {home.scope_label}</div>
      </div>
      <div className="kpi-row">
        {home.tiles.map((t) => (
          <KpiCard key={t.key} tile={t} />
        ))}
      </div>
      {home.rows.length > 0 && (
        <div className="home-rows">
          <div className="home-rows-header">Drill-in</div>
          {home.rows.map((r, i) => (
            <div key={i} className={`home-row intent-${r.intent}`}>
              <span className="home-row-primary">{r.primary}</span>
              {r.secondary && <span className="home-row-secondary">{r.secondary}</span>}
              {r.metric && <span className="home-row-metric">{r.metric}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function KpiCard({ tile }: { tile: HomeTile }) {
  return (
    <div className={`kpi-tile intent-${tile.intent}`}>
      <div className="kpi-label">{tile.label}</div>
      <div className="kpi-value">{formatValue(tile)}</div>
      {tile.sub_label && <div className="kpi-sub">{tile.sub_label}</div>}
    </div>
  )
}

function formatValue(tile: HomeTile): string {
  const v = tile.value
  if (v == null) return '—'
  if (tile.format === 'currency' && typeof v === 'number') return formatCurrency(v)
  if (tile.format === 'percent' && typeof v === 'number') return `${v.toFixed(1)}%`
  if (tile.format === 'count' && typeof v === 'number') return v.toLocaleString()
  return String(v)
}

function formatCurrency(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (Math.abs(v) >= 10_000) return `$${(v / 1000).toFixed(0)}K`
  if (Math.abs(v) >= 1000) return `$${(v / 1000).toFixed(1)}K`
  return `$${v.toLocaleString()}`
}
