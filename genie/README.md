# Genie Spaces — Source of Truth

This directory is the **Git-tracked source** for the COMPASS demo's Genie Spaces.
The live spaces in `fe-vm-classic-stable-1zia5t-kp` are deployed *from* these
files, not the other way around. Click-ops in the UI is OK for exploration but
should be reflected back into these files within the same session.

## Spaces

| Domain | Local dir | Live space |
|---|---|---|
| Co-op Utilization & Risk | `spaces/utilization-and-risk/` | `01f152f8ed8a1682af57700b37fb11bb` (renamed from "Co-op Program Analytics") |
| Marketing Effectiveness & ROI | `spaces/marketing-effectiveness-roi/` | TBD on first create |

## Per-space layout

| File | Purpose |
|---|---|
| `instructions.md` | Long-form context / system prompt. Loaded as the space `description`. Defines persona, grounding preferences, vocabulary, hero numbers, tone. |
| `tables.yaml` | Curated FQN list of tables exposed to the space (metric views + dim views). Includes `warehouse_id`. |
| `sample-questions.yaml` | Starter chips, certified questions, exploration questions. |
| `sql-examples.sql` | Certified SQL snippets — the "right answers" Genie uses as in-context exemplars. |

## Backups

`exports/` holds JSON dumps from `databricks api get /api/2.0/data-rooms/{id}`
before any rename / re-scope. Use these to rebuild a space verbatim if a deploy
goes sideways.

## Why two spaces?

The original "Co-op Program Analytics" space spanned both **operations**
(forfeiture, claim cycle time, dealer balances) and **strategy** (activity
lift, attribution, monthly performance). Splitting gives:

- **Tighter instructions** per space — better Genie translation accuracy.
- **Distinct sample-question chips** — Maya sees risk prompts, Eliot sees ROI prompts.
- **Cleaner supervisor agent routing** (Phase 6) — risk questions go to A, ROI questions go to B.

The two spaces overlap on dim tables (`dim_dealer`, `dim_region`, `dim_fiscal_calendar`)
but diverge on:
- Metric views: A uses `forfeiture_risk` / `claim_lifecycle` / `coop_program_metrics`;
  B uses `activity_lift` / `dealer_performance`.
- Vocabulary: A leads with dollars + urgency; B leads with ratios + methodology version.
- Hero numbers: A anchors on $1.62M / 23 dealers; B anchors on $7.40/$1 / Programmatic Display.

## Deploying changes

### Update an existing space (replace contents)
```bash
# Via direct REST API (CLI auth must be on the right workspace profile)
PROFILE=fe-vm-classic-stable-1zia5t-kp
SID=01f152f8ed8a1682af57700b37fb11bb
# (See deploy.sh in this directory for the actual call.)
```

### Create a new space
```bash
# Build a POST body with title/description/table_identifiers/warehouse_id from the local files.
# (See deploy.sh in this directory.)
```

### Backup before a destructive change
```bash
SID=<space_id>
mkdir -p genie/exports
databricks api get "/api/2.0/data-rooms/$SID" --profile fe-vm-classic-stable-1zia5t-kp \
  > genie/exports/$(basename $(grep -l "$SID" genie/spaces/*/)).$(date +%Y-%m-%d).json
```
