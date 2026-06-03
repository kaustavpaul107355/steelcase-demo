import { useEffect, useState } from 'react'
import { api, personaStore, type Config, type Me, type Mode } from './api'
import Chat from './components/Chat'
import Home from './components/Home'
import PersonaSwitcher from './components/PersonaSwitcher'
import RightPane from './components/RightPane'

export default function App() {
  const [me, setMe] = useState<Me | null>(null)
  const [config, setConfig] = useState<Config | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [personaEmail, setPersonaEmail] = useState<string | null>(() => personaStore.get())

  function loadIdentity() {
    setMe(null)
    setError(null)
    Promise.all([api.me(), api.config()])
      .then(([m, c]) => {
        setMe(m)
        setConfig(c)
      })
      .catch((e) => setError(String(e)))
  }

  useEffect(loadIdentity, [personaEmail])

  function onPersonaChange(email: string) {
    personaStore.set(email)
    setPersonaEmail(email)
  }

  if (error) {
    return (
      <div className="app-shell">
        <Header me={null} mode={null} config={null} onPersonaChange={onPersonaChange} />
        <div className="pane-body">
          <div className="coachmark">
            Backend unreachable. <pre>{error}</pre>
          </div>
        </div>
      </div>
    )
  }

  if (!me || !config) {
    return (
      <div className="app-shell">
        <Header me={null} mode={null} config={null} onPersonaChange={onPersonaChange} />
        <div className="pane-body">
          <div className="empty">Loading…</div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <Header
        me={me}
        mode={config.mode}
        config={config}
        onPersonaChange={onPersonaChange}
      />
      <Home reloadKey={`${me.email}:${me.role}`} />
      <div className="body">
        <Chat />
        <RightPane me={me} config={config} />
      </div>
    </div>
  )
}

interface HeaderProps {
  me: Me | null
  mode: Mode | null
  config: Config | null
  onPersonaChange: (email: string) => void
}

function Header({ me, mode, config, onPersonaChange }: HeaderProps) {
  return (
    <div className="header">
      <span className="brand">
        <span className="brand-mark" />
        COMPASS
        <small>Co-op Program Analytics Agent</small>
      </span>
      <span className="spacer" />
      {mode && <span className={`badge mode-${mode}`}>mode: {mode}</span>}
      {me && (
        <>
          <span className={`badge role role-${me.role}`}>{me.role}</span>
          {me.region_id && <span className="badge region">{me.region_id}</span>}
          {me.dealer_id && <span className="badge dealer">{me.dealer_id}</span>}
        </>
      )}
      {config?.allow_persona_switch && me && (
        <PersonaSwitcher currentEmail={me.email} onChange={onPersonaChange} />
      )}
      {!config?.allow_persona_switch && me && (
        <span className="muted-name">{me.display_name}</span>
      )}
    </div>
  )
}
