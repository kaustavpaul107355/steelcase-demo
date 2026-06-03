# Steelcase Co-op Program Analytics Agent — Demo Requirements

## Business Objective

**The problem.** Steelcase invests **~$45–55M per year** in dealer co-op marketing funds across its ~800-dealer network. Of that, **18–22% — roughly $8–12M every fiscal year — forfeits unused at year-end** because dealers cannot see their balance in time, program policy lives in scattered PDFs, and the claim workflow averages **12.4 business days** to approve. On top of the leakage, channel marketing leaders cannot answer the CFO's question — *"for every co-op dollar we spent, what sell-through did we actually get?"* — so each year's budget is reset by negotiation rather than evidence.

**What we are building.** "**COMPASS**" — the **Co-op M**arketing **P**rogram **A**nalytics & **S**trategy **S**ystem — is a conversational analytics application on Databricks that lets a channel marketing manager, in one chat, (1) **see** governed co-op program KPIs, (2) **ask** policy / eligibility questions and get cited answers, and (3) **act** — draft nudge campaigns for at-risk dealers, advance pending claims, save views for executive reviews. A single Agent Bricks **Supervisor Agent (MAS)** routes each turn between a **Genie Space** over Unity Catalog **Metric Views** (quantitative), a **Knowledge Assistant** over the curated program corpus (qualitative), and **Lakebase-backed action tools** (transactional). Every turn is traced and evaluated in MLflow.

**Quantified outcomes we are targeting (vs FY-prior baselines):**

| Outcome | Baseline | Target with COMPASS | Annualized impact |
|---|---|---|---|
| Forfeiture rate | 18–22% of allocation | **< 8%** | **+$5–8M of marketing investment recovered** |
| Avg claim approval cycle | 12.4 business days | **< 4 business days** | 3× faster dealer reimbursement, less channel friction |
| Channel-manager time-to-insight | 2–5 days | **< 5 minutes** | Decisions move from quarterly to weekly cadence |
| Sell-through attribution | not measured | reported quarterly, methodology auditable | Defensible budget allocation to the CFO and DPC |

**Why this matters now.** Steelcase's CDPP Coach App has already validated the Databricks Apps + Agent Bricks + Lakebase pattern internally. COMPASS reuses that pattern against a problem with **measurable, finance-grade dollars at risk**, owned by the **Channel Marketing organization** rather than HR. A 60-day pilot in AMER East — Maya's region, 120 dealers, $4.5M allocation — is the proposed path; a successful pilot unlocks rollout to EMEA in Q1 FY27 and APAC in Q2 FY27.

**Bottom line.** If COMPASS moves the forfeiture rate to single digits and gives Channel Marketing a defensible ROI story, the platform pays for itself in one fiscal quarter at one regional cohort, with zero incremental marketing budget.

---

**Demo ID:** SC-DEMO-05
**Owner:** Kaustav Paul (Lakeflow Connect EPL, AMER RCT)
**Customer:** Steelcase Inc. (Furniture / Contract Office, Grand Rapids MI)
**Created:** 2026-05-18
**Status:** In construction
**Target customer audience:** VP Channel Marketing, Director Dealer Programs, Channel Marketing Managers, Dealer Marketing Operations Lead, Finance Controller (Channel)
**Demo length target:** 25 minute live click-through + 10 minute Q&A
**Demo modality:** Live Databricks Apps demo using a Supervisor Multi-Agent System (MAS) over Genie + Knowledge Assistant + Lakebase

---

## 1. Executive Summary

Steelcase distributes more than 80% of its products through an independent dealer network of **~800 authorized dealers** across the Americas, EMEA and APAC. To grow brand presence and accelerate dealer sell-through, Steelcase runs a multi-million-dollar **Co-op Marketing Program** (sometimes called MDF — Market Development Funds) that reimburses dealers for approved marketing activities: digital advertising, trade shows, showroom refreshes, client events, account-based marketing, sponsorships, sales literature, etc.

Today, the program is operated through a mix of spreadsheets, SharePoint, the dealer portal, and a homegrown claims app. Three structural problems hurt program ROI:

1. **Forfeiture leakage.** Roughly 18-22% of allocated co-op funds expire unused at fiscal year-end because dealers do not know their balance, the policy is opaque, and claim friction is high. At Steelcase's allocation scale this is **$8-12M of marketing investment left on the table annually.**
2. **Slow & inconsistent claim adjudication.** Claim approval averages 12.4 business days with high variance because reviewers must cross-reference policy PDFs, dealer tier rules, brand-compliance specs, and pre-approval emails living in different systems.
3. **No sell-through attribution.** Channel marketers cannot directly answer "for every co-op dollar spent on Activity X in Region Y, what was the incremental sell-through dollar return?" — so budget reallocation each year is political, not analytical.

The **Co-op Program Analytics Agent** ("COMPASS") is a conversational analytics application on Databricks that lets a Channel Marketing Manager, in plain English:

- Ask **quantitative** questions about program health, dealer utilization, forfeiture risk, and sell-through attribution — backed by Unity Catalog **Metric Views** and a **Genie Space**.
- Ask **policy / how-do-I** questions about program rules, eligible activities, claim documentation requirements, and brand-compliance specs — backed by an Agent Bricks **Knowledge Assistant** over the curated program corpus.
- Trigger **actions** — generate dealer nudge campaigns, advance pending claim approvals, set saved views — backed by **Lakebase** (managed Postgres) state.

A **Supervisor Agent (MAS)** routes each user turn to the right specialist (Genie, KA, or action tool), preserves chat memory in Lakebase, and emits **MLflow traces** for every interaction so the team can evaluate, monitor, and improve quality.

The demo's "hero moment" is recovering **$1.6M of forfeiture risk** in Q4 by combining a Genie metric drill-down + KA policy lookup + a Lakebase-backed nudge campaign — all in a single conversation.

---

## 2. Demo Goals & Non-Goals

### 2.1 Goals (what the audience must walk away believing)

| # | Goal | Audience Belief |
|---|------|-----------------|
| G1 | **Databricks is the right platform for channel marketing analytics.** | "We can land our co-op fact tables, dealer master, policy corpus, and claim workflow all on one platform." |
| G2 | **Metric Views deliver governed, reusable business KPIs.** | "We will not have three definitions of `coop_utilization_rate` ever again." |
| G3 | **Genie + KA + Action tools, orchestrated by a Supervisor Agent, beat dashboards for this persona.** | "My channel managers cannot read 12-tab dashboards. They can ask questions." |
| G4 | **Lakebase replaces the bespoke claim-workflow database.** | "Synced from Unity Catalog, OLTP-fast, OAuth-native to Databricks Apps." |
| G5 | **MLflow Tracing + Evaluation gives us production confidence in an agent.** | "We can prove this agent gets better, not worse, over time." |

### 2.2 Non-Goals

- This is **not** a full Salesforce CRM replacement; we read dealer master from Salesforce/CDPP, we do not rewrite it.
- This is **not** a creative-asset DAM; brand asset storage stays on the existing system; we only retrieve specs.
- This is **not** an attribution model science project; we use a defensible mid-fidelity lift-vs-control approach for sell-through impact, not a peer-reviewed MMM.
- We will not show real Steelcase dealer names or PII; all data is synthetic but plausible.

---

## 3. Target Personas

### 3.1 Primary persona — **"Maya", Channel Marketing Manager, Americas East**

- 8-12 years at Steelcase. Manages ~120 dealers across 14 states.
- Owns a $4.5M annual co-op allocation, KPI'd on **utilization rate**, **on-brand compliance**, and **sell-through lift**.
- Lives in Outlook, Teams, the dealer portal, and 4 Excel pivots. Has no SQL. Trusts numbers when she sees the supporting policy.
- Pain: "I find out about dealer forfeitures in January when it is too late. I want to know in October."

### 3.2 Secondary persona — **"Eliot", Director Dealer Programs (Global)**

- 15+ years. Sets the program design — tier rules, allocation formulas, eligible-activity matrix, audit policy.
- Cares about **program ROI**, **fairness**, **fraud / leakage**, and being able to **defend changes to the program** to the CFO.
- Pain: "I cannot answer 'is Tier-3 EMEA digital ad spend actually moving sell-through?' without a 6-week analyst project."

### 3.3 Tertiary persona — **"Priya", Dealer Marketing Operations Lead at Dealer #4711**

- Submits 30-60 claims/year for a single mid-size dealer.
- Wants to know **balance, deadlines, what's eligible, and claim status** in 30 seconds.
- (Demo shows her use case briefly to make the case that the same agent serves the dealer side too.)

---

## 4. Business Outcomes & Success Metrics

| Outcome | Baseline | Target with COMPASS | How we measure |
|---------|----------|-------------------|----------------|
| Forfeiture rate (% of allocation unused at FY-end) | 18-22% | <8% | `coop_program_metrics` view, year-over-year |
| Avg claim approval cycle time | 12.4 business days | <4 business days | `claim_lifecycle` view, p50 + p90 |
| Channel mgr time-to-insight (ask → decision) | 2-5 days | <5 minutes | MLflow trace duration + UAT survey |
| Sell-through lift attributed to co-op-funded activities | not measured | reported quarterly | `dealer_performance` view + lift-vs-control |
| Program ROI defensibility (CFO review) | qualitative | quantitative, reproducible | metric view lineage + saved Genie answers |

These five metrics anchor the storyline and the dashboards. The demo will surface (or imply) each one.

---

## 5. Solution Architecture

### 5.1 High-level architecture (logical)

```
                +----------------------------------------------------+
                |   Databricks App (React + FastAPI, OAuth via App)  |
                |   "Co-op Program Analytics Agent" UI               |
                +----------------------------------------------------+
                          |                              |
                          | chat / tool calls            | claim actions
                          v                              v
                +----------------------+        +------------------------+
                |  Supervisor Agent    |        |   Lakebase (Postgres)  |
                |  (Agent Bricks MAS)  |<------>|  - chat memory         |
                +----------------------+ memory |  - approvals workflow  |
                  |        |        |           |  - nudge campaigns     |
                  v        v        v           |  - saved views         |
            +--------+ +--------+ +---------+   +------------------------+
            | Genie  | |  KA    | |  Action |             ^
            | Space  | | Co-op  | |  Tools  |             | UC sync
            +--------+ +--------+ +---------+             | (synced tables)
                  |        |                              |
                  v        v                              |
            +-------------------+   +----------------+    |
            | Unity Catalog     |   | UC Volumes     |    |
            | - Metric Views    |   | - policy PDFs  |    |
            | - silver/gold     |   | - brand specs  |    |
            | - dealer master   |   | - playbooks    |    |
            +-------------------+   +----------------+    |
                  ^                       ^               |
                  |                       |               |
            +-----+----+    +-------------+----+    +-----+------+
            | Lakeflow |    | Auto Loader      |    | Reverse    |
            | Connect  |    | (PDFs/Markdown)  |    | ETL sync   |
            | (SFDC,   |    +------------------+    | from gold  |
            |  ERP)    |                            +------------+
            +----------+
```

### 5.2 Component-by-component

**Ingestion (bronze)**
- **Lakeflow Connect — Salesforce**: dealer master, tier, owner, address, life-cycle state. Daily.
- **Lakeflow Connect — SAP ERP** (or simulated CSV land): sell-through orders by dealer / product family / week.
- **Auto Loader on UC Volume**: monthly co-op fund allocations CSVs (one per region), claim submissions (JSON exports from current portal), proof-of-execution images (path-only land for demo).
- **Zerobus or batch**: marketing event registrations (trade shows) — kept lightweight for demo.

**Curation (silver / gold)** — Lakeflow Spark Declarative Pipelines:
- `silver.dealer` (SCD-2 on tier and territory)
- `silver.coop_allocation` (allocation events per dealer × program × fiscal period)
- `silver.coop_claim` (full claim lifecycle, one row per state transition)
- `silver.marketing_event` (events / activities with type, dates, cost, status)
- `silver.sell_through_order` (line-item dealer orders)
- `gold.fact_coop_utilization` (daily snapshot of allocated / committed / paid / forfeited per dealer × program × fiscal period)
- `gold.fact_claim_sla` (per-claim cycle time, broken down by state)
- `gold.fact_dealer_performance` (monthly sell-through with attributed co-op spend)
- `gold.dim_dealer`, `gold.dim_activity_type`, `gold.dim_fiscal_calendar`, `gold.dim_region`, `gold.dim_program`

**Semantic layer — UC Metric Views** (the source of truth for KPIs):
- `metric.coop_program_metrics` — utilization, commitment, payout, forfeiture risk
- `metric.dealer_performance` — sell-through and co-op-funded lift
- `metric.claim_lifecycle` — cycle-time SLAs by state, region, tier
- `metric.forfeiture_risk` — dealers / programs at risk in current fiscal period

**Conversational layer**:
- **Genie Space** "Co-op Program Analytics" grounded on the 5 metric views + curated dimension tables, with ~25 example questions.
- **Knowledge Assistant** "Co-op Program Handbook" indexed over the KA corpus (program handbook, policy, eligibility matrix, claim playbook, brand specs, regional addenda, FAQ).
- **Supervisor Agent (MAS)** that decides between Genie (metric Qs), KA (policy/how-to Qs), and tool calls (actions).

**Action tools** (function tools registered with the supervisor):
- `create_nudge_campaign(dealer_ids, template_id, deadline)` → writes to Lakebase `nudge_campaign`.
- `advance_claim(claim_id, decision, reviewer_note)` → updates Lakebase `claim_review`, then reverse-ETL'd to UC.
- `save_view(view_name, filter_payload)` → Lakebase `saved_view` for the user.

**Lakebase (managed Postgres)**:
- Stores agent **chat memory**, **approval workflow state**, **nudge campaign drafts**, **saved views**, and **per-user preferences**.
- **Synced tables** from `gold.fact_coop_utilization` so the app can read OLTP-fast without going back to Spark.
- OAuth-on-behalf-of-user for Databricks App auth.

**Observability / Quality**:
- All agent turns logged as **MLflow Traces** (parent span = supervisor; child spans = Genie / KA / tool).
- A small **eval dataset** (20 graded turns at v1; extensible to 40+ as production traces accumulate) drives `mlflow.genai.evaluate()` with built-in scorers (Correctness, Guidelines, RetrievalGroundedness) + one custom @scorer for "policy citation present".
- Production traces ingested back into MLflow for continuous monitoring of regression / drift.

### 5.3 Deployment topology
- **Workspace:** fevm-provisioned AWS workspace (no PrivateLink needed for demo).
- **Compute:** Serverless SQL warehouse "co-op-demo-wh" for Genie + Metric Views; serverless model serving for Agent Bricks; Lakebase autoscaling instance "coop-lakebase".
- **Bundles:** DAB (`databricks.yml`) packages catalog, schemas, pipelines, jobs, app, KA, Genie space.

---

## 6. Data Model (logical)

See `data/data-model.md` for the full ERD, grain, and column-level dictionary. Summary:

**Dimensions**
- `dim_dealer` — `dealer_id`, `dealer_name`, `region`, `country`, `tier` (Platinum / Gold / Silver / Authorized), `sales_rep_id`, `salesforce_account_id`, scd2 effective dates.
- `dim_program` — `program_id`, `program_name` ("Steelcase 2026 Co-op", "WorkLife Marketing Lab", "Net-Zero Showroom Refresh"), fiscal_year, allocation_method.
- `dim_activity_type` — `activity_type_id`, `category` (Digital, Event, Showroom, Content, Sponsorship), `default_cofund_pct`, `requires_preapproval`.
- `dim_fiscal_calendar` — Steelcase fiscal year (March–February), period (P1..P12), week-of-fiscal-year.
- `dim_region` — Region, sub-region, country list.

**Facts**
- `fact_coop_allocation` — grain: dealer × program × fiscal_period × allocation_event. Columns: allocated_usd, allocation_date, expiration_date.
- `fact_coop_claim` — grain: claim. Columns: claim_id, dealer_id, program_id, activity_type_id, submission_date, requested_amount_usd, approved_amount_usd, paid_amount_usd, status (Draft / Submitted / Under_Review / Approved / Rejected / Paid / Expired), preapproval_id_nullable, brand_compliance_score, reviewer_id, decision_date, payment_date.
- `fact_sell_through_order` — grain: order_line. Columns: order_id, dealer_id, product_family, order_date, ship_date, net_revenue_usd.
- `fact_marketing_event` — grain: event. Columns: event_id, dealer_id, event_type, start_date, end_date, attendees, claim_id_nullable.

**Snapshot / derived gold**
- `fact_coop_utilization_daily` — for trend lines + Genie.
- `fact_claim_sla` — one row per claim with elapsed days per status.
- `fact_dealer_performance_monthly` — sell-through tied to attributed co-op spend.

---

## 7. Metric Views (governed KPIs)

Five metric views in `metric-views/`:

1. **`coop_program_metrics.yaml`** — joinable on dealer / program / region / period.
   Measures: `allocated_usd`, `committed_usd`, `approved_usd`, `paid_usd`, `forfeited_usd`, `utilization_rate`, `commitment_rate`, `forfeiture_rate`.

2. **`dealer_performance.yaml`** — sell-through with co-op attribution, **dealer × month grain**.
   Measures: `net_revenue_usd`, `attributed_coop_usd_lift`, `revenue_per_coop_dollar`, `lift_vs_control_pct`.

3. **`activity_lift.yaml`** — **activity-type × region × FY grain**. Drives the Act 6 "top-5 activity types" turn.
   Measures: `coop_paid_usd`, `attributed_revenue_usd`, `revenue_per_coop_dollar`, `matched_pairs`.

4. **`claim_lifecycle.yaml`** — claim SLAs.
   Measures: `claims_submitted`, `claims_approved`, `claims_rejected`, `cycle_time_days_p50`, `cycle_time_days_p90`, `first_pass_approval_rate`.

5. **`forfeiture_risk.yaml`** — current-period at-risk dealers.
   Measures: `unused_balance_usd`, `days_to_expiration`, `expected_forfeit_usd` (precomputed two-band heuristic in gold), `dealers_at_risk_count`.

Each YAML carries a `description`, joins, dimensions, and the natural-language synonyms Genie uses.

---

## 8. Knowledge Assistant Corpus

Eight curated documents in `ka-corpus/` (see folder for full text):

1. `coop-program-handbook.md` — program intent, fiscal cadence, governance.
2. `eligibility-matrix.md` — what counts and what doesn't, by activity type and dealer tier.
3. `claim-submission-playbook.md` — step-by-step, required docs, pre-approval thresholds.
4. `brand-compliance-spec.md` — logo, color, typography, photography rules; rejection triggers.
5. `regional-addendum-amer.md` — AMER-specific tax, NLA, dealer council rules.
6. `regional-addendum-emea.md` — EMEA-specific GDPR, VAT, sustainability claims rules.
7. `forfeiture-and-extension-policy.md` — when balances expire, how to request extensions.
8. `co-op-faq.md` — top 30 dealer questions with curated answers.

Index strategy: chunk by H2; tag each doc with `region`, `audience` (dealer | internal), and `effective_date`.

---

## 9. Lakebase Schema

See `lakebase/schema.sql`. High-level tables:

- `app_user` (user_id, email, role, region, default_tier_filter)
- `chat_session` (session_id, user_id, started_at, last_active_at, supervisor_state_json)
- `chat_turn` (turn_id, session_id, role, content, tool_calls_json, trace_id, latency_ms)
- `claim_review` (claim_id PK, status, reviewer_id, decision_at, reviewer_note, brand_check_json)
- `nudge_campaign` (campaign_id, created_by, created_at, template_id, dealer_filter_json, deadline, status)
- `nudge_recipient` (campaign_id, dealer_id, email_status, opened_at)
- `saved_view` (view_id, user_id, name, filter_payload_jsonb)
- **Synced** read-only views: `v_coop_utilization` (from `gold.fact_coop_utilization_daily`), `v_dealer` (from `gold.dim_dealer`).

OAuth-on-behalf-of integrates with Databricks App identity. Indexes on `(user_id, last_active_at)`, `(claim_id)`, and `(campaign_id, dealer_id)`.

---

## 10. Demo Storyline (one-paragraph version)

Maya, the AMER East Channel Marketing Manager, opens COMPASS on a Tuesday morning in October. She asks "What's my Q4 forfeiture risk?" and the agent answers $1.6M across 23 dealers, surfacing the metric view. She asks "Which activity types tend to recover fastest in Q4?" — KA returns the playbook excerpt, and Genie shows historical lift. She asks "Generate a nudge campaign for those 23 dealers with the digital-ad fast-track template, deadline Dec 12" — the action tool writes to Lakebase, returns the draft, and she approves it. She pivots: "Of my paid claims YTD, which had the best sell-through lift?" — Genie returns the top 10 with attribution. Finally Maya asks "What policy stops a Tier-Silver dealer from submitting a $25K digital ad claim?" — KA cites the eligibility matrix line-by-line. Total elapsed time: 6 minutes. The same conversation, three months ago, would have been a 4-day analyst ticket plus a SharePoint scavenger hunt.

Full beat-by-beat narrative is in `storyline.md`. Click-by-click presenter script is in `click-script.md`.

---

## 11. Demo Asset Inventory (what we will build)

| # | Asset | Path | Format | Status |
|---|-------|------|--------|--------|
| 1 | Requirements doc (this file) | `demo-requirements.md` | Markdown | ✅ Done (Iter 3) |
| 2 | Design doc (HOW) | `demo-design.md` | Markdown | ✅ Done (Iter 2) |
| 3 | Storyline + narrative | `storyline.md` | Markdown | ✅ Done |
| 4 | Click-by-click script | `click-script.md` | Markdown | ✅ Done |
| 5 | Data model + ERD | `data/data-model.md` | Markdown + Mermaid | ✅ Done |
| 6 | Bronze/Silver/Gold DDL | `data/ddl/*.sql` | SQL | ✅ Done |
| 7 | Synthetic data generator (pinned heroes) | `data/generate-synthetic-data.py` | Python | ✅ Done |
| 8 | Local gold rollup script | `data/build-gold.py` | Python | ✅ Done (Iter 1, retuned Iter 3) |
| 9 | Metric Views (5) | `metric-views/*.yaml` | YAML | ✅ Done (Iter 3: + `activity_lift`) |
| 10 | KA corpus (8 docs) | `ka-corpus/*.md` | Markdown | ✅ Done |
| 11 | Lakebase schema + seed + hydrate + grants | `lakebase/{schema.sql, seed-data.sql, hydrate_synced_views.py, grants.sql}` | SQL + Python | ✅ Deployed Phase 5 to Lakebase Provisioned instance `compass-lakebase-prov` (host `ep-raspy-credit-d2yhs2ud...`, CU_1, Postgres 16). Migrated from Autoscale in Session p — Apps↔Autoscale auth not GA. `grants.sql` (Session m) is idempotent. |
| 11a | Lakebase OAuth token-refresh helper | `app/backend/lakebase_token.py` | Python | ✅ Done (Session m); `LakebaseTokenManager` + `make_engine` for the Phase 7 BFF to import. |
| 12 | DAB bundle config | `databricks.yml` | YAML | ✅ Skeleton (Iter 1) |
| 13 | Pipeline notebooks (bronze/silver/gold) | `pipelines/0[1-3]_*.py` | Python (DLT) | Bronze ✅ (Iter 4, Phase 1.5 Excel pattern); silver/gold stubs |
| 13a | Phase 1.5 source workbook (generator output) | `data/seed/compass-source.xlsx` | XLSX (4 sheets) | ✅ Done (Iter 4) |
| 14 | Eval dataset (20 graded turns) | `eval/coop-eval-dataset.jsonl` | JSONL | ✅ Done (Iter 1, refined Iter 3) |
| 15 | Custom MLflow scorer | `eval/scorers.py` | Python | ✅ Done |
| 16 | Nightly eval runner stub | `eval/run_eval.py` | Python | ✅ Stub (Iter 3) |
| 17 | App scaffolding spec | `app/README.md` | Markdown | ✅ Spec; Phase 7 implementation lives in `app/backend/` + `app/frontend/` |
| 17a | FastAPI BFF | `app/backend/{main.py, config.py, schemas.py, auth.py, agent/, tools/, store/}` | Python | ✅ Scaffolded (Iter 6); lite-mode boot validated end-to-end against live Genie + KA |
| 17b | React + Vite frontend | `app/frontend/` | TS/React | ✅ Scaffolded (Iter 6); `npm install && npm run build` pending |
| 17c | App container + DAB resource | `app/Dockerfile`, `app/app.yaml`, `resources.apps.compass_app` in `databricks.yml` | Dockerfile + YAML | ✅ Iter 6 |
| 18 | Supervisor agent (MAS) | (in-workspace, Agent Bricks) | — | TODO (Phase 6) |
| 19a | Genie space — Co-op Utilization & Risk | (in-workspace, id `01f152f8ed8a...`) | — | ✅ Deployed; source in `genie/spaces/utilization-and-risk/` |
| 19b | Genie space — Marketing Effectiveness & ROI | (in-workspace, id `01f1532267c4...`) | — | ✅ Deployed; source in `genie/spaces/marketing-effectiveness-roi/` |
| 20 | KA index — COMPASS Co-op Program Handbook | (in-workspace, Agent Bricks; tile `f000ded6-362a-...`, endpoint `ka-f000ded6-endpoint`) | — | ✅ Deployed (Phase 4); 8 corpus docs indexed from `/Volumes/classic_stable_1zia5t_kp_catalog/compass_bronze/raw/ka-corpus/` |

---

## 12. Synthetic Data Specification

Volume targets (small enough to land in minutes on serverless, large enough that Genie answers feel real):

- **Dealers**: 820 (AMER 380, EMEA 260, APAC 180), tier mix 5/20/40/35.
- **Programs**: 6 active in current fiscal year, 4 retired.
- **Activity types**: 22 across 5 categories.
- **Fiscal calendar**: 3 fiscal years (FY24, FY25, FY26 partial), Steelcase fiscal March–Feb.
- **Allocations**: ~6,500 allocation events.
- **Claims**: ~28,000 claims across 3 years, with realistic state distribution (Draft 5%, Submitted 8%, Under_Review 12%, Approved 25%, Rejected 8%, Paid 38%, Expired 4%).
- **Sell-through orders**: ~480,000 order lines (manageable, not huge — Genie joins should stay fast).
- **Marketing events**: ~3,200 events.

Data generator (`data/generate-synthetic-data.py`):
- Uses **Polars + Mimesis** locally for portability; the same script also documents the Spark + Faker variant for in-workspace generation.
- Outputs Parquet to `data/seed/`; bronze ingestion notebook then lands them via Auto Loader.
- Plants two deliberate **demo signals**:
  - **Forfeiture-risk hotspot**: 23 AMER East dealers with unused balances > $40K and < 60 days to expiration — drives the hero moment.
  - **High-ROI activity**: "Digital — Programmatic Display" in EMEA shows clean lift signal vs control — drives the attribution moment.

---

## 13. Quality, Evaluation, and Observability

- **Tracing**: every agent turn → MLflow trace; parent supervisor span + child Genie/KA/tool spans; tags include `user_role`, `region`, `tool_path`.
- **Eval dataset**: 20 graded turns at v1 spanning Genie-only, KA-only, mixed, action-tool, refuse, and adversarial routes; held in `eval/coop-eval-dataset.jsonl`. Expand to 40+ as production traces are graded.
- **Scorers**: built-ins (Correctness, RetrievalGroundedness, Guidelines) + one custom `@scorer` named `policy_citation_present` that fails if a KA-routed answer omits a citation to a corpus doc.
- **Monitoring**: scheduled `mlflow.genai.evaluate` run nightly over a sample of production traces; alert if any scorer p50 drops > 5pp.

---

## 14. Security, Privacy, Governance

- All data is synthetic; no real PII. Dealer "emails" are `dealer####@example.invalid`.
- UC governance: row-level filter on `dim_dealer.region` so a regional channel manager sees only their region. Demo shows this with two user logins.
- Lakebase: OAuth tokens scoped to the app principal; no static creds checked into the repo.
- KA: corpus documents tagged with `confidentiality: internal` or `dealer-shareable`; the agent's system prompt enforces the audience scope.
- Audit: all metric-view queries and KA retrievals are visible in `system.access.audit`.

---

## 15. Build Phases & Sequencing

**Phase 0 — Specification (this doc) ✅**

**Phase 1 — Data foundation**
- DDL, synthetic data generator, ingestion pipeline, gold tables.

**Phase 1.5 — Bronze hydration via native Excel connector (DBR 17.1+)**
- Single source workbook `seed/compass-source.xlsx` with 4 sheets (`Allocations`, `ERP_Sales_Orders`, `Event_Registrations`, `Portal_Claims`) feeds the four previously empty `bronze.*` tables. Each DLT bronze table uses `cloudFiles.format = "excel"` with `dataAddress` pinning the sheet and `schemaEvolutionMode = "none"`. No JAR/PyPI dependency — native reader only. Production framing (Lakeflow Connect for SFDC/SAP, Auto Loader for portal/allocations/events) is documented in `demo-design.md §5.A` and is unchanged; Phase 1.5 is a deliberate demo-time consolidation, called out in `§5.D`. Hero cohort math is preserved bit-for-bit.

**Phase 2 — Semantic layer**
- 5 Metric Views; verify with hand-written SQL.

**Phase 3 — Genie Spaces** ✅ Deployed (2 distinct domain spaces)
- **Co-op Utilization & Risk** (id `01f152f8ed8a...`) — Maya persona. Tables: `compass_metric.{forfeiture_risk, claim_lifecycle, coop_program_metrics}` + 4 dim views. Drives Acts 2-3, 5, 7-8 (forfeiture, dealer drill, action, approvals, eval).
- **Marketing Effectiveness & ROI** (id `01f1532267c4...`) — Eliot persona. Tables: `compass_metric.{activity_lift, dealer_performance}` + 4 dim views. Drives Act 6 (top-5 activities, $7.40/$1 ladder).
- Source-of-truth artifacts (instructions, sample questions, certified SQL) Git-tracked in `genie/spaces/<domain>/`.

**Phase 4 — Knowledge Assistant** ✅ Deployed
- 8-doc corpus indexed in workspace as Agent Bricks KA "COMPASS Co-op Program Handbook" (tile `f000ded6-362a-476b-ab3f-1f6e1bfb6def`, endpoint `ka-f000ded6-endpoint`).
- Knowledge source: `/Volumes/classic_stable_1zia5t_kp_catalog/compass_bronze/raw/ka-corpus/` (8 markdown files; sizes match repo `ka-corpus/`).
- Instructions enforce: citation in `[KA-XXX-### §<section>]` form, audience+region scoping, FY26 currency, routing of metric questions to Genie and action requests to the app.

**Phase 5 — Lakebase** ✅ Deployed (Provisioned, migrated from Autoscale in Session p)
- Lakebase **Provisioned** instance `compass-lakebase-prov` (Postgres 16, capacity `CU_1`, read-write DNS `ep-raspy-credit-d2yhs2ud.database.us-east-1.cloud.databricks.com`). The original Autoscale project (`compass-lakebase`) was retired because Apps↔Autoscale OAuth auth is not yet GA per the Lakebase Autoscale skill ("Databricks Apps UI integration" is in the not-yet-supported list).
- `compass` schema + 11 tables created from `lakebase/schema.sql`; seed loaded from `lakebase/seed-data.sql` (6 users including `kaustav.paul@databricks.com`, Maya's pre-warmed chat session + 3 saved views, 5 pending claim reviews with 4 hero-cohort dealers, 4 user prefs).
- `compass.v_dealer` (843 rows) and `compass.v_coop_utilization_today` (3,042 rows; latest `date_key = 2026-10-13`) hydrated by `lakebase/hydrate_synced_views.py` — one-shot copy from UC via SQL warehouse + psycopg `COPY`. AMER East FY26 top-3 unused match the hero cohort byte-for-byte (Pivot $147.2K / Halcyon $118.4K / Northpoint $96.3K).
- OAuth tokens minted via `w.database.generate_database_credential(request_id=..., instance_names=[...])` (Provisioned API); the Phase 7 BFF rotates them via `app/backend/lakebase_token.py` (`LakebaseTokenManager` + `make_engine`); SQLAlchemy's `do_connect` event hook injects a fresh token per pool connection, `pool_pre_ping=True` recycles any connection whose token expired mid-pool.
- **Grants** in `lakebase/grants.sql` — idempotent; creates `compass_app` (full DML) and `compass_reader` (read-only) container roles, GRANTs App SP into `compass_app`. Apply with `psql -v app_sp_id=<uuid> -f lakebase/grants.sql`.
- **App resource binding**: `app.yaml` declares `resources: [{name: compass-lakebase, database: {instance_name: compass-lakebase-prov, permission: CAN_CONNECT_AND_CREATE}}]` so Databricks Apps platform attaches the Lakebase OAuth scope to the App SP automatically.

**Phase 6 — Supervisor Agent (MAS)**
- Genie + KA + 3 action tools; chat memory in Lakebase; MLflow tracing on.

**Phase 7 — App UI** ✅ Scaffolded (Iter 6 / DEV_LOG Session n)
- Databricks App (React + FastAPI) with chat pane, approval queue, nudge composer.
- Three capability modes selected by `COMPASS_AGENT_MODE` env var:
  - `lite` — Genie + KA only (Phases 3+4). No Lakebase, no Supervisor. Action tools are preview-only.
  - `standard` — adds Phase 5 (Lakebase) for persisted chat + live right-pane tabs.
  - `full` — adds Phase 6 (Supervisor MAS) for agent-driven routing and real action tools.
- Same code in all modes; only `agent/router`, `tools/actions`, and `store/memory` implementations swap at startup. See `app/README.md` and `demo-design.md §14`.
- **Validated end-to-end (lite):** KA returns assistant text + 3 corpus citations w/ excerpts; Genie returns hero AMER East FY26 forfeiture ($1.62M) — matches the seeded hero math byte-for-byte.
- **Open:** frontend `npm install`/`npm run build`; standard-mode live boot; `lakebase/grants.sql -v app_sp_id=<uuid>` apply after `databricks bundle deploy`; MLflow experiment id wire-up; Phase 6 MAS endpoint integration in `router_full.py`.

**Phase 8 — Evaluation harness**
- Eval dataset, scorers, nightly monitoring job.

**Phase 9 — Rehearsal**
- Click-script dry run, timing, backup recordings.

---

## 16. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Genie picks the wrong table when measures look similar | Medium | High | Disambiguate via metric view descriptions + sample questions; verify in Genie certification |
| KA hallucinates a policy not in corpus | Medium | High | Custom scorer `policy_citation_present`; system prompt forbids policy claims w/o citation |
| Synthetic data looks "too clean" and audience disengages | Medium | Medium | Plant realistic noise — rejected claims, late submissions, off-brand events |
| Action tools fire side effects during a demo | Low | High | Demo tenant only; nudge campaign writes to Lakebase, never sends real email |
| Lakebase cold-start latency on first demo turn | Medium | Medium | Pre-warm with a `SELECT 1` in the click-script's "open the app" step |
| Live demo network failure | Low | High | Pre-recorded backup video of the hero moment |

---

## 17. Open Questions (to resolve before customer)

1. Do we show **one persona** (Maya) or **two** (Maya + Eliot Director view)? Recommend **one** for a 25-min slot; tease Eliot's view as a sidebar.
2. Should the Genie space be **certified** in the demo workspace, or left in draft? Recommend **certified** to show governance maturity.
3. Do we include **Salesforce ingestion via Lakeflow Connect** as a live segment, or pre-loaded? Recommend **pre-loaded** with a 30-second mention of the connector.
4. Do we include **a brief Maya-as-dealer view** (Priya use case)? Recommend **no** for v1 to keep the storyline crisp.

---

## 18. Appendix — Glossary

- **Co-op / MDF** — Co-op marketing funds / Market Development Funds; manufacturer dollars made available to channel partners for approved marketing.
- **Sell-through** — Revenue from the dealer to the end customer (vs sell-in, which is from manufacturer to dealer).
- **Forfeiture** — Allocated co-op funds that expire unused at end of fiscal period.
- **Tier** — Dealer classification (Platinum / Gold / Silver / Authorized) that drives allocation formula and co-fund %.
- **Pre-approval** — Required for activities above a threshold (typically $5K); without it, a claim cannot be paid.
- **Brand compliance score** — Internal 0-100 score from creative review on a submitted asset.
- **MAS** — Multi-Agent System (Agent Bricks Supervisor Agent).
- **KA** — Knowledge Assistant (Agent Bricks).
- **Metric View** — UC-governed YAML-defined semantic metric.
