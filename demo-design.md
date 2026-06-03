# Steelcase COMPASS — Demo Design Document

**Companion to:** `demo-requirements.md` (WHY + WHAT) — this doc is the **HOW**.
**Owner:** Kaustav Paul
**Last updated:** 2026-05-18
**Status:** Draft 1 (covers Phases 0–6; Phase 7 app design is intentionally lighter)

---

## 1. Purpose & Scope

This document captures every **design decision** required to implement COMPASS (Co-op Marketing Program Analytics & Strategy System) as specified in `demo-requirements.md`. Where the requirements doc says *"a Knowledge Assistant grounded on the policy corpus"*, this doc says **how** it is grounded — chunking, tagging, retrieval, citation enforcement, governance. The intended audience is the engineer who will build the demo (and the SE/SA reviewing the work).

The doc is organized so that each section can be read independently by the function that owns it: data eng for §6–§8, semantics for §9, ML/agent for §11–§12, full-stack for §13, platform/devops for §16.

### In scope
- Component-level design for every layer named in `demo-requirements.md §5`.
- Source-data inventory with type, volume, format, landing, and refresh cadence (§5 below).
- Identifier schemes, naming, partitioning, SCD, and quality-rule placement.
- Conversational layer routing rules, retrieval strategy, citation enforcement.
- Action-tool side-effect boundaries (draft vs commit), idempotency keys.
- Observability taxonomy and the custom scorer's contract.

### Out of scope (for this iteration)
- Full app pixel design / Figma artifacts (Phase 7).
- Production multi-region deployment design (single-region demo).
- Disaster-recovery design for Lakebase (synthetic data, recoverable from seed).
- Cost optimization beyond serverless defaults.

---

## 2. Design Principles

Five principles that decide tradeoffs throughout the doc:

1. **Governed metrics first.** No business number reaches a user without going through a UC Metric View. If a question can't be answered by a metric view, the answer is "I don't have a governed metric for that yet."
2. **Citations are not optional.** Any policy / how-to answer must cite at least one corpus doc. Enforced by a custom MLflow scorer that fails the trace if no `KA-*` doc-ID appears.
3. **The agent stages, humans commit.** Action tools draft state in Lakebase and surface a preview. Sending email, paying claims, or any externally visible side effect is gated on an explicit user approval click — never on agent inference alone.
4. **One identity end-to-end.** OAuth on-behalf-of-user from Databricks App → UC → Genie → Lakebase. No service-principal "god mode" calls from the agent in user flows; RLS and column masks are evaluated against the actual user.
5. **Boring deployment.** Everything is one DAB. No ad-hoc notebooks, no console-pinned resources, no manual permission grants outside the bundle.

---

## 3. System Architecture (component view)

Same logical architecture as `demo-requirements.md §5.1`, with the design-level annotations the requirements doc deliberately omitted:

```
                                +---------------------------------------------------+
                                | Databricks App: compass-app                       |
                                |   React + Vite (UI)                               |
                                |   FastAPI (BFF, OAuth, MLflow tracing)            |
                                +---------------------------------------------------+
                                              |                   |
                                              | invoke            | DML (chat, approvals,
                                              v                   | nudges, saved views)
                                +-------------------------+       v
                                | Serving endpoint        |   +------------------------+
                                | compass-supervisor      |   | Lakebase (Postgres)    |
                                | Agent Bricks MAS        |<->| Schema: compass        |
                                +-------------------------+   | Synced views from UC   |
                                  |        |         |       +------------------------+
                            route v        v         v                        ^
                          +---------+ +--------+ +--------+                   | sync
                          | Genie   | |  KA    | | Action |                   | (synced
                          | space:  | | index: | | tools  |                   |  tables)
                          | coop-   | | coop-  | | (3)    |                   |
                          | program-| | hand-  |                              |
                          | analytics| | book  |                              |
                          +---------+ +--------+                              |
                              |          |                                    |
                              v          v                                    |
                       +-----------------+ +------------------+               |
                       | UC Metric Views | | UC Volume:       |               |
                       | metric.*        | | coop-corpus      |               |
                       +-----------------+ +------------------+               |
                              ^                  ^                            |
                              |                  |                            |
                       +-----------------+ +------------------+ +-------------+
                       | gold.* (Delta)  | | Auto Loader      | | gold ->     |
                       | streaming tables| | (markdown land)  | | lakebase    |
                       +-----------------+ +------------------+ |  reverse    |
                              ^                                 |  ETL job    |
                              |                                 +-------------+
                       +-----------------+
                       | silver.* (Delta)|
                       | SCD-2 dealer    |
                       +-----------------+
                              ^
                              |
                       +-----------------+ +------------------+ +--------------+
                       | bronze.*        | | Auto Loader (UC  | | Lakeflow     |
                       | landing         |<-| Volume CSV/JSON) | | Connect      |
                       +-----------------+ +------------------+ | (SFDC, ERP)  |
                                                                +--------------+

  Cross-cutting:  MLflow Tracing + Evaluation (every supervisor turn)
                  Unity Catalog (governance, RLS, column masks, lineage, audit)
```

Two non-obvious wiring decisions:
- **Lakebase is fronted by the BFF, not the agent.** The agent's action tools are FastAPI endpoints; FastAPI owns the Lakebase connection pool and writes through SQLAlchemy. The agent's "tool" is therefore just a function call into FastAPI. This keeps Lakebase credentials out of the model-serving endpoint.
- **The agent reads metric views via Genie, not via raw SQL.** Even when the agent needs to compose a follow-up question, it goes back through Genie so synonyms, certification, and SQL safety all apply.

---

## 4. Build Phase × Design Section Map

| Build phase (`demo-requirements.md §15`) | Design sections that must be settled first |
|---|---|
| 1. Data foundation | §5, §6, §7, §8 |
| 2. Semantic layer | §9 |
| 3. Genie space | §9, §11 |
| 4. KA | §10 |
| 5. Lakebase | §11 |
| 6. Supervisor Agent (MAS) | §12, §13 |
| 7. App | §14 |
| 8. Eval | §16 |
| 9. Rehearsal | §17 |

---

## 5. Source Datasets / Files — Full Inventory

This is the canonical list. **Two categories**: (A) production-shape sources we'd ingest at Steelcase, and (B) the synthetic artifacts we actually produce + commit in this repo for the demo.

### 5.A. Production-shape sources (simulated for the demo)

These are the systems the bronze layer is **designed against**. For the demo, the data is synthesized; for a real Steelcase build, these are the Lakeflow Connect / Auto Loader entry points.

| # | Source system | Dataset | Type | Volume (steady state) | Format | Bronze landing | Refresh cadence | Ingestion mechanism |
|---|---|---|---|---|---|---|---|---|
| 1 | Salesforce (CDPP) | Dealer master (Account, Tier, Region, Sales Rep) | Tabular / CDC | ~820 rows | Avro (CDC) | `bronze.sfdc_account` | Daily | **Lakeflow Connect — Salesforce** |
| 2 | SAP ERP | Sell-through orders (header + line) | Tabular / CDC | ~160k order lines / yr ⇒ ~480k rows over 3 FYs | CSV/Parquet via CDC | `bronze.erp_sales_order` | Daily | **Lakeflow Connect — SAP** (or batch fallback) |
| 3 | Co-op Portal (homegrown app) | Claim submissions (full payload) | Semi-structured | ~9–10k claims / yr ⇒ ~28k over 3 FYs | JSON (one object per claim) | `bronze.portal_claims` (raw JSON preserved in `raw_payload`) | Hourly | **Auto Loader** on UC Volume `/Volumes/steelcase_demo/raw/portal-claims/` |
| 4 | Channel Mktg Office | Allocation roster (per region per FY) | Tabular | ~6,500 allocations over 3 FYs | CSV (one file per region per FY) | `bronze.allocation_csv` | On allocation event (3–4×/yr) | **Auto Loader** on `/Volumes/steelcase_demo/raw/allocations/` |
| 5 | Event registration system | Marketing event registrations | Semi-structured | ~3,200 events over 3 FYs | CSV/JSON | `bronze.event_registration` | Hourly | **Auto Loader** on `/Volumes/.../events/` |
| 6 | Creative Review Pod (Brand-compliance tool) | Per-claim creative scores | Tabular | 1:1 with claim — ~28k rows | JSON, embedded in claim payload | column on `bronze.portal_claims` | with claim | inline (no separate land) |
| 7 | Channel Mktg Office (curated) | Reference data — programs, activities, regions | Tabular | 10 + 22 + 8 = 40 rows | CSV | `bronze.ref_program`, `bronze.ref_activity_type`, `bronze.ref_region` | Quarterly | Auto Loader on `/Volumes/.../ref/` |
| 8 | Confluence / LMS (curated) | Policy / handbook corpus (8 docs) | Unstructured | ~50 KB total Markdown (~10–12 H2 sections per doc, ~30 doc-ID-tagged chunks) | Markdown (.md) | UC Volume `/Volumes/steelcase_demo/raw/coop-corpus/` | On policy change (each FY + occasional in-year) | **Auto Loader** (notification-trigger) |
| 9 | Co-op Portal proof bundles | Per-claim proof artifacts (invoice, screenshots, photos) | Unstructured | ~28k bundles ⇒ ~300k files | PDF, PNG, JPG, MP4 | `/Volumes/.../claim-docs/` (path-only land for demo) | On submission | Auto Loader (path-only, no content parsing for v1) |

### 5.B. Synthetic artifacts produced + committed by the demo build

Everything below is generated locally by `data/generate-synthetic-data.py` and `data/build-gold.py` and lives under `data/seed/` (gitignored).

#### Silver-shaped (generator output)

| # | File | Logical role | Volume | Format | Notes |
|---|---|---|---|---|---|
| 1 | `data/seed/dealer.parquet` | Dim | **843 rows** (820 random + 23 pinned hero) | Parquet | Hero IDs `D-04711..D-04733`; Pivot Workplace Solutions = `D-04711` |
| 2 | `data/seed/program.parquet` | Dim | **10 rows** | Parquet | 6 active FY26 + 4 retired |
| 3 | `data/seed/activity_type.parquet` | Dim | **22 rows** | Parquet | 5 categories (Digital, Event, Showroom, Content, Sponsorship) |
| 4 | `data/seed/region.parquet` | Dim | **8 rows** | Parquet | AMER (3), EMEA (3), APAC (2) |
| 5 | `data/seed/fiscal_calendar.parquet` | Dim | **~1,460 rows** | Parquet | 4 fiscal years (FY23–FY26) of daily rows |
| 6 | `data/seed/coop_allocation.parquet` | Fact | **~6,500 rows** + **23 hero rows** | Parquet | Hero allocations sized so unused = pinned $1.62M total |
| 7 | `data/seed/coop_claim.parquet` | Fact | **~28,000 rows** + **~150 hero rows (Paid)** | Parquet | State mix Draft 5% / Submitted 8% / Under_Review 12% / Approved 25% / Rejected 8% / Paid 38% / Expired 4% |
| 8 | `data/seed/sell_through_order.parquet` | Fact | **~480,000 rows** | Parquet | One row per order line over 3 FYs |
| 9 | `data/seed/marketing_event.parquet` | Fact | **~3,200 rows** | Parquet | One row per event |

#### Gold (build-gold.py output)

| # | File | Logical role | Volume | Format | Notes |
|---|---|---|---|---|---|
| 10 | `data/seed/gold/fact_coop_utilization_daily.parquet` | Gold fact (snapshot) | **~7,000 rows** at as-of (1 row per active dealer × program) | Parquet | Includes precomputed `expected_forfeit_usd` |
| 11 | `data/seed/gold/fact_claim_sla.parquet` | Gold fact | **~28,000 rows** | Parquet | 1 row per claim with cycle-time decomposition |
| 12 | `data/seed/gold/fact_dealer_performance_monthly.parquet` | Gold fact | **~30,000 rows** (843 dealers × ~36 months) | Parquet | Includes attributed lift |
| 13 | `data/seed/gold/fact_activity_lift.parquet` | Gold fact (rollup) | **~528 rows** (22 activities × 8 regions × 3 FYs) | Parquet | Drives the Act 6 "top-5 activities" turn |

#### Knowledge Assistant corpus (committed in repo)

| # | File | Audience | Region | Approx size | Sections (H2) | Doc ID |
|---|---|---|---|---|---|---|
| 1 | `ka-corpus/coop-program-handbook.md` | internal+dealer | global | ~7 KB | 12 | `KA-HANDBOOK-001` |
| 2 | `ka-corpus/eligibility-matrix.md` | internal+dealer | global | ~6 KB | 5 | `KA-ELIG-002` |
| 3 | `ka-corpus/claim-submission-playbook.md` | internal+dealer | global | ~7 KB | 11 | `KA-PLAYBOOK-003` |
| 4 | `ka-corpus/brand-compliance-spec.md` | internal+dealer | global | ~6 KB | 10 | `KA-BRAND-004` |
| 5 | `ka-corpus/regional-addendum-amer.md` | internal+dealer | AMER | ~5 KB | 11 | `KA-AMER-005` |
| 6 | `ka-corpus/regional-addendum-emea.md` | internal+dealer | EMEA | ~6 KB | 11 | `KA-EMEA-006` |
| 7 | `ka-corpus/forfeiture-and-extension-policy.md` | internal+dealer | global | ~5 KB | 9 | `KA-FORFEIT-007` |
| 8 | `ka-corpus/co-op-faq.md` | dealer | global | ~6 KB | 30 Q&A | `KA-FAQ-008` |
| **Total** | | | | **~48 KB** | **~80 H2 chunks** | |

#### Lakebase seed (operational state at demo-time)

| # | Table | Rows | Purpose |
|---|---|---|---|
| 1 | `compass.app_user` | 5 | Maya, Eliot, Priya (D-04711), Jordan, Renske |
| 2 | `compass.chat_session` | 1 | Maya's pre-warmed session |
| 3 | `compass.saved_view` | 3 | Maya's pinned views |
| 4 | `compass.claim_review` | 5 | Pending approvals (4 hero-cohort, 1 random) |
| 5 | `compass.user_preference` | 4 | Default layouts and display prefs |

#### Eval dataset

| # | File | Volume | Format | Purpose |
|---|---|---|---|---|
| 1 | `eval/coop-eval-dataset.jsonl` | 20 graded turns | JSONL (MLflow-compatible) | Nightly + manual evaluation across Genie / KA / tool / refuse / adversarial |

### 5.C. Source-to-target lineage summary

```
bronze.sfdc_account              → silver.dealer (SCD-2)            → gold.dim_dealer
bronze.erp_sales_order           → silver.sell_through_order        → gold.fact_dealer_performance_monthly
bronze.portal_claims (JSON)      → silver.coop_claim                → gold.fact_claim_sla, gold.fact_coop_utilization_daily, gold.fact_activity_lift
bronze.allocation_csv            → silver.coop_allocation           → gold.fact_coop_utilization_daily
bronze.event_registration        → silver.marketing_event           → (joined to claims for attribution)
bronze.ref_program/activity/...  → silver.program/activity_type/... → gold.dim_program/dim_activity_type/...
UC Volume markdown corpus        → KA index "Co-op Program Handbook"
gold.fact_coop_utilization_daily → compass_lakebase_sync.coop_utilization_today (CDF Delta) → compass.v_coop_utilization_today  (one-shot hydrate; Phase 5)
gold.dim_dealer                  → compass_lakebase_sync.dealer_current          (CDF Delta) → compass.v_dealer                  (one-shot hydrate; Phase 5)
```

**As-built note (Phase 5):** The two Lakebase mirror tables are populated by `lakebase/hydrate_synced_views.py` — a one-shot `COPY` from UC via the SQL warehouse, sized for the static FY26 demo. The Lakebase instance is **Provisioned** (`compass-lakebase-prov`, CU_1, Postgres 16), not Autoscale: Apps↔Autoscale auth is not yet GA, so Provisioned is the path that lets the deployed App SP authenticate via OAuth. The intermediate `compass_lakebase_sync.{dealer_current, coop_utilization_today}` Delta tables are created CDF-enabled so a future upgrade to UC-managed continuous synced tables (via `create_synced_database_table`) is a drop-in replacement — same source columns, same target schemas.

### 5.D. Phase 1.5 — single-workbook bronze hydration (demo shortcut)

For Phase 1.5 the demo bundles four of the streaming feeds from §5.A (SAP ERP, portal claims, allocations, event registrations) into **one source workbook** to showcase the native Databricks Excel reader (DBR 17.1+). This is a demo-time consolidation only — §5.A remains the design target for a real Steelcase build.

| Sheet                    | Bronze target                | Generator origin                                      |
|--------------------------|------------------------------|-------------------------------------------------------|
| `Allocations`            | `bronze.allocation_csv`      | `coop_allocation.parquet` (columns renamed to bronze) |
| `ERP_Sales_Orders`       | `bronze.erp_sales_order`     | `sell_through_order.parquet` + `currency = 'USD'`     |
| `Event_Registrations`    | `bronze.event_registration`  | `marketing_event.parquet`                             |
| `Portal_Claims`          | `bronze.portal_claims`       | `coop_claim.parquet` (no `raw_payload` for the demo)  |

**Reader configuration** (per sheet, in `pipelines/01_bronze_landing.py`):
- `cloudFiles.format = "excel"` — native, no Maven/PyPI dep
- `dataAddress = "'<SheetName>'!A1"` — sheet selection
- `headerRows = 1`
- `cloudFiles.schemaEvolutionMode = "none"` — required for streaming Excel
- adds provenance columns `_ingest_ts`, `_source_file`, `_source_sheet`

**Volume drop location:** `/Volumes/steelcase_demo/raw/compass-source/`.

**Out of scope for Phase 1.5:** SFDC dealer master (`bronze.sfdc_account`) and the three `bronze.ref_*` tables stay on their §5.A mechanisms (Lakeflow Connect / Auto Loader CSV) — the four-sheet workbook only replaces the four streaming feeds that previously had no implementation. Silver, gold, metric views, KA, Lakebase, and the click-script flow are untouched.

---

## 6. Catalog & Schema Design

```
catalog:  steelcase_demo
├─ bronze          raw / append-only / typed minimally
├─ silver          curated, typed, conformed, SCD-2 where applicable
├─ gold            materialized aggregates, conformed dims
├─ metric          metric views (one YAML per view)
└─ lakebase_sync   reverse-ETL target metadata only — actual tables are in Lakebase
```

**Design rules:**
- Catalogs and schemas are created by the DAB. Manual creation is not allowed.
- `bronze` rows are immutable — schema evolution is permitted, but row-level mutations come via Delta CDF, not in place.
- `silver` schema enforces **CHECK constraints** (see `data/ddl/02-silver.sql`). Failing rows are quarantined into `<schema>.<table>_quarantine` (DAB to create on first violation).
- `gold` tables are **Streaming Tables** in the real pipeline; the demo's `build-gold.py` simulates the eventual SDP definition.
- `metric` schema holds only views — no tables, no procedures.

---

## 7. Data Model Design Decisions

This section captures the **why** behind choices in `data/data-model.md`.

### 7.1 Identifier scheme

| Entity | Format | Example | Notes |
|---|---|---|---|
| Dealer | `D-NNNNN` | `D-04711` | 5-digit zero-padded. Random dealers occupy `D-01001..D-01820`; hero dealers reserved at `D-04711..D-04733` to avoid collision and to keep the "#4711" reference in the requirements doc deterministic. |
| Allocation | `AL-<12hex>` or `AL-HERO-<dealer_id>` | `AL-HERO-D-04711` | Hero IDs are human-readable for ease of audit during the demo. |
| Claim | `CL-FY26-NNNNNN` | `CL-FY26-009842` | Six-digit sequence, fiscal year embedded for partition predicate pushdown. Hero claims start at 900,000 to avoid collision. |
| Pre-approval | `PA-<8hex>` | `PA-9C42AB10` | Random; no semantics. |
| Reviewer | `RV-NN` | `RV-23` | Reviewer pool small (~40); fine to overload across regions for the demo. |
| Region | `RGN-<REGION>-<SUB>` | `RGN-AMER-EAST` | Stable, human-readable; encodes region in the key. |
| Program | `PRG-<FY>-<NAME>` | `PRG-FY26-COOP-MAIN` | Embeds FY for partition predicate pushdown. |
| Activity type | `ACT-<CAT>-<NAME>` | `ACT-DIG-PROG-DISPLAY` | Encodes category, helping Genie disambiguate without joins. |

### 7.2 SCD strategy

- **`silver.dealer`** is SCD-2 (effective_from / effective_to / is_current). Tier and territory changes are common; we need correct attribution to prior-year tier.
- **`silver.program`, `silver.activity_type`, `silver.region`** are Type-1 — they change rarely; if they do, we accept "as of now" semantics for the demo.
- Reference doc rows in `ka-corpus/*.md` carry an `effective_date` and `expires` in frontmatter; the KA index reads these to scope retrieval to the active FY.

### 7.3 Partitioning

- `silver.coop_claim`, `silver.coop_allocation`, `silver.sell_through_order`, `silver.marketing_event` partition by `fiscal_year`. Queries are nearly always FY-scoped, and the cardinality is right (3 partitions for steady state, 4 once FY27 begins).
- `silver.dealer` partitions by `is_current` to make the very common current-only filter cheap.
- Gold tables partition by `fiscal_year`.

### 7.4 Quality rule placement

| Rule | Enforced where | Failure handling |
|---|---|---|
| `dealer_id IS NOT NULL` on facts | bronze→silver pipeline | quarantine + nightly report |
| `requested_amount_usd > 0` | silver CHECK constraint | quarantine |
| `status` is one of the enum values | silver CHECK constraint | quarantine |
| `paid <= approved` (status=Paid) | silver CHECK constraint | quarantine + alert |
| Pre-approval present when required (matrix §2) | gold derivation, surfaces as a column | flag, don't quarantine |
| Sum reconciliation (allocations CSV vs silver) | nightly reconciliation job | report only |

### 7.5 Currency handling

- All currency columns are `DECIMAL(p, 2)`, **always USD-normalized at land time**.
- The portal payload retains local currency in `raw_payload`; conversion uses the daily ECB reference rate on submission date for EMEA, MXN→USD wire spot for AMER-MX, etc.
- The metric view formatter (`{ type: currency, currency_code: USD }`) trusts the data; the UI never re-converts.

---

## 8. Synthetic Data Generation Design

### 8.1 Determinism vs realism

- **Deterministic** for hero dealers (`HERO_DEALERS` constant in `generate-synthetic-data.py`): IDs, names, tiers, FY26 unused balances are all pinned. Sum of unused = **$1,619,400** ≈ "$1.62M".
- **Pseudo-random** for the other 820 dealers; seeded with `SEED = 20260518` so the random draws are repeatable per machine.
- **Mid-band realism**: state distributions and lognormal amount distributions chosen so a casual eye believes the data is real, but no detail is so peculiar that the demo gets sidetracked by anomaly questions.

### 8.2 Planted signals

| Signal | What it drives | How it's planted |
|---|---|---|
| Hero forfeiture cohort | Act 2 (`"$1.62M across 23 dealers"`) | 23 named dealers in AMER East, deterministic allocations and Paid claims so `allocated - paid = pinned_unused`. |
| Top-3 named dealers | Act 2 narrative | First three hero entries: Pivot Workplace Solutions, Halcyon Office Group, Northpoint Workspaces, with $147.2K / $118.4K / $96.3K respectively. |
| Activity lift ladder | Act 6 ("top 5 activities") | `LIFT_FACTOR` dict in `build-gold.py` pins Programmatic Display = 7.4×, A+D Event = 5.1×, Hybrid Work Zone = 4.2×, ABM Enterprise = 3.8×, NeoCon Regional = 2.9×. |
| EMEA digital ROI | Backup beat (Eliot view) | Bonus boost in `gen_claims` for EMEA × Programmatic Display sets `approved = requested`. |
| Approval queue overlap | Act 8 ("4 also have pending claims") | Lakebase `claim_review` seed re-points 4 of 5 pending rows to hero-cohort dealers. |

### 8.3 Generator → bronze → silver path (production)

In the real Steelcase build, the generator output is the **handoff contract** for source teams:
1. Salesforce team ensures dealer rows match the `silver.dealer` shape post-CDC.
2. Portal team ensures the JSON export carries every field the generator emits.
3. Allocation roster team uses the CSV column order the generator uses.

For the demo, `build-gold.py` plays the role of the Spark Declarative Pipeline.

---

## 9. Semantic Layer (Metric Views) Design

Five YAMLs in `metric-views/` (`coop_program_metrics`, `dealer_performance`, `activity_lift`, `claim_lifecycle`, `forfeiture_risk`). Design decisions:

### 9.1 What goes in a metric view vs gold

- **Heavy compute** (probabilistic forecasts, attribution joins, window functions) is materialized in **gold**. Metric views aggregate; they don't compute.
- This is what made `forfeiture_risk.expected_forfeit_usd` flip from a nested-subquery expression to a simple `SUM` after Iteration 1.

### 9.2 Joins

Every metric view joins to the same dim set: `dim_dealer`, `dim_program`, `dim_region`, `dim_fiscal_calendar`. This pays off in Genie — synonyms like "dealer" and "region" resolve consistently regardless of which view answers the question.

### 9.3 Dimension naming for Genie

- Dimensions use the user-facing name (`dealer_name`, `region`, `tier`) — not the surrogate key — so Genie's NL → SQL has the right tokens to match.
- Where a name might collide (`region` is both the column and a sub_region adjective), `synonyms:` in YAML disambiguates.

### 9.4 Synonyms strategy

Every YAML carries a `synonyms:` block. The list is drafted from real channel-marketing language: *"burn rate"* for utilization, *"leakage"* for forfeiture, *"at-risk"* for dealers near expiration. This is the single biggest factor in Genie answer quality and is the place to invest before certification.

### 9.5 Certification

- The Genie space is **certified** before the demo. Certification process: run the 20 eval-dataset questions, mark each verified answer.
- A view's "verified questions" become Genie's example questions.

---

## 10. Knowledge Assistant Corpus Design

### 10.1 Chunking

- **One chunk per H2 section.** This matches the way the corpus is written (every H2 is a self-contained policy unit) and gives retrieval a sweet-spot chunk size (~700 tokens median, ~1500 max).
- Tables embedded under an H2 stay with their parent chunk.
- The chunk metadata carries `doc_id`, `section_id` (e.g., `§3.2`), `audience`, `region`, `effective_date`, `confidentiality`.

### 10.2 Indexing & retrieval

- Vector index on the chunk text (default embedding endpoint).
- Hybrid retrieval (BM25 + vector), top-K = 6.
- **Filter at retrieval time** by `audience` (dealer vs internal) and `region` (AMER / EMEA / global), pulled from the user's app_user row.

### 10.3 Citation contract

- Every KA-routed answer **must** include at least one `KA-*` doc-ID citation.
- The agent system prompt enforces this:
  > "When answering a policy or how-to question, you must cite the supporting document(s) using the doc_id (e.g., `[KA-ELIG-002 §3.2]`). If you cannot ground your answer in the retrieved corpus, say 'I don't have authoritative source for that' and route the user to their CMM."
- Enforced post-hoc by the `policy_citation_present` scorer (see §16.3).

### 10.4 Refresh

- Corpus refresh on policy change (`effective_date` updated) triggers re-indexing via the DAB-managed job.
- Versioning is by `effective_date`; superseded versions remain in the index but are filtered out by date.

---

## 11. Genie Space Design

### 11.1 Scope

The Genie space "Co-op Program Analytics" is grounded on:
- The 5 metric views (`metric.*`).
- The conformed dim views in `gold.dim_*`.
- The hero fact `gold.fact_activity_lift` (because it has the lift methodology version column).

The space is **not** grounded on silver tables. Silver is for engineering; semantic governance is for users.

### 11.2 Sample questions (drives certification)

Pre-loaded questions, grouped by metric view:

- `coop_program_metrics`: "Show utilization rate by region YTD", "Top 20 dealers by paid USD in FY26", "Compare FY25 forfeiture rate vs FY26".
- `forfeiture_risk`: "What is AMER East's Q4 forfeiture risk?", "Which dealers in EMEA have unused balance > €50K?".
- `dealer_performance`: "Best 5 activity types by revenue per co-op dollar in AMER", "EMEA Programmatic Display lift in FY26".
- `claim_lifecycle`: "Median claim cycle time by region", "First-pass approval rate by activity category", "Which reviewers are above the SLA p90?".

### 11.3 Disambiguation

- View-level descriptions are written to be **mutually distinguishing**: `coop_program_metrics` is "program health"; `forfeiture_risk` is "what will expire if we don't act"; `claim_lifecycle` is "how fast is the workflow"; `dealer_performance` is "what came back as revenue."

---

## 12. Supervisor Agent (MAS) Design

### 12.1 Topology — hybrid (Phase 6.1)

```
                ┌──────────────────────────────┐
                │ Action-gate supervisor       │
                │ (foundation model, embedded) │
                │ tools: query, advance_claim, │
                │ create_nudge_campaign,       │
                │ save_view, refuse            │
                └────────────┬─────────────────┘
                 ask vs do
        ┌─────────────┬─────┴──────────┬──────────┐
        ▼             ▼                ▼          ▼
     query         action(3)       refuse        (no tool)
        │             │                              │
        ▼             ▼                              ▼
 ┌─────────────┐  tool_preview                    fallback
 │ compass-    │  card → UI                       → MAS
 │ supervisor  │  Confirm →
 │ (Agent      │  BFF →
 │ Bricks MAS) │  Lakebase
 │ tile        │
 │ 2a692b50…   │
 └──────┬──────┘
        │ MAS routes between sub-agents
   ┌────┼──────────────┐
   ▼    ▼              ▼
util_risk marketing handbook_expert
analyst   analyst   (KA)
(Genie A) (Genie B)
```

**Why hybrid:** MAS executes tools server-side and returns a final assistant turn, so a pure-MAS implementation cannot surface a structured `tool_preview` for the §13.4 Confirm-before-write gate. Splitting the supervisor into (a) an in-process *action gate* and (b) the Agent Bricks MAS for reads preserves the audit-loggable confirmation moment while still putting a real MAS surface in the workspace. Cost: one extra LLM hop on read turns (action-gate → MAS), no extra hop on write turns.

**Components (Phase 6.1, as built):**

- **Action gate** — `app/backend/agent/supervisor.py`, foundation model `databricks-claude-sonnet-4-6` (env: `COMPASS_FM_ENDPOINT`). 5 tools: `query`, `advance_claim`, `create_nudge_campaign`, `save_view`, `refuse`.
- **MAS** — `compass-supervisor`, tile `2a692b50-bcd1-41cc-b1a2-182cf596a5fc`, endpoint `mas-2a692b50-endpoint` (env: `COMPASS_SUPERVISOR_ENDPOINT`). 3 sub-agents: `util_risk_analyst` (Genie space `01f152f8ed8a…`), `marketing_analyst` (Genie space `01f1532267c4…`), `handbook_expert` (KA tile `f000ded6-362a-…`).
- **Router** — `app/backend/agent/router_full.py`. `query` → `workers.query_mas`; actions → `tool_preview`; refuse → refuse turn.

### 12.2 Routing rules

Two-layer routing reflects the hybrid:

**Action gate (system-prompt-level):**

| Intent signal | Tool |
|---|---|
| User is ASKING (any topic — number, rule, eligibility, how-to) | `query` → forward to MAS |
| User is asking the agent to DO something (approve/reject claim, draft nudge, save view) | matching action tool |
| `channel_mgr` asks about another region | `refuse` |
| `dealer` asks about another dealer | `refuse` |

**MAS (instructions-level — owns Genie/KA choice):**

| Intent signal | Sub-agent |
|---|---|
| "How many" / "show me" / a measure (forfeit, unused, paid, balance, tier) | `util_risk_analyst` |
| ROI / lift / sell-through / activity / campaign / revenue | `marketing_analyst` |
| Policy / eligibility / "is X allowed" / "what's the rule" / "how do I" | `handbook_expert` |

### 12.3 Chat memory

- Per-session memory stored in `compass.chat_session.supervisor_state` (JSONB).
- Rolling-window summarization triggered every 10 turns: the summary replaces the oldest 6 turns in the supervisor's context.
- `chat_turn` table preserves the full transcript for traceability (trace_id, latency_ms).

### 12.4 Tool calling shape

The action gate emits OpenAI-format `tool_calls` against the FM endpoint. The BFF either (a) forwards `query` turns to the MAS endpoint (`POST /serving-endpoints/mas-2a692b50-endpoint/invocations` with `{"input":[…]}` Responses shape) and parses the routed sub-agent + final assistant text, or (b) executes action tools by returning a `tool_preview` payload, then writing to Lakebase on user Confirm.

### 12.5 What the agent **cannot** do

- Send email (must stage in `nudge_campaign` as `Draft`).
- Pay claims (must mark `PaidStaged`; finance disburses).
- Bypass RLS by switching execution identity.
- Edit a metric view definition.
- Re-index the KA corpus.

These restrictions are enforced both in the system prompt and structurally (the BFF endpoints don't exist).

---

## 13. Action Tools Design

Three tools registered with the supervisor:

### 13.1 `create_nudge_campaign(dealer_ids: list[str], template_id: str, deadline: date, notes: str | None) -> NudgeDraft`

- **Side effect:** writes one `nudge_campaign` row (status=`Draft`) + N `nudge_recipient` rows.
- **Returns:** the campaign_code, recipient count, and personalized previews for top-3 recipients.
- **Idempotency:** call hash = sha256(user_id + sorted(dealer_ids) + template_id + deadline). If a Draft with the same hash exists in the last 5 minutes, return the existing draft instead of creating a new one.
- **Visibility:** `Draft` only — `Queued` requires a separate POST from the UI.

### 13.2 `advance_claim(claim_id: str, decision: 'Approve' | 'Reject', note: str, rejection_code: str | None = None) -> ClaimReviewState`

- **Side effect:** updates `claim_review` row; emits an `audit_log` row.
- **Returns:** the updated state.
- **Idempotency:** if claim is already in a terminal state, return the existing state with `was_idempotent: true`.
- **Guardrails:** rejection requires a `rejection_code`; the BFF validates it against the enum.

### 13.3 `save_view(name: str, filter_payload: dict, description: str | None = None, pinned: bool = False) -> SavedView`

- **Side effect:** UPSERT into `saved_view` keyed by `(user_id, name)`.
- **Returns:** the saved view's id.
- **Validation:** `filter_payload.metric_view` must be one of the 4 known views; otherwise 400.

### 13.4 Audit log

Every tool call writes an `audit_log` row capturing `user_id`, `session_id`, `action`, `target_type`, `target_id`, `payload_json`, `trace_id`. This is the basis for the "agent did X" question in any post-hoc review.

---

## 14. App / UI Design (Phase 7 — short version)

See `app/README.md` for the full routes / stack / capability-matrix spec. The Phase 7 scaffold (DEV_LOG Session n, 2026-05-19) implemented against this spec. Concrete locations:

| Concern | File |
|---|---|
| Mode selection / env-var contract | `app/backend/config.py` |
| Routes | `app/backend/main.py` |
| Pydantic models | `app/backend/schemas.py` |
| Auth (OAuth header → `compass.app_user`) | `app/backend/auth.py` |
| Router interface + lite (Genie + KA via regex) + full (MAS stub) | `app/backend/agent/{router.py, router_lite.py, router_full.py}` |
| Action-tool interface + preview impl + Lakebase impl | `app/backend/tools/{actions.py, tools_preview.py, tools_lakebase.py}` |
| Session/turn memory interface + ephemeral impl + Lakebase impl | `app/backend/store/{memory.py, memory_ephemeral.py, memory_lakebase.py}` |
| Lakebase OAuth-token refresh + SQLAlchemy engine factory | `app/backend/lakebase_token.py` |
| React + Vite SPA | `app/frontend/src/{App.tsx, api.ts, components/Chat.tsx, components/RightPane.tsx}` |
| Container build + Apps runtime spec | `app/Dockerfile`, `app/app.yaml`, `app/requirements.txt` |
| DAB resource | `resources.apps.compass_app` block + 12 vars in `databricks.yml` |

Design highlights:

- **Modular by phase.** A single env var `COMPASS_AGENT_MODE = lite | standard | full` selects which downstream phases the app needs:
  - `lite` — Phases 3 + 4 only (Genie + KA). BFF owns intent routing; no Lakebase; no Supervisor; action tools are preview-only.
  - `standard` — adds Phase 5 (Lakebase) for persisted chat + live approval / nudge / saved-view tabs.
  - `full` — adds Phase 6 (Supervisor MAS) for agent-driven routing and the 3 real action tools.
  Same FastAPI + React codebase across all three; only the implementations of `agent/router.py`, `tools/actions.py`, and `store/memory.py` are swapped at startup. This keeps Phase 7 unblocked while 5/6 are in flight and lets us ship a "Genie+KA-only" preview to customers who haven't deployed Lakebase yet.
- **Two-pane layout.** Left = chat. Right = tabs (Approval Queue, Nudges, Saved Views). Tabs disabled in the current mode render a coachmark naming the missing phase, not blank space.
- **Chat affordances**: starter prompts (sourced from Genie sample questions), citation chips (open side panel with corpus excerpt), "Show metric & SQL" disclosure (renders the Genie-generated SQL and the lineage link), inline action-tool preview cards.
- **Region & tier badges in the header** — show that governance is on, even before the user asks a question. A **mode badge** sits next to them so capability boundaries are visible to anyone watching the demo.
- **Streaming responses** via SSE; thinking states surfaced to avoid dead air.

### 14.1 Wire-format gotchas surfaced during Phase 7 scaffold (Session n)

- **Agent Bricks KA serving endpoint expects the Responses-style `{"input": [{role,content}]}` payload, not OpenAI Chat `{"messages":...}`.** SDK's typed `serving_endpoints.query()` only types Chat. The lite-mode router calls the endpoint via `httpx.post` with `WorkspaceClient.config.authenticate()` headers (`router_lite._invoke_ka`).
- **KA citations live in `output[*].content[*].annotations[*]` with `type=url_citation`.** Each annotation's `title` is the corpus filename and `url` carries a `#:~:text=…` fragment that the frontend uses as a tooltip excerpt. Doc-id-in-text (`[KA-XXX-### §<section>]`) is *not* what the KA emits in practice — it's not necessary for the citation contract because every annotation already points at a corpus file. `custom_outputs.sources_used` is a bool (whether the corpus was consulted), not a list.
- **Genie SDK's `resp.content` is the user's question.** The assistant's response text is in `resp.attachments[*].text.content` (or `resp.attachments[*].query.description` for SQL-only replies). The lite router falls back to summarising the first 3 result rows if neither is present.
- **Eager `WorkspaceClient()` blocks app boot when default-profile creds are stale.** Both routers lazy-init `self.w` via a `@property` so the app boots without Databricks auth (helpful for Docker builds and CI).

---

## 15. Identity, Auth & Governance Design

### 15.1 Auth flow

```
Browser ── OAuth login ──> Databricks App
   ▲                          │
   │       redirect           │ on-behalf-of token
   └──────────────────────────┘
                              │
                              ▼
                          FastAPI BFF ──▶ UC (Genie, MV, Volumes) via user identity
                                       └▶ Lakebase via OAuth (Lakebase OAuth-on-behalf-of)
                                       └▶ Serving endpoint (supervisor) — service identity
```

The serving endpoint runs as a service principal (the agent itself doesn't need a user identity). But every **data read** (UC query, Lakebase query) goes through the user identity, so RLS and column masks apply.

### 15.2 Row-level security

- `silver.dealer` has a row filter:
  ```
  CREATE FUNCTION dealer_region_filter(region_id STRING)
  RETURNS BOOLEAN
  RETURN
    IS_MEMBER('compass_global_admins') OR
    region_id = (SELECT region_id FROM compass.app_user WHERE email = current_user());
  ```
  This filter is **declared but not yet deployed** — it depends on `compass.app_user` being reachable from UC. The original plan was to reverse-sync the Lakebase `compass.app_user` table back to UC as `lakebase_sync.app_user`; that reverse direction isn't currently supported on Lakebase Autoscale (only UC → Lakebase). For Phase 5/7 we enforce region/tier scoping in the BFF's SQL `WHERE` clauses (joining `compass.app_user` on the OAuth subject) so the same logic also runs in `lite` mode without Lakebase. Membership in `compass_global_admins` bypasses the filter for Eliot's director view.
- Same filter, when deployed, will propagate through `gold.dim_dealer` (view) and be inherited by metric views.

**Lakebase grants** are applied via `lakebase/grants.sql` once the COMPASS app's service principal exists. The script creates two NOLOGIN container roles: `compass_app` (full DML on `compass.*`) and `compass_reader` (SELECT only). The App SP is `GRANT`ed into `compass_app` via `psql -v app_sp_id=<uuid>`. Postgres RLS is intentionally **not** enabled — the BFF speaks a single SP identity, so per-end-user RLS would require `SET LOCAL` on every pool checkout and fork the scoping logic between `lite` and `standard/full`.

### 15.3 Column masking

- `dim_dealer.sales_rep_id` and `dim_dealer.salesforce_account_id` are masked for `role = 'dealer'`.

### 15.4 KA scoping

The KA system prompt includes the user's `role` and `region`; the retrieval filter on `audience` and `region` is applied before the LLM sees any chunks.

---

## 16. Observability Design

### 16.1 Tracing

- **Tracing destination:** MLflow experiment `/Shared/steelcase-demo/compass-experiment` (parametrized in DAB).
- **Spans:**
  - Root span: `supervisor.turn` (user-facing turn).
  - Child spans: `genie.query`, `ka.retrieve`, `ka.synthesize`, `tool.<name>`.
  - Tags on every span: `user.role`, `user.region`, `chat.session_id`, `chat.turn_index`, `tool.routed`.

### 16.2 Eval dataset

- `eval/coop-eval-dataset.jsonl` — 20 graded turns; schema in `eval/README.md`.
- Each row carries `expected_tool`, `expected_facts`, `must_cite_corpus`, `guidelines`, and persona tags.
- Used both for nightly batch eval and as a smoke test before demo rehearsals.

### 16.3 Scorers

| Scorer | Built-in / custom | Pass criterion |
|---|---|---|
| `Correctness` | built-in | Answer contains all `expected_facts` |
| `RetrievalGroundedness` | built-in | KA-routed turns are supported by retrieved chunks |
| `Guidelines` | built-in | Each rule in `guidelines` array is met |
| `policy_citation_present` | **custom**, `eval/scorers.py` | Any KA-routed (or `must_cite_corpus`) turn contains a `KA-*` doc-ID |

### 16.4 Nightly job

- DAB job `compass-eval-nightly` runs daily at 06:00 UTC.
- Inputs: a sample of yesterday's production traces + the seed eval dataset.
- Output: MLflow eval run with the four scorers; alert (Slack / email) on p50 drop > 5pp on any scorer.

---

## 17. Deployment Design (DAB)

### 17.1 One bundle, multiple targets

`databricks.yml` defines:
- 1 catalog, 5 schemas
- 1 warehouse (`co-op-demo-wh`)
- 1 pipeline (`compass-bronze-silver-gold`)
- 1 nightly job (`compass-eval-nightly`)
- 1 app (`compass-app`)
- Targets: `dev` (default), `prod`

### 17.2 Required out-of-band resources

These are provisioned by FEVM (or manually), not by the bundle:

- The workspace itself (FEVM `databricks-workspace` template). **Live as `fe-vm-classic-stable-1zia5t-kp`** (catalog `classic_stable_1zia5t_kp_catalog`, `compass_*` schemas — see DEV_LOG Session d).
- The Lakebase instance — **`compass-lakebase-prov` (Provisioned, Postgres 16, capacity `CU_1`, read-write DNS `ep-raspy-credit-d2yhs2ud.database.us-east-1.cloud.databricks.com`).** Provisioned in Phase 5 (Session l, migrated from Autoscale to Provisioned in Session p — Apps↔Autoscale auth not yet GA).
- The Genie spaces (created in UI, certified, then referenced) — **2 spaces live: Co-op Utilization & Risk `01f152f8ed8a...`, Marketing Effectiveness & ROI `01f1532267c4...`** (Phase 3, Session i).
- The KA index (Agent Bricks) — **live as tile `f000ded6-362a-476b-ab3f-1f6e1bfb6def`, endpoint `ka-f000ded6-endpoint`** indexed over `/Volumes/.../compass_bronze/raw/ka-corpus/` (Phase 4, Session k).
- The serving endpoint backing the supervisor agent (Agent Bricks MAS) — **TODO Phase 6**.

The bundle references these by name and asserts permissions on them. **As-built provisioning order**: workspace ✅ → silver+gold via DAB ✅ → metric views ✅ → Genie spaces ✅ → KA ✅ → Lakebase (Provisioned, after Autoscale migration) ✅ → app (Phase 7) ✅ → supervisor endpoint (Phase 6, deferred).

### 17.3 Secrets

- **Lakebase OAuth** — the Databricks App identity gets the OAuth scope to the Lakebase Provisioned instance via the app's `resources:` block (binds `instance_name: compass-lakebase-prov` with `CAN_CONNECT_AND_CREATE`). No static credential. The token lifecycle lives in `app/backend/lakebase_token.py`: `LakebaseTokenManager` caches and proactively rotates the ~1 hr token via `w.database.generate_database_credential(request_id=..., instance_names=[...])`, and `make_engine(...)` wires a SQLAlchemy `do_connect` event hook that injects a fresh token + `sslmode=require` on every new pool connection. `pool_pre_ping=True` recycles any connection whose token expired mid-pool.
- **Lakebase grants** are applied by `lakebase/grants.sql` (idempotent; `psql -v app_sp_id=<uuid> -f lakebase/grants.sql`) — creates `compass_app` + `compass_reader` container roles and grants the App SP into `compass_app`.
- ECB rate / external API keys (not used in v1) would live in a Databricks secret scope `compass-secrets`.

---

## 18. Non-Functional Design

| Concern | Target | How |
|---|---|---|
| Per-turn latency p50 | ≤ 4 seconds | Pre-warmed SQL warehouse; Lakebase synced tables; KA hybrid retrieval top-K capped at 6 |
| Per-turn latency p95 | ≤ 9 seconds | Same; tail dominated by LLM streaming |
| Cold-start (first turn) | ≤ 12 seconds | Click script pre-warms with `SELECT 1` against Lakebase + a no-op Genie call |
| Eval-job runtime | ≤ 5 minutes | 20 turns × ~10s/turn + overhead |
| Demo dataset land time | ≤ 8 minutes | Generator + build-gold + UC ingestion |
| Monthly cost (single tenant) | < $X (TBD) | Serverless warehouse auto-stop 10 min; Lakebase Provisioned CU_1 baseline |

---

## 19. Open Design Decisions

| # | Decision | Default | Open question |
|---|---|---|---|
| 1 | Genie space certification | certified before demo | yes |
| 2 | KA embedding model | default Databricks embedding endpoint | swap to bge-large for EMEA multilingual? |
| 3 | Supervisor base model | Claude Sonnet 4.6 | upgrade to Opus when needed for adversarial cases? |
| 4 | Lakebase region | same as workspace | cross-region for latency? (not for this pilot) |
| 5 | App framework | React + FastAPI (CDPP Coach pattern) | reuse existing repo or fresh? |
| 6 | RLS function placement | `silver.dealer` row filter | propagate to gold or rely on view inheritance? — TBD with security |
| 7 | Forfeiture probability model | heuristic v1.0 | replace with propensity model trained on FY24/FY25 claim arrival curves — Phase 10 |

---

## 20. Appendix

### 20.1 Status enums

- `coop_claim.status`: `Draft`, `Submitted`, `Under_Review`, `Approved`, `Rejected`, `Paid`, `Expired`
- `claim_review.status` (Lakebase): `Pending`, `Approved`, `Rejected`, `PaidStaged`
- `nudge_campaign.status`: `Draft`, `Queued`, `Sent`, `Cancelled`
- `nudge_recipient.email_status`: `Pending`, `Queued`, `Sent`, `Opened`, `Clicked`, `Bounced`, `Failed`
- `claim_review.rejection_code`: `MISSING_PREAPPROVAL`, `TIER_INELIGIBLE`, `OFF_BRAND`, `OUT_OF_REGION`, `DOC_INCOMPLETE`, `DOUBLE_DIP`, `OTHER`

### 20.2 KA doc-ID convention

`KA-<TOPIC>-<###>` — uppercase topic shorthand + 3-digit ordinal. Reserved range: 001–099 for FY26 policy; 100–199 for FY27; 900–999 for sandbox/demo-only docs. Used by the `policy_citation_present` scorer to detect citations.

### 20.3 Glossary

(See `demo-requirements.md §18`.)
