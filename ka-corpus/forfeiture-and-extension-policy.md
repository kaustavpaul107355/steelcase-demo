---
title: Forfeiture & Extension Policy (FY26)
doc_id: KA-FORFEIT-007
audience: internal,dealer
region: global
effective_date: 2026-03-01
expires: 2027-02-28
language: en
confidentiality: dealer-shareable
version: FY26.1
---

# Forfeiture & Extension Policy (FY26)

> *Co-op allocations are use-it-or-lose-it. This document defines exactly when funds expire, what (narrowly) qualifies for an extension, and how the extension process works.*

## 1. Standard forfeiture rule

Unused co-op allocation funds **forfeit at midnight (Eastern Time) on the last day of the fiscal year**, i.e., 23:59:59 ET on **February 28, 2027** for FY26.

"Unused" means: not committed via a claim in `Submitted`, `Under_Review`, `Approved`, or `Paid` status. Claims in `Draft` at the cutoff do **not** count as committed and their underlying funds forfeit.

## 2. Operational deadlines that protect against forfeiture

To avoid forfeiture, dealers must hit these earlier deadlines:

| Deadline | What | Why |
|----------|------|-----|
| 2027-01-31 | Last day to submit new claims | Provides 28 days for review and payment |
| 2027-02-14 | Last day to upload proof for in-flight claims | Allows brand-compliance and CMM review |
| 2027-02-21 | Last day for CMM decision | Allows finance disbursement |
| 2027-02-28 | Last day for finance disbursement | FY-end |

A claim **submitted on 2027-01-31** is **safe**: the system protects the underlying funds for the full review cycle even if disbursement slips past Feb 28 (in which case payment occurs in FY27 but the FY26 accrual is preserved).

## 3. What forfeits and what doesn't

| Status at FY-end cutoff | Outcome |
|-------------------------|---------|
| `Draft` | Funds forfeit. Claim becomes uneditable on March 1. |
| `Submitted` | Funds protected. Claim continues through review in FY27. |
| `Under_Review` | Funds protected. |
| `Approved` (awaiting payment) | Funds protected. Payment moves to FY27 disbursement. |
| `Paid` | Funds disbursed. No further action. |
| `Rejected` | Funds released back to the pool, then forfeit if not re-committed. |
| `Expired` | Forfeited (this status exists for system bookkeeping). |

## 4. Extensions — narrow grounds

An **extension** lets a dealer carry **specific unused funds** into the first 60 days of the next fiscal year. Extensions are **rare** and not a substitute for planning. The three permitted grounds:

### 4.1 Steelcase delay

If a Steelcase-side delay (slow pre-approval, brand-review backlog, finance issue) prevents a dealer from executing on time, the affected funds may be extended on request. The CMM documents the delay in the claim history. **Auto-approved**.

### 4.2 Force majeure

Natural disasters, government action, or other force majeure events affecting the dealer's market. Requires:
- A short narrative from the dealer.
- CMM and RMD co-approval.
- Cap: 30% of the dealer's annual allocation.

### 4.3 Strategic exception (Net-Zero, WorkLife Lab)

Funds tied to the Net-Zero Showroom Refresh program or the WorkLife Marketing Lab may extend on RMD approval, recognizing the longer planning cycle. Cap: full unused balance in those programs.

## 5. Extension process

1. Dealer submits **Extension Request** in the portal: amount, reason (§4 ground), supporting documentation, planned execution window in the new FY.
2. CMM reviews within **3 business days**.
3. For §4.2 and §4.3, RMD co-approves within **5 business days**.
4. If approved, the funds are tagged `extended` with a new expiration date of **April 30** of the next FY.
5. The dealer must execute and submit a claim by April 30; any unused extended funds **then** forfeit (no further extension).

## 6. What is **not** a valid extension ground

- "The dealer was busy" or "we ran out of ideas".
- "The dealer is going to spend it next year on a planned activity" (use FY27 allocation instead).
- Vendor delays that the dealer could have escalated earlier.
- Personnel changes at the dealer.

The CMO maintains a list of repeat-extension-requesters and flags them to the DPC for follow-up.

## 7. Forfeiture reporting

Forfeited dollars are reported in the `coop_program_metrics` view as `forfeited_usd`. Reports surface:
- Forfeiture by region, sub-region, tier, program.
- Year-over-year forfeiture trend.
- Top-N most-forfeiting dealers (for coaching, not punishment).

## 8. Anti-gaming

Two patterns are watched:
- **Late-cycle dumping**: a dealer submitting an unusually high volume of claims in the last week of January. Threshold: > 30% of annual claim count submitted in the final week triggers an audit flag.
- **Round-trip extension**: requesting a §4.2 extension and then never executing. Repeat offenders lose access to the §4.2 ground.

## 9. Defensive recommendation for dealers

The single best protection against forfeiture is to **commit early**:
- Plan 60% of annual spend before mid-year recalibration (September).
- File claims monthly, not quarterly.
- Pre-approve trade shows and showroom refreshes 90+ days in advance.

CMMs are scored in part on the **forfeiture rate** of their dealer book, so the incentive is aligned.
