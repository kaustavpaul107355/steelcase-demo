# COMPASS Demo — App scaffolding (placeholder)

This directory will hold the Databricks App that fronts the Co-op Program Analytics Agent. **Not yet implemented** — this README captures the intended shape so the build is unambiguous when we get to Phase 7.

## Design principle: modular by phase

The app is built so it **degrades gracefully** when downstream phases (5 Lakebase, 6 Supervisor MAS) aren't deployed yet. A single env var (`COMPASS_AGENT_MODE`) selects one of three capability modes. The same backend/frontend code runs in all three — only the wired implementations of `router`, `tools`, and `memory` change.

This keeps Phase 7 (and the demo storyline acts that depend on it) **unblocked** while Phases 5 and 6 are still in flight, and lets us ship a "lite" version against just **Phase 3 (Genie) + Phase 4 (KA)** to customers, internal previews, or sales rehearsals.

### Capability matrix

| Mode | Phases required | Chat backend | Right pane | Action tools |
|---|---|---|---|---|
| **`lite`** | 3 + 4 | Direct Genie REST + KA REST; intent router in BFF (regex on verbs → Genie/KA; LLM fallback for ambiguous turns) | Static starter prompts + Genie sample-question chips | None — "preview only" cards generated client-side; nothing persists |
| **`standard`** | 3 + 4 + 5 | Same routing as `lite`, **plus** persisted chat history in Lakebase (`chat_session`, `chat_turn`) | Live **Approval Queue**, **Nudge drafts**, **Saved Views** — all from Lakebase | **`save_view`** is real; nudge / claim buttons stage rows but do not flow through the supervisor |
| **`full`** | 3 + 4 + 5 + 6 | **Hybrid**: embedded action-gate (foundation model, ask-vs-do) + `compass-supervisor` Agent Bricks MAS for read-side routing between Genie / KA. Action tools (advance_claim / nudge / save_view) stay in the BFF so the UI gets a Confirm card before any Lakebase write. Chat memory in `chat_session.supervisor_state` | All tabs live; the agent can stage nudges and advance claims | All 3 tools live |

The demo's "hero moment" (recovering $1.62M of forfeiture risk via a single conversation that touches Genie + KA + an action) **requires `full`**. The "answer Maya's policy + metric questions" half of the storyline works in `lite`. Most customer-rehearsal sessions can run in `lite` or `standard`.

### Feature flags (env vars)

| Var | Required in | Purpose |
|---|---|---|
| `COMPASS_AGENT_MODE` | all | `lite` \| `standard` \| `full`. Default: `lite`. |
| `COMPASS_GENIE_SPACE_UTIL_RISK_ID` | all | Genie space A id (currently `01f152f8ed8a1682af57700b37fb11bb`) |
| `COMPASS_GENIE_SPACE_MARKETING_ID` | all | Genie space B id (currently `01f1532267c4147d9781fe17c1c6230f`) |
| `COMPASS_KA_NAME` | all | KA name (or `COMPASS_KA_TILE_ID` if known) |
| `COMPASS_WAREHOUSE_ID` | all | SQL warehouse for direct Genie SQL (currently `e6dc9b218651c48a`) |
| `COMPASS_LAKEBASE_HOST` | `standard`, `full` | Postgres host for the Lakebase instance |
| `COMPASS_LAKEBASE_DB` | `standard`, `full` | Database name (default: `compass`) |
| `COMPASS_SUPERVISOR_ENDPOINT` | `full` only | Agent Bricks MAS endpoint for read-side routing (currently `mas-2a692b50-endpoint`, tile `2a692b50-bcd1-41cc-b1a2-182cf596a5fc`) |
| `COMPASS_FM_ENDPOINT` | `full` only | Foundation model endpoint for the embedded action-gate supervisor (currently `databricks-claude-sonnet-4-6`) |
| `COMPASS_MLFLOW_EXPERIMENT_ID` | all | MLflow experiment for trace ingestion |

Startup-time validation: the BFF asserts the env vars required for the chosen mode and refuses to boot if any are missing. Missing vars for *higher* modes are silently ignored.

### Stack

- **Framework**: React + Vite frontend, FastAPI backend (matches the existing CDPP Coach App pattern).
- **Auth**: Databricks App OAuth (user identity passed through to UC and Lakebase).
- **Backend deps**: `databricks-sdk`, `mlflow`, `httpx` (always); `sqlalchemy`, `psycopg[binary]` (standard/full).
- **Agent**: in `full` mode, two serving endpoints are reached per Auto-tab turn — (1) the action-gate FM endpoint (`COMPASS_FM_ENDPOINT`) for the ask-vs-do decision, and (2) on a query, the Agent Bricks MAS (`COMPASS_SUPERVISOR_ENDPOINT`) which routes across the two Genie spaces + handbook KA. Action tools execute through the BFF after the user confirms. In `lite`/`standard`, no serving endpoint is called — the BFF routes turns itself.

### BFF abstraction layers

The backend is structured so the three modes are a **wiring choice**, not three forks of the codebase:

```
backend/
  agent/
    router.py          # interface: route(turn) -> ("genie"|"ka", payload)
    router_lite.py     # regex + small-LLM intent classifier; calls Genie/KA REST directly
    router_full.py     # forwards turn to supervisor endpoint, parses tool_calls
  tools/
    actions.py         # interface: 3 functions (create_nudge_campaign, advance_claim, save_view)
    tools_preview.py   # logs + returns JSON for UI preview cards; no persistence
    tools_lakebase.py  # SQLAlchemy writes to compass.* tables
  store/
    memory.py          # interface: load_session, append_turn
    memory_ephemeral.py
    memory_lakebase.py
  main.py              # picks impls based on COMPASS_AGENT_MODE
```

`main.py` is the only place the mode is read. Routes, schemas, MLflow tracing, and the React frontend are mode-agnostic.

## Routes

| Method | Path | Modes | Purpose |
|--------|------|-------|---------|
| GET    | `/api/me` | all | Returns the OAuth user, role, region |
| GET    | `/api/config` | all | Returns enabled features (drives UI tab visibility) |
| GET    | `/api/session/latest` | standard / full | Latest chat session for the user |
| POST   | `/api/chat` | all | Send a user turn → routes (mode-dependent) → persists turn (standard/full) |
| GET    | `/api/approvals` | standard / full | Pending `claim_review` rows scoped to user's region |
| POST   | `/api/approvals/{claim_id}/advance` | standard / full | Approve / reject (full = via agent; standard = direct user click) |
| GET    | `/api/nudge-campaigns` | standard / full | List user's drafted / queued campaigns |
| POST   | `/api/nudge-campaigns` | standard / full | Persist a campaign (full = drafted by agent; standard = drafted by user UI) |
| POST   | `/api/nudge-campaigns/{id}/queue` | standard / full | Move from Draft → Queued |
| GET    | `/api/saved-views` | all (local-only in `lite`) | List saved views (pinned first) |
| POST   | `/api/saved-views` | all (local-only in `lite`) | Create / overwrite |
| GET    | `/api/saved-views/{id}/run` | all | Re-execute the saved query |

In `lite` mode, `/api/saved-views` stores to browser localStorage instead of Lakebase, so the right pane has *some* persistent state without a Postgres dependency. The 5 standard/full-only routes return `404 {"detail": "feature_disabled_in_mode_lite"}` so the frontend can hide the tabs.

## UI layout

```
+---------------------------+---------------------------+
| Left pane: Chat           | Right pane: Tabs          |
|  - turn history           |   - Approval Queue (badge)|     [standard/full]
|  - composer               |   - Nudges                |     [standard/full]
|  - "Show metric & SQL"    |   - Saved Views (pinned)  |     [all; local in lite]
|  - citations expander     |                           |
+---------------------------+---------------------------+
```

Header strip: user identity, region badge, tier filter dropdown, **mode badge** (`lite` / `standard` / `full`) to make capability boundaries visible during demos.

Right-pane tabs that are disabled in the current mode render a coachmark explaining the missing dependency, e.g.:
- "Approval Queue requires Lakebase (Phase 5). Currently running in `lite`."

## Local dev

```
cd app/
export COMPASS_AGENT_MODE=lite          # or standard / full
# lite needs only Genie + KA env vars; standard adds Lakebase; full adds supervisor
uvicorn backend.main:app --reload       # port 8080
pnpm --filter frontend dev              # port 5173
```

Lakebase connection (standard/full): `COMPASS_LAKEBASE_HOST` + OAuth credential refresh.

## Tracing

All `/api/chat` calls wrap the routing + tool execution in an `mlflow.start_span()` with attributes:
- `compass.mode` (`lite` / `standard` / `full`)
- `user.role`, `user.region`
- `chat.session_id`, `chat.turn_index` (when `memory_lakebase` is wired)
- `tool.routed` (`genie`, `ka`, `create_nudge_campaign`, `advance_claim`, `save_view`, `refuse`)

Traces flow to the experiment configured by `COMPASS_MLFLOW_EXPERIMENT_ID`. The same experiment is shared across modes so mode-to-mode quality regressions surface in eval.

## Deploy

- **DAB target**: `compass_app` in `databricks.yml`.
- **Resources referenced**: SQL warehouse, Genie spaces, KA. Lakebase instance and serving endpoint are referenced **conditionally** (the bundle's app resource pulls env from a target-specific variable block).
- **Permissions**: `CAN_USE` on the warehouse; `CAN_QUERY` on KA + Genie spaces; `CAN_USE` on the Lakebase instance (when present); `CAN_INVOKE` on the supervisor endpoint (when present) — all on the app principal.

---

This file is a spec. The actual `app/backend/`, `app/frontend/`, and `app/Dockerfile` will be added in Phase 7 of the build sequence (see `demo-requirements.md §15`).
