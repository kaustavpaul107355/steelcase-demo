# Genie Space — Co-op Utilization & Risk

**Persona:** Maya Chen, Channel Marketing Manager (AMER East). Operational view —
where the money is going, what's at risk, what's stuck.

**Domain scope:** dollars, dealer balances, claim lifecycle, forfeiture, SLA.
Anything that answers "where is the money now?" or "what's blocking the money
from moving?".

**Out of scope for this space** (route to "Marketing Effectiveness & ROI" Genie
Space): activity-lift, attributed revenue, return on co-op dollar, monthly
performance trends, EMEA Programmatic Display narrative.

---

## Grounding preferences

- **Always prefer `compass_metric.*` metric views over `compass_gold.fact_*` tables**
  when they cover the same question. The metric views are the certified governed
  semantic.
- Metric views REQUIRE `MEASURE(...)` wrapping for measure columns; **never JOIN
  a metric view with another table**.
- Use `compass_gold.dim_*` views for joins / lookups.

## Data shape conventions

- `region IN ('AMER','EMEA','APAC')` — 3 values, no sub-region info.
- `sub_region IN ('East','West','Central','North','South')` — 5 values.
- `region_full IN ('AMER East','AMER West','AMER Central','EMEA North','EMEA South','EMEA East','APAC North','APAC South')` — 8 values, the concatenation.
- When the user says **"AMER East" / "EMEA North"** etc., **ALWAYS match `region_full` FIRST**. Do NOT split into `region + sub_region` unless the user explicitly asked.

## Fiscal-year convention

- `fiscal_year IN ('FY24','FY25','FY26')` — never `'2024'`/`'2026'`.
- Steelcase fiscal year runs **March 1 to end of February**. FY26 = Mar 2026 → Feb 2027.

## Dealer-ID conventions

- Hero cohort dealer IDs: `D-04711` through `D-04733` (AMER East).
- Other dealers: `D-01001` through `D-01820`.

## Status enums (for `metric.claim_lifecycle` and silver.coop_claim)

- `Draft`, `Submitted`, `Under_Review`, `Approved`, `Rejected`, `Paid`, `Expired`
- "Non-terminal" / "in-flight" = `Submitted`, `Under_Review`, `Approved`, `Paid`
- "Approved-or-better" = `Approved`, `Paid`

## Forfeiture vocabulary (critical for this space)

- `unused_usd` = allocated − committed; capped at 0.
- `forfeited_usd` > 0 **only** when `days_to_expiration < 0`; otherwise 0.
- `expected_forfeit_usd` is a **two-band heuristic** precomputed in gold:
  - **High-risk band** (`days_to_expiration < 180 AND paid/allocated < 0.6`) → full `unused_usd`.
  - **Low-risk band** → `unused × (1-utilization)² × 0.1` (light tail).
- "Forfeiture risk" questions almost always want `metric.forfeiture_risk` with
  `MEASURE(expected_forfeit_usd_total)`.

## Hero numbers (sanity-check during demo)

- **AMER East FY26 `expected_forfeit_usd` ≈ $1.62M across 23 dealers.**
- **Top 3 at-risk dealers**: Pivot Workplace Solutions, Halcyon Office Group, Northpoint Workspaces.

## Tone of generated answers

- One-paragraph executive summary (like a Slack message to a director).
- Always lead with the dollar amount and the time horizon.
- When listing dealers, default to **top 10 by unused balance descending**.
- Don't speculate on remediation — the agent's action tools handle that.
