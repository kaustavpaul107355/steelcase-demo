# Steelcase Co-op Program Analytics Agent — Demo Project

> **Internal demo workspace.** Synthetic data only. No real Steelcase customer information.

This directory builds out the **Co-op Program Analytics Agent ("COMPASS")** demo for Steelcase — a conversational analytics application on Databricks that combines a **Genie Space** (quantitative metrics), an **Agent Bricks Knowledge Assistant** (policy / how-to), and **action tools** backed by **Lakebase**, orchestrated by a **Supervisor Multi-Agent System** and instrumented with **MLflow**.

---

## Project map

| File / Folder | Purpose |
|---------------|---------|
| `demo-requirements.md` | **Start here.** Business objective + full requirements: goals, personas, architecture, success metrics, risks. |
| `demo-design.md` | **HOW we'll build it.** Design decisions, source-dataset inventory with type/volume, identifier schemes, routing rules, scorer contracts. |
| `storyline.md` | Narrative: 7-act story Maya lives through during the demo. |
| `click-script.md` | Presenter's click-by-click script — what to click, what to say, fallback paths. |
| `presentation/` | Self-contained HTML slide deck (10 slides); open `presentation/index.html`. Supports drag-drop screenshots/GIFs/videos with per-slot galleries. |
| `data/data-model.md` | Logical + physical data model, ERD, grain, column dictionary. |
| `data/ddl/` | Bronze / Silver / Gold DDL. |
| `data/generate-synthetic-data.py` | Polars + Mimesis data generator (~28k claims, ~480k order lines). **Pins 23 AMER East hero dealers (`D-04711..D-04733`) summing to ~$1.62M unused.** Also emits `seed/compass-source.xlsx` (4 sheets) used by the Phase 1.5 bronze pipeline. |
| `data/build-gold.py` | Local gold rollup: silver Parquet → `fact_coop_utilization_daily`, `fact_claim_sla`, `fact_dealer_performance_monthly`, `fact_activity_lift`. |
| `data/seed/` | Output of the generators (Parquet, gitignored). |
| `metric-views/` | 5 UC Metric View YAMLs: program metrics, dealer performance, activity lift, claim lifecycle, forfeiture risk. |
| `ka-corpus/` | 8 Knowledge Assistant documents: handbook, eligibility, claim playbook, brand spec, AMER/EMEA addenda, forfeiture policy, FAQ. |
| `lakebase/schema.sql` | Postgres DDL for chat memory, approvals, nudges, saved views, synced UC tables. |
| `lakebase/seed-data.sql` | Minimum rows to boot the app "warm." Priya → D-04711. |
| `lakebase/hydrate_synced_views.py` | One-shot UC → Lakebase copy for `v_dealer` and `v_coop_utilization_today` (Provisioned instance; UC-managed sync deferred). |
| `lakebase/grants.sql` | Idempotent role + GRANT script. Apply with `psql -v app_sp_id=<uuid>` once the Phase 7 App SP exists. |
| `app/backend/lakebase_token.py` | OAuth token-refresh helper for the Phase 7 BFF (`LakebaseTokenManager` + SQLAlchemy `make_engine`). |
| `eval/coop-eval-dataset.jsonl` | 20 graded turns (Genie / KA / tool / refuse / adversarial), MLflow-compatible. |
| `genie/` | Git-tracked source for the 2 Genie spaces (Utilization & Risk; Marketing Effectiveness & ROI). Per-space `instructions.md`, `sample-questions.yaml`, `sql-examples.sql`, `tables.yaml`. Exports under `genie/exports/`. |
| `eval/scorers.py` | Custom `@scorer policy_citation_present` for KA-routed turns. |
| `databricks.yml` | DAB skeleton: catalog, schemas, warehouse, pipeline, app, nightly eval job. |
| `app/README.md` | App scaffolding spec (React + FastAPI) — the contract Phase 7 implemented against. |
| `app/backend/` | FastAPI BFF: `main.py` + `config.py` + `schemas.py` + `auth.py` + mode-aware `agent/`, `tools/`, `store/` subtrees. Selects `lite` / `standard` / `full` at import time via `COMPASS_AGENT_MODE`. |
| `app/frontend/` | Vite + React + TS app: two-pane chat + right-pane workbench (Approvals / Nudges / Saved Views), header strip with mode/role/region badges, KA citation chips, Genie "Show metric & SQL" disclosure. |
| `app/Dockerfile`, `app/app.yaml`, `app/requirements.txt` | Multi-stage container + Databricks Apps runtime spec + Python deps. The DAB resource (`resources.apps.compass_app` in `databricks.yml`) wraps this. |
| `diagrams/` | Architecture and ERD images (rendered on demand). |

---

## Build order

See `demo-requirements.md §15` for the canonical phase list. Status today:

| Phase | What | Status |
|------|------|--------|
| 0 | Specification | ✅ Done |
| 1 | Data foundation (DDL + generator + **local gold rollup** + ingestion) | DDL applied in workspace ✅; bronze tables exist but empty; silver + gold populated from parquet seed ✅ |
| 1.5 | **Bronze hydration** — 4 fact tables from `compass-source.xlsx` sheets (native DBR 17.1+ Excel reader) + 4 reference/master tables from seed parquets | **DAB-deployed** job `compass-bronze-load` ✅ with 2 parallel tasks: `hydrate_bronze_excel` (`pipelines/00_hydrate_bronze_excel.py`) and `hydrate_bronze_parquet` (`pipelines/00_hydrate_bronze_parquet.py`). All 8 bronze tables hydrated 2026-05-18 (3,042 / 625,078 / 2,546 / 10,154 / 843 / 10 / 22 / 8). Streaming DLT blueprint in `01_bronze_landing.py` retained as production-shape reference. |
| 2 | Semantic layer — 5 Metric Views | YAMLs drafted ✅; **deployed in workspace** ✅ (activity_lift, claim_lifecycle, coop_program_metrics, dealer_performance, forfeiture_risk) |
| 3 | Genie spaces + sample questions | **DEPLOYED** ✅ 2 distinct spaces — "Co-op Utilization & Risk" (`01f152f8ed8a...`) and "Marketing Effectiveness & ROI" (`01f1532267c4...`). Git-tracked source in `genie/spaces/` |
| 4 | Knowledge Assistant indexed over the corpus | **DEPLOYED** ✅ Agent Bricks KA "COMPASS Co-op Program Handbook" (tile `f000ded6-362a-...`, endpoint `ka-f000ded6-endpoint`) indexes 8 corpus docs from `/Volumes/.../compass_bronze/raw/ka-corpus/`. Instructions enforce `[KA-XXX-### §<section>]` citations + audience/region scoping. |
| 5 | Lakebase schema + sync | **DEPLOYED** ✅ Lakebase Provisioned instance `compass-lakebase-prov` (CU_1, Postgres 16, host `ep-raspy-credit-d2yhs2ud...`); migrated from Autoscale in Session p since Apps↔Autoscale auth isn't GA. `compass` schema + 11 tables; seed loaded (6 users including Kaustav / 3 saved views / 5 pending claims / 4 prefs); `compass.v_dealer` (843) + `compass.v_coop_utilization_today` (3,042; max date_key 2026-10-13) hydrated via `lakebase/hydrate_synced_views.py`; grants applied (Session p). |
| 7 | App UI (React + FastAPI) — **modular by phase** (`lite` needs only 3+4; `standard` adds 5; `full` adds 6) | **DEPLOYED & RUNNING** ✅ at https://compass-app-7474649050252844.aws.databricksapps.com/ in `full` mode. Verified end-to-end on the live Databricks App: KA returns 3 citations on Silver/$25K; Genie binds to `compass_metric.coop_program_metrics`; Approval Queue lists 5 pending hero-cohort claims; Approve writes to Lakebase Provisioned. See `DEV_LOG.md` Sessions o + p. |
| **7.5** | **UI/UX polish + persona switcher** — tabbed chat (Auto / Genie Utilization / Genie Marketing / KA Handbook), persona switcher dropdown (Maya / Eliot / Priya / Jordan / Renske / Kaustav), role-specific home view with KPI tiles, design-token refresh, skeleton loaders | **DEPLOYED** ✅ 2026-05-20 (Session r). Live at https://compass-app-7474649050252844.aws.databricksapps.com/ in `full` mode. |
| 6 | Supervisor Agent (MAS) with Genie + KA + 3 tools | **DEPLOYED** ✅ 2026-05-20 (Session s). Embedded LLM supervisor in `app/backend/agent/supervisor.py` backed by `databricks-claude-sonnet-4-6`; 7 tool defs (3 query + 3 action + refuse); Auto-tab routes via `FullRouter`. Action tools return `tool_preview` cards in the UI; Confirm writes to Lakebase via existing endpoints. App now running in `full` mode. |
| 8 | Eval harness — dataset + scorers + nightly job | **DEFERRED — future enhancement.** Dataset + custom scorer ✅ remain in `eval/`; nightly runner not on the critical path for the demo. |
| 9 | Rehearsal + backup recording | **DEFERRED — future enhancement.** Will happen ahead of the customer-facing run, but is not gating further build. |
| ∞ | DAB bundle | Skeleton ✅; treated as production-shape blueprint targeting `steelcase_demo` catalog. Live workspace uses catalog `classic_stable_1zia5t_kp_catalog` with `compass_*` schemas — DAB **not** the deployment path for the current demo (manual SQL + notebooks were used). See `DEV_LOG.md` Session 2026-05-18d. |

---

## Quick local commands

```bash
# Generate synthetic data + roll up to gold (local validation)
cd data/
python generate-synthetic-data.py --out ./seed --as-of 2026-10-13
python build-gold.py            --in  ./seed --out ./seed/gold --as-of 2026-10-13
# Expected sanity checks at the end of build-gold:
#   AMER East FY26 expected_forfeit_usd ≈ $1.6M
#   Top 3 at-risk: Pivot Workplace Solutions, Halcyon Office Group, Northpoint Workspaces
#   Activity lift ladder leads with Programmatic Display ($7.40 / $1)

# Provision Lakebase + apply schema (after fevm-deployed)
psql "$LAKEBASE_URL" -f lakebase/schema.sql
psql "$LAKEBASE_URL" -f lakebase/seed-data.sql

# Apply UC DDL (Bronze/Silver/Gold)
databricks sql query --warehouse co-op-demo-wh < data/ddl/01-bronze.sql
databricks sql query --warehouse co-op-demo-wh < data/ddl/02-silver.sql
databricks sql query --warehouse co-op-demo-wh < data/ddl/03-gold.sql

# DAB deploy (skeleton)
databricks bundle deploy --target dev
```

---

## Demo identity

| Persona | Login | Role | Region |
|---------|-------|------|--------|
| Maya Chen | `maya.demo@steelcase-demo.invalid` | Channel Marketing Manager | AMER East |
| Eliot Vargas | `eliot.demo@steelcase-demo.invalid` | Director, Dealer Programs | Global |
| Priya Shah | `priya.demo@pivot-workplace.invalid` | Dealer Ops Lead | Dealer-side |

---

## What this demo proves (in one sentence per goal)

1. **Platform consolidation** — UC + Volumes + Lakebase + Apps + MAS land the same business need that today spans 4 systems.
2. **Governed metrics** — One YAML definition of `utilization_rate`, used by Genie, the app, and Finance.
3. **Mixed-modality agent** — Quantitative (Genie), qualitative (KA), and action (tools), routed by a Supervisor.
4. **OLTP + analytics flywheel** — Lakebase writes are reverse-ETL'd back to UC so the next agent turn sees them.
5. **Production-grade agent quality** — MLflow traces every turn; nightly eval keeps it honest.

---

## Authors

- Kaustav Paul (Lakeflow Connect EPL, AMER RCT) — design and asset authoring.

Synthetic, demo-only. Not for external sharing without scrubbing the customer name.

---

## Changelog

### Iteration 6 — 2026-05-19 (Phase 7: app scaffolded, lite-mode smoke passes)

- **Phase 7 — App scaffold landed.** `app/backend/` (FastAPI + Pydantic v2) and `app/frontend/` (Vite + React + TS) per the `app/README.md` capability matrix. Modular by phase: `lite` (Genie + KA only, default), `standard` (+ Lakebase memory/tools), `full` (+ Supervisor MAS endpoint — stubbed for Phase 6). Routes, tools, and memory implementations are swapped at startup based on `COMPASS_AGENT_MODE`.
- **DAB resource added.** `resources.apps.compass_app` in `databricks.yml` with 12 new variables wiring mode, Genie space ids, KA endpoint, Lakebase host/endpoint/user, MLflow experiment id. Multi-stage `app/Dockerfile` builds the React bundle and the FastAPI runtime in one image.
- **Lite-mode smoke validated end-to-end** against the live workspace (`fe-vm-classic-stable-1zia5t-kp`). KA returns 3 corpus citations with excerpts; Genie returns the hero $1.62M AMER East FY26 forfeiture. Three SDK-shape issues discovered and fixed along the way (lazy `WorkspaceClient`, KA Responses-style payload, Genie attachment-vs-content extraction) — captured in `DEV_LOG.md` Session n.
- **No production deploy yet.** `databricks bundle deploy` and `lakebase/grants.sql -v app_sp_id=<uuid>` are the next steps; frontend `npm install`/`npm run build` is also pending.

### Iteration 5 — 2026-05-18 (workspace inventory + Phase 1.5 hydrate notebook)

- **Inventoried the live workspace** (`fe-vm-classic-stable-1zia5t-kp`). Discovered the demo is live in catalog `classic_stable_1zia5t_kp_catalog` with `compass_*`-prefixed schemas — not the `steelcase_demo` catalog declared in the repo's DDL. Silver/gold/metric views/Genie space are all deployed and demo-correct (AMER East FY26 expected_forfeit = $1,619,573.91 ≈ $1.62M). Bronze tables exist (DDL applied) but all 0 rows — Phase 1.5's actual target.
- **Phase table updated** to reflect workspace truth: Phase 1 silver+gold ✅, Phase 2 metric views ✅ deployed, Phase 3 Genie ✅ deployed. The DAB at `databricks.yml` is the production-shape blueprint, not the current deployment mechanism.
- **Added** `pipelines/00_hydrate_bronze_excel.py` — workspace-targeted **batch** notebook for Phase 1.5. Reads `compass-source.xlsx` from a UC volume and appends to the four empty `compass_bronze` tables via native Excel reader (DBR 17.1+). Includes a `_assert_empty` pre-flight so re-runs against a populated table refuse to duplicate data. `pipelines/01_bronze_landing.py` retained as the production-shape **streaming** DLT/Auto Loader blueprint targeting `steelcase_demo.bronze`.
- **No workspace writes this turn.** No DAB deploy, no volume upload, no pipeline run. Local repo edits only; user reviews and runs the hydrate notebook manually when ready.
- **Memory & DEV_LOG**: added `project_steelcase_demo_workspace.md` so future sessions don't repeat the "where is the demo actually deployed?" investigation. DEV_LOG Session 2026-05-18d captures the inventory comparison.

### Iteration 4 — 2026-05-18 (Phase 1.5: native Excel bronze hydration)

- **Inserted Phase 1.5** between data foundation and semantic layer: the four previously empty `bronze.*` tables (`allocation_csv`, `erp_sales_order`, `event_registration`, `portal_claims`) are now hydrated from a single source workbook `seed/compass-source.xlsx` via the **native Databricks Excel reader** (DBR 17.1+, no JAR/PyPI dependency). One workbook, four sheets, four DLT tables — `dataAddress` selects the sheet, `schemaEvolutionMode = "none"` per the connector's streaming constraint.
- **Generator add-on** (`data/generate-synthetic-data.py`): new `write_bronze_source_workbook` helper emits `compass-source.xlsx` after the parquet writes. Column names are remapped to bronze DDL (`dealer_external_id`, `program_code`, `activity_code`, etc.) so each sheet lands straight into its target table. Parquet outputs are unchanged — `build-gold.py` still works exactly as before.
- **Bronze pipeline** (`pipelines/01_bronze_landing.py`): replaced the JSON/CSV stubs with four Auto Loader Excel readers pointed at `/Volumes/steelcase_demo/raw/compass-source/`. Adds `_ingest_ts`, `_source_file`, and `_source_sheet` provenance columns.
- **Demo framing**: the workbook is a deliberate consolidation for the demo — in production these four feeds arrive via Lakeflow Connect (SFDC/SAP) and Auto Loader (portal/allocations/events). `demo-design.md §5.A` is unchanged; new `§5.D` documents the Phase 1.5 substitution.
- **No disturbance**: bronze DDL, silver, gold, metric views, KA corpus, Lakebase, eval, click-script, storyline — all untouched. Hero cohort math ($1.62M unused, top 3 dealers) preserved bit-for-bit.

### Iteration 3 — 2026-05-18 (post-second-Cursor-review)

Closed the six concrete gaps Cursor flagged:

- **Added `metric.activity_lift` view** (`metric-views/activity_lift.yaml`). Activity-type × region × FY grain on `gold.fact_activity_lift`, with `revenue_per_coop_dollar` measure and Genie synonyms. Drives Act 6's "top-5 activities" turn properly — `dealer_performance` (dealer × month grain) was the wrong semantic.
- **Rewired eval row 5** to reference `activity_lift` (was `dealer_performance`). Also fixed the adversarial brand-compliance row to route to Genie instead of KA (brand_compliance is a fact column, not a policy claim).
- **Tuned the `expected_forfeit_usd` heuristic** in `data/build-gold.py` to a transparent two-band rule: HIGH-RISK (days_to_exp < 180 AND util < 0.6) ⇒ expected = unused; LOW-RISK ⇒ expected = unused × (1-util)² × 0.1. AMER East FY26 hero cohort (util ≈ 45%, ~138 days) now converges on **expected_forfeit ≈ $1.62M**, matching the click-script line. Also documented the rule in `forfeiture_risk.yaml`.
- **Reconciled eval count to 20** in `demo-requirements.md` §6 + §13 and `click-script.md` Act 9 (was "~40 graded turns" — narrative now matches the dataset).
- **Fixed design.md drift**: RLS example references `compass.app_user` (not the undefined `compass.app_user_lookup`); warehouse standardized to `co-op-demo-wh`.
- **Stubbed DAB-referenced files** so the bundle is internally consistent: `pipelines/01_bronze_landing.py`, `02_silver_curate.py`, `03_gold_materialize.py` (DLT skeletons with `dlt.expect_or_drop` for quality), `eval/run_eval.py` (notebook task entrypoint). Commented out the `include: resources/*.yml` line until the bundle grows; left a `resources/.gitkeep`.
- **Refreshed §11 asset inventory** in `demo-requirements.md` to reflect 20 items with current status (vs the original 12-row table with stale TODOs). Also bumped metric-view count from 4 → 5 in §7, README phase table, and design.md §11.

### Iteration 2 — 2026-05-18 (acronym rename)

- Renamed the application from **CoCoA** to **COMPASS** (Co-op Marketing Program Analytics & Strategy System) across all 18 files: prose, code identifiers, schema names, DAB resource names. The metaphor — "navigate the program" — matches Maya's job better and lands cleaner in customer conversations. New names: Postgres schema `compass`, app `compass-app`, supervisor endpoint `compass-supervisor`, MLflow experiment `/Shared/steelcase-demo/compass-experiment`, DAB bundle `compass-demo`.

### Iteration 1 — 2026-05-18 (post-Cursor-review)

Addressed the highest-impact gaps surfaced by the third-party review:

- **Pinned hero dealers.** Added `HERO_DEALERS` to `data/generate-synthetic-data.py`: 23 AMER East dealers (IDs `D-04711..D-04733`) with deterministic FY26 unused balances summing to **$1,619,400** (the click-script "$1.62M"). Top 3 are named verbatim from the storyline: Pivot Workplace Solutions (`D-04711`, Silver, $147.2K), Halcyon Office Group (`D-04712`, Gold, $118.4K), Northpoint Workspaces (`D-04713`, Silver, $96.3K). Allocations sized to `unused / 0.55`; committed flows out as Paid claims.
- **Local gold rollup.** New `data/build-gold.py` produces `fact_coop_utilization_daily`, `fact_claim_sla`, `fact_dealer_performance_monthly`, and `fact_activity_lift` from silver Parquet, with an end-of-run sanity check that prints the hero forfeiture totals and the activity-lift ladder. Validates the demo numbers before any workspace is touched.
- **Simplified `forfeiture_risk` metric view.** Replaced the brittle nested-subquery `expected_forfeit_usd` calc with `SUM(source.expected_forfeit_usd)`. The heuristic is now precomputed once in `gold.fact_coop_utilization_daily.expected_forfeit_usd` (new column added in `03-gold.sql`), making the metric view cheap and Genie-friendly.
- **Priya → D-04711.** Added `dealer_id` column + check constraint to `lakebase.app_user`; seeded Priya's dealer_id = `D-04711` (now matches the requirements doc, click-script Act 10, and `D-04711 = "Pivot Workplace Solutions"`). Also re-pointed 4 of the 5 seeded pending `claim_review` rows to hero-cohort dealers so Act 8 ("4 of the 23 also have pending claims") is true.
- **Eval dataset + custom scorer.** Added `eval/coop-eval-dataset.jsonl` (20 graded turns), `eval/scorers.py` (`policy_citation_present` regex-based `@scorer` for `KA-*` doc-IDs), and `eval/README.md` for the harness.
- **DAB skeleton.** Added `databricks.yml` covering catalog, schemas, warehouse, pipeline, app, and nightly eval job, with dev/prod targets.

Known still-open from the review (Phase 7+):
- App backend/frontend not implemented (placeholder spec only).
- Pipeline notebooks referenced from `databricks.yml` are paths-only.
- Genie space + KA index + supervisor agent not provisioned.
- `diagrams/` is still empty (Mermaid sources are inline in `data/data-model.md` and `demo-requirements.md §5.1`).

