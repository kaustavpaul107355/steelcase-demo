# COMPASS Demo — Click-by-Click Presenter Script

**Audience:** Steelcase VP Channel Mktg + ~6 stakeholders
**Length target:** 25 min demo + 10 min Q&A
**Persona:** Maya (Channel Marketing Manager, AMER East)
**Pre-demo checks (T-15 min):**

- [ ] Logged into demo workspace as `maya.demo@steelcase-demo.invalid`
- [ ] SQL warehouse `co-op-demo-wh` is **running** (not cold)
- [ ] Lakebase instance `coop-lakebase` is **ready**; pre-warm with `SELECT 1` from the App
- [ ] COMPASS app opened on a fresh browser tab; chat history cleared
- [ ] Backup video of Acts 2-4 loaded in a second tab (don't show unless needed)
- [ ] Genie space "Co-op Program Analytics" certified status visible in its tab
- [ ] MLflow Traces UI ready in a third tab, filtered to today
- [ ] Notification banner closed; do-not-disturb on

---

## Cold open (00:00 – 00:90)

**Show on screen:** Slide — title "Co-op Program Analytics Agent for Steelcase" with subtitle "From dashboards to decisions, in one conversation."

**Say:**
> "Before we open anything: a typical morning for a Steelcase channel marketing manager looks like this — dealer portal, SharePoint, Outlook, a Power BI dashboard that broke yesterday. Today I'll show you what that morning looks like when the data, the policy, and the action live in one conversation."

**Action:** Advance to a one-slide architecture diagram (logical 5.1 from the requirements doc).
**Say (15 sec on architecture):**
> "Three things to notice on the architecture, then we'll never look at it again. One: every number comes from a Unity Catalog metric view. Two: every policy answer comes from a Knowledge Assistant grounded on a real corpus, and it cites its source. Three: the orchestration is an Agent Bricks supervisor — it picks the right tool. Now let's go to the app."

**Action:** Click the COMPASS app tab.

---

## Act 1 — Open the app (00:90 – 02:00)

**Action:** Click the **COMPASS** browser tab.
- The app shows: left = empty chat with starter prompts; right = "Approval Queue" tab (5 pending), "Saved Views" tab (3), "My Region" header showing **AMER East**.

**Say:**
> "This is Maya. AMER East, 120 dealers, $4.5M allocation, KPI'd on utilization, on-brand compliance, and sell-through lift. The starter prompts on the left are the ones her predecessors actually asked. The approval queue on the right is wired to a Lakebase table — we'll come back to that."

**Pointer pause** — let them see the regional badge "AMER East — Tier filter: All".

---

## Act 2 — Turn 1: Forfeiture risk (02:00 – 03:30)

**Action:** Click the starter prompt **"What's my Q4 forfeiture risk?"** (or type it).

**Expected response in chat:**
- Text: *"AMER East is projected to forfeit ~$1.62M across 23 dealers by FY-end (2027-02-28). Top contributors: Pivot Workplace Solutions ($147K), Halcyon Office Group ($118K), Northpoint Workspaces ($96K)."*
- Embedded bar chart: top 10 at-risk dealers, value = unused balance.
- Below the chart: a small expandable **"Show metric & SQL"** chip.

**Action:** Click **"Show metric & SQL"**.
- Expands to show: metric view name `metric.forfeiture_risk`, the rendered SQL Genie used, the catalog/schema path, and a "Lineage" link.

**Say:**
> "This number is not a hallucination. It came from a metric view in Unity Catalog — same view Finance uses, same view Eliot will see Friday. The SQL is auditable, the lineage is auditable, and if anyone redefines the rule, everyone using it sees the new definition."

**Action:** Collapse the SQL panel.

---

## Act 3 — Turn 2: Drill into dealers (03:30 – 04:30)

**Action:** Type *"Show me those 23 dealers with their balance, expiration, and current YTD utilization."*

**Expected response:**
- A sortable table: `dealer_name`, `tier`, `unused_balance_usd`, `expiration_date`, `utilization_rate_ytd`.
- 23 rows. Sorted desc by `unused_balance_usd`.

**Say:**
> "Same metric view. Finer grain. The agent didn't write new SQL — it composed the same governed view with new filters."

**Action:** Sort by `expiration_date` ascending — the table re-sorts in place.

**Say:**
> "The top of the list is now the most urgent. Five dealers have balances expiring before Thanksgiving."

---

## Act 4 — Turn 3: The policy question (04:30 – 06:00)

**Action:** Type *"Pivot Workplace Solutions is Tier-Silver. What activity types can a Silver dealer claim against in Q4 without pre-approval?"*

**Expected response (from KA):**
- Bulleted list of eligible activities with **citations as superscript links**: `[1]`, `[2]`, `[3]`.
- A **"View citations"** chip below.

**Action:** Click `[1]` — a side-panel opens showing the exact excerpt from `eligibility-matrix.md §3.2`, highlighted.

**Say:**
> "Notice the citation. We built a custom MLflow scorer that fails any policy answer if a citation is missing. Channel marketing managers told us — and I quote — *'if I can't see where the answer came from, I won't trust it.'* So we made the agent unable to ship a policy answer without a source."

**Action:** Close the citation panel.

---

## Act 5 — Turn 4: The action (06:00 – 09:00)

**Action:** Type *"For those 23 dealers, generate a nudge campaign with the 'Q4 Fast-Track Digital' template, deadline December 12. Show me the draft before sending."*

**Expected response:**
- Text: *"Drafted campaign `nudge-2026-Q4-AE-001`: 23 recipients, template = Q4 Fast-Track Digital, deadline 2026-12-12. Status: DRAFT. Personalized previews for top 3 below. Tap 'Approve and queue' to schedule."*
- Below the text: an inline card with **3 personalized email previews** for Pivot, Halcyon, Northpoint, each showing the dealer's actual unused balance.
- A green button: **"Approve and queue"**.

**Say:**
> "Three things to call out. First — the campaign was written to Lakebase, our managed Postgres. The agent has an action tool that can stage work; it cannot send email by itself. Second — each preview is personalized because Lakebase joined the dealer master and the per-dealer balance. Third — Maya still approves. The human is in the loop."

**Action:** Click **"Approve and queue"**.

**Expected response:**
- Toast: *"Campaign queued. 23 recipients. Will send 2026-10-13 09:00 ET."*
- Right pane "Approval Queue" tab badge updates from `5` to `5` (unchanged) and "Nudges" tab shows `1 queued`.

**Say:**
> "In a real deployment, this is where we'd hand off to Marketo or HubSpot. For this demo it stays inside the app, but the integration pattern is the same."

---

## Act 6 — Turn 5: ROI defense (09:00 – 12:30)

**Action:** Type *"Of my paid claims YTD, which activity types delivered the best sell-through lift?"*

**Expected response:**
- Top-5 list with `revenue_per_coop_dollar`:
  1. Digital — Programmatic Display ($7.40 / $1)
  2. Local Dealer Event — Architecture+Design ($5.10 / $1)
  3. Showroom Refresh — Hybrid Work Zone ($4.20 / $1)
  4. Account-Based Marketing — Enterprise ($3.80 / $1)
  5. Trade Show — NeoCon Regional ($2.90 / $1)
- A **"Methodology"** link below the table.

**Action:** Click **"Methodology"** — opens a side panel rendering the metric view definition + lift-vs-control description.

**Say:**
> "This is the conversation Maya has been trying to have for three years. Notice: the methodology is *the metric view definition*. If anyone redefines lift, every consumer of this metric sees the new definition the next time they ask. That is what governance looks like when it isn't a slide."

**Action:** Close panel.

---

## Act 7 — Turn 6: Save view (12:30 – 13:30)

**Action:** Type *"Save this as a view called 'Q4 Defense — Top ROI Activities' so I can pull it up Friday."*

**Expected response:**
- Text: *"Saved. Pinned to your sidebar."*
- Right pane "Saved Views" tab now shows the new entry at the top.

**Action:** Click the saved view in the sidebar — the chat re-renders the same table.

**Say:**
> "Saved views also live in Lakebase. Maya brings these into the QBR on Friday and they replay exactly. No fresh query, no surprises."

---

## Act 8 — Turn 7: The cross-system flourish (13:30 – 17:00)

**Action:** Type *"Are any of those 23 at-risk dealers also flagged in the claim approval queue today?"*

**Expected response:**
- Text: *"Yes — 4 dealers have pending submitted claims (total requested: $87,240). See the queue."*
- Table with 4 claims and inline **"Approve" / "Reject"** buttons per row.

**Say:**
> "Watch what just happened. The at-risk cohort is from a gold metric view in UC. The pending approvals are from Lakebase, our OLTP store. The agent stitched them together — *that* is the analytics + transactions flywheel we keep talking about, in one query the user didn't have to plan."

**Action:** Click **"Approve"** on the first row.

**Expected response:**
- Toast: *"Claim `cl-2026-AE-009842` approved. Reviewer note logged."*
- The row dims; the queue count drops.

**Say:**
> "Approving here writes back to Lakebase, which is reverse-ETL'd into Unity Catalog so the next forfeiture-risk query picks up the change. No double-bookkeeping."

---

## Act 9 — The quality story (17:00 – 21:00)

**Action:** Switch to the **MLflow Traces** browser tab.

**Action:** Filter by `session_id = <Maya's current session>` (or just take the latest 10 traces).

**Show:**
- Each turn from Acts 2-8 is a parent trace.
- Expand turn 4 (the nudge campaign): see the supervisor span → tool span (`create_nudge_campaign`).
- Expand turn 3 (the policy turn): see the supervisor span → KA span → retrieval child spans.

**Say:**
> "Every turn is a trace. We can inspect the tool routing, the latency, the retrieval hits, the LLM call. This is the production-grade observability story for agents."

**Action:** Switch to the **MLflow Evaluation** sub-tab.

**Show:**
- The eval run dashboard: 20 graded turns (the v1 seed set; production traces add ~10/week graded by the team), scorers: `Correctness`, `RetrievalGroundedness`, `Guidelines`, `policy_citation_present`.
- Trendline showing the last 7 nightly runs.

**Say:**
> "This eval runs nightly over a sample of production traces, scored by built-in MLflow scorers plus one we wrote — `policy_citation_present` — which fails any KA-routed turn that does not cite a corpus document. If we change the corpus, retrain a model, or modify the system prompt, we know within a day whether we broke something."

**Action:** Return to COMPASS tab.

---

## Act 10 — Backup beat (only if time): the governance flourish (21:00 – 23:00)

**Action:** Open a private window; log in as `priya.demo@pivot-workplace.invalid` (a dealer user).

**Action:** Type *"What is AMER East's forfeiture risk?"*

**Expected response:** *"You are signed in as a dealer user. I can only answer questions about your own balance and claims. Would you like to see your current balance for Dealer #4711 Pivot Workplace Solutions?"*

**Say:**
> "Row-level security is enforced at Unity Catalog. The agent respects it because it runs as the user — not as a service principal. Same agent, two audiences."

**Action:** Type *"Yes — show my balance."*
- Returns Priya's dealer-scoped balance card.

---

## Act 11 — Close (23:00 – 25:00)

**Action:** Return to the architecture slide.

**Say:**
> "Six minutes of Maya's morning. Eight things just happened that previously took her four days. The platform paid for itself in this one persona, in one quarter. Eliot already has fourteen of these conversations queued up for EMEA. We're ready to talk timeline, scope, and what a 60-day pilot looks like."

**Q&A** — 10 minutes. Anticipated questions:
- "How accurate is the lift attribution?" → see `dealer_performance.yaml` methodology.
- "Can we plug in Marketo?" → action tool target swap.
- "What about French/German corpus?" → KA supports per-doc language; demo only shows English.
- "Cost?" → serverless warehouse + serving + Lakebase; sized roughly at $X/month for AMER East scale.
- "Where does the bronze data come from?" → For the demo, one source workbook with four sheets (`Allocations`, `ERP_Sales_Orders`, `Event_Registrations`, `Portal_Claims`) lands via the **native Databricks Excel reader** (DBR 17.1+) — no Maven JAR, no Python dependency. In a real Steelcase build the same bronze tables would arrive via **Lakeflow Connect** for Salesforce + SAP and **Auto Loader** for portal exports, allocation rosters, and event registrations (see `demo-design.md §5.A` for the production design and `§5.D` for the demo-time consolidation).

---

## Failure-recovery playbook

| If… | Then… |
|------|------|
| Genie returns a slow or wrong answer | Say "let me show you the SQL", click "Show SQL", explain the metric view, manually run the SQL in a SQL editor tab if needed. |
| KA returns no citation | Say "this is exactly the failure case our scorer catches — let me show you the eval dashboard." (Pivot to Act 9.) |
| Lakebase write fails | Say "the agent staged this; in production we retry — let me show you the synced table that proves the round-trip." |
| App crashes | Switch to backup video tab. Resume narrative; pivot to MLflow tab to keep momentum. |
| Wifi dies | Open the backup video on the laptop; narrate over it. |

---

## What to NOT click (live demo discipline)

- Do not click the metric view edit button — easy to deface a YAML mid-demo.
- Do not click "delete saved view" — Maya needs the view for Friday in the story.
- Do not log out — re-auth flow takes 30s and breaks the rhythm.
- Do not open the Genie space directly until Act 11 (if at all) — Genie's UI is a different story than the agent UI.
