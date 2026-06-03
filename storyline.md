# COMPASS Demo — Storyline & Narrative

This is the **narrative** version of the demo — what we tell the audience, in plot order. For literal click steps see `click-script.md`.

---

## Cast

- **Maya** — Channel Marketing Manager, AMER East. Primary persona we demo "as".
- **Eliot** — Director of Dealer Programs, Global. Appears as the stakeholder Maya owes a report to.
- **Priya** — Dealer Marketing Ops Lead at Dealer #4711, "Pivot Workplace Solutions". Off-stage but referenced.
- **COMPASS** — the Co-op Program Analytics Agent (the app).

## Setting

It is **Tuesday, October 13, 2026, 8:47 a.m. ET**. Steelcase's fiscal year ends **end of February 2027**. Maya's quarterly business review with Eliot is **Friday**. Q4 dealer co-op balances are starting to look ugly. Last year Maya's region forfeited **$2.1M** of unused funds; Eliot has asked her to do better this year.

---

## Act 1 — The problem (90 seconds)

Maya's old-world morning:
1. Open the dealer portal (slow). Export this week's claim queue to Excel.
2. Open SharePoint. Hunt for the 2026 eligibility matrix PDF (last updated Feb).
3. Open Outlook. Three emails from dealers asking "what's my balance?".
4. Open Power BI. The forfeiture dashboard is broken because someone renamed a column in the source view.

She has 90 minutes before her first 1:1. Friday is coming.

**Presenter line:** *"This is the situation every channel marketing manager at every manufacturer is in. Dashboards don't answer her question. Policy lives in a PDF. The numbers and the rules are in different worlds. So today she's going to do something different."*

## Act 2 — The hero moment, part 1: ask the metric (4 minutes)

Maya opens **COMPASS**. The app loads — chat pane on the left, approval queue and saved views on the right.

**Turn 1.**
Maya: *"What's my Q4 forfeiture risk for AMER East?"*

COMPASS (Supervisor → Genie):
> Based on `forfeiture_risk` as of 2026-10-13, AMER East is projected to forfeit **$1.62M** across **23 dealers** by FY-end. Top three contributors: Pivot Workplace Solutions ($147K), Halcyon Office Group ($118K), Northpoint Workspaces ($96K). [Chart: bar of top 10 at-risk dealers.]

**Presenter line:** *"Notice three things. One — that number came from a Unity Catalog metric view, not from a query someone wrote on the fly. Two — the agent showed its work; you can see the SQL and the data lineage. Three — this took 4 seconds. Maya's BAU answer to this is a 4-day analyst ticket."*

**Turn 2.**
Maya: *"Show me those 23 dealers with their balance, expiration, and current YTD utilization."*

COMPASS returns a sortable table from `coop_program_metrics`.

**Presenter line:** *"Same metric view, finer grain. No new SQL. Governance preserved."*

## Act 3 — The hero moment, part 2: ask the rule (2 minutes)

**Turn 3.**
Maya: *"Pivot Workplace Solutions is Tier-Silver. What activity types can a Silver dealer claim against in Q4 without pre-approval?"*

COMPASS (Supervisor → KA "Co-op Program Handbook"):
> Silver-tier dealers may claim **without pre-approval** for: digital paid social up to $4,999 per claim, sales-literature reprints, local dealer council events under $5K. Pre-approval is required for: trade shows, programmatic display above $5K, showroom refresh, sponsorships. [Citation: `eligibility-matrix.md §3.2`, `coop-program-handbook.md §6.1`].

**Presenter line:** *"This came from the Knowledge Assistant, indexed over the program handbook and eligibility matrix. The citation is non-negotiable — we built a custom MLflow scorer that fails any policy answer without one."*

## Act 4 — The hero moment, part 3: take an action (3 minutes)

**Turn 4.**
Maya: *"For those 23 dealers, generate a nudge campaign with the 'Q4 Fast-Track Digital' template. Deadline December 12. Show me the draft before sending."*

COMPASS (Supervisor → action tool `create_nudge_campaign`):
> Drafted campaign `nudge-2026-Q4-AE-001`: 23 recipients, template = "Q4 Fast-Track Digital", deadline 2026-12-12. **Status: DRAFT**. Personalized previews below for the top 3 recipients. *Tap "Approve and queue" to schedule.*

The right pane shows the drafted campaign with 3 personalized previews.

**Presenter line:** *"This is the third leg of the stool. Genie did the metric. KA did the rule. Now an action tool writes the campaign to Lakebase. Notice what didn't happen — no emails went out. The agent is constrained to draft + queue. A human still approves."*

Maya clicks **Approve and queue**. The right pane updates: status = `QUEUED`.

## Act 5 — The proof-it-works moment (4 minutes)

Maya now wants to defend her budget at Friday's review.

**Turn 5.**
Maya: *"Of my paid claims YTD, which activity types delivered the best sell-through lift?"*

COMPASS (Genie over `dealer_performance` metric view):
> Top 5 by `revenue_per_coop_dollar` (paid claims YTD, AMER East):
> 1. Digital — Programmatic Display ($7.40 / $1)
> 2. Local Dealer Event — Architecture+Design ($5.10 / $1)
> 3. Showroom Refresh — Hybrid Work Zone ($4.20 / $1)
> 4. Account-Based Marketing — Enterprise ($3.80 / $1)
> 5. Trade Show — NeoCon Regional ($2.90 / $1)
>
> Lift methodology: matched-pair lift-vs-control on dealers receiving co-op support vs matched non-supported dealers in the same tier and region. [View methodology.]

**Presenter line:** *"This is the conversation Maya has been trying to have for three years. The methodology link goes to the metric view definition — auditable, reproducible, the same answer every time."*

**Turn 6.**
Maya: *"Save this as a view called 'Q4 Defense — Top ROI Activities' so I can pull it up Friday."*

COMPASS (action tool `save_view`):
> Saved view `Q4 Defense — Top ROI Activities`. Pinned to your sidebar.

## Act 6 — The "and one more thing" moment (2 minutes)

**Turn 7.**
Maya: *"Are any of those 23 at-risk dealers also flagged in the claim approval queue today?"*

COMPASS cross-references Lakebase `claim_review` with the at-risk cohort and returns 4 dealers with pending submitted claims. Maya inline-approves two of them right from the chat (`advance_claim` tool).

**Presenter line:** *"And this is the OLTP/analytics flywheel. The at-risk cohort came from the gold metric view. The pending approvals came from Lakebase. The agent stitched them together. Maya just unblocked $87K of in-flight commitments without leaving the app."*

## Act 7 — The wrap (2 minutes)

Maya closes the chat at 8:53 a.m. Six minutes elapsed.

The presenter zooms out:
- **One platform** held the data (UC), the policy corpus (Volumes), the agent (MAS), the OLTP state (Lakebase), and the app (Databricks Apps).
- **Two metric views** drove every number she saw — same definitions for finance, marketing, and the CFO.
- **Three components** — Genie, KA, action tools — orchestrated by one supervisor agent.
- **Five evals** ran nightly to keep the agent honest.

**Presenter close:** *"At 18% forfeiture, Maya's region was leaving $2M on the table every year. If COMPASS gets that to single digits — and the early data says it does — that's pure margin uplift, no incremental marketing budget. Eliot already has 14 channel managers running this. He wants you to roll it to Europe by end of Q1."*

---

## Backup beats (if time)

- **Eliot's executive view**: same agent, regional row-filter off, drill into "Tier-3 EMEA digital ad spend → sell-through" question. Demonstrates row-level security and the same metric definitions reused.
- **Dealer view (Priya)**: switch user; agent now refuses to answer Maya's questions ("you are not authorized") and instead surfaces Priya-scoped balance + claim status. Demonstrates governance and audience-scoped KA.
- **Quality story**: open MLflow Traces UI, show the supervisor's tool-routing decisions, then show the eval dashboard with the custom `policy_citation_present` scorer.

---

## Why this storyline works

1. **One persona, one morning, one outcome.** Audiences remember Maya. They forget feature lists.
2. **Money in the headline.** $1.6M forfeiture risk is a CFO-grade number, not a vanity metric.
3. **Three modalities in one flow.** Quantitative (Genie) → Qualitative (KA) → Action (tool). Each modality is a Databricks capability we want to land.
4. **Governance is on-camera, not behind the curtain.** Metric views are explicitly named. Citations are visible. Row-level security is demonstrable.
5. **The "boring" parts are also on-camera.** Approval queue. Saved views. These say: "this is a working application, not a demo prototype."
