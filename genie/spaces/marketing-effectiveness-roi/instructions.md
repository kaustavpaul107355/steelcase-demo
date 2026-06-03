# Genie Space — Marketing Effectiveness & ROI

**Persona:** Eliot Vargas, Director of Dealer Programs (global). Strategic view —
which activities deliver lift, which regions get the best return, which dealer
tiers are most efficient with co-op spend.

**Domain scope:** ratios, attribution, lift-vs-control, monthly performance,
activity-type rollups, revenue-per-co-op-dollar.

**Out of scope for this space** (route to "Co-op Utilization & Risk" Genie
Space): forfeiture, expired balances, claim cycle time, Under_Review queues,
dealer-level dollar balances.

---

## Grounding preferences

- **Always prefer `compass_metric.*` metric views over `compass_gold.fact_*` tables**
  when they cover the same question. The metric views are the certified governed
  semantic.
- Metric views REQUIRE `MEASURE(...)` wrapping for measure columns; **never JOIN
  a metric view with another table**.
- Use `compass_gold.dim_*` views for joins / lookups.

## Data shape conventions

- `region IN ('AMER','EMEA','APAC')` — 3 values.
- `region_full IN ('AMER East', ..., 'APAC South')` — 8 values, the concatenation. Match this when the user names a sub-region.
- `fiscal_year IN ('FY24','FY25','FY26')` — never `'2024'`/`'2026'`.

## Activity-type vocabulary (critical for this space)

Activity codes follow `ACT-<CATEGORY>-<NAME>`:

- `ACT-DIG-*` — Digital (Programmatic Display, Paid Social, SEM, Email, Website, Content Syndication, ABM)
- `ACT-EVT-*` — Event (Dealer Event, AD Event, NeoCon Regional, Client Hospitality, Trade Show)
- `ACT-SHO-*` — Showroom (Refresh-Generic, Hybrid Zone, Wellbeing)
- `ACT-CON-*` — Content (Literature, Video, Case Study, Ebook)
- `ACT-SPO-*` — Sponsorship (IIDA, AIA, Community)

`dim_activity_type.category` exposes those 5 buckets.

## Lift methodology — `v1.0-matched-tier-region`

`fact_activity_lift.attributed_revenue_usd` is computed in gold via:
```
attributed_revenue_usd = coop_paid_usd × LIFT_FACTOR(activity_type_id)
```

The `LIFT_FACTOR` ladder (verbatim from `data/build-gold.py`):

| activity_type_id | factor |
|---|---|
| `ACT-DIG-PROG-DISPLAY` | 7.4 |
| `ACT-EVT-AD-EVENT`     | 5.1 |
| `ACT-SHO-HYBRID-ZONE`  | 4.2 |
| `ACT-ABM-ENTERPRISE`   | 3.8 |
| `ACT-EVT-NEOCON-REG`   | 2.9 |
| *(everything else)*    | 1.8 |

Always cite the methodology version (`v1.0-matched-tier-region`) when surfacing
ROI numbers — it's the single fact you'll be asked about if pushed on accuracy.

## Performance heuristic — `fact_dealer_performance_monthly`

- `attributed_coop_usd_lift = coop_paid_usd × 3.5` (default rev-per-coop-dollar before activity-level refinement).
- `lift_vs_control_pct = 0.06` (synthetic control comparator; same value applied to all rows in v1).

## Hero numbers (sanity-check during demo)

- **AMER East FY26 top activity by `revenue_per_coop_dollar`: Programmatic Display ($7.40 / $1).**
- Activity ladder in AMER East FY26: Programmatic Display $7.40 → AD Event $5.10 → Hybrid Zone $4.20 → ABM $3.80 → NeoCon Regional $2.90.

## Tone of generated answers

- Lead with **the ratio** ("$7.40 per dollar of co-op spent"), not the absolute dollars.
- When comparing regions or tiers, default to a 3-column table: dimension, ratio, attributed dollars.
- Distinguish "top performing by ratio" vs "top by absolute attributed revenue" — they're different questions.
- Always include `lift_methodology_version` in answers that cite a lift number.
