---
title: Claim Submission Playbook (FY26)
doc_id: KA-PLAYBOOK-003
audience: internal,dealer
region: global
effective_date: 2026-03-01
expires: 2027-02-28
language: en
confidentiality: dealer-shareable
version: FY26.1
---

# Claim Submission Playbook (FY26)

> *Step-by-step process, required documents, deadlines, and escalation paths for filing a co-op claim. Use this with `eligibility-matrix.md` (what's eligible) and `brand-compliance-spec.md` (creative review).*

## 1. Process map

```
[Plan]  ->  [Pre-approval (if required)]  ->  [Execute]
   ->  [Upload proof]  ->  [Submit claim]
   ->  [Brand-compliance review]  ->  [CMM review]
   ->  [Decision]  ->  [Finance pays]  ->  [Closed]
```

Median elapsed time, plan-to-payment: ~38 days for activities requiring pre-approval; ~15 days otherwise.

## 2. Before you start: the four mandatory inputs

For every claim you must have:

1. **Activity definition** — name, dates, medium/venue, target audience.
2. **Budget** — your full activity budget; Steelcase co-funds only the eligible portion.
3. **Creative or run-of-show** — the exact creative or event plan that will be reviewed.
4. **Allocation reference** — which program's allocation pool you intend to draw from. Default is the main co-op program; specialty programs (Net-Zero, WorkLife Lab, EMEA Digital, APAC Launch) require explicit choice.

## 3. Pre-approval (if required)

See `eligibility-matrix.md §2` for when this is required. If required:

1. In the dealer portal, **Claims > New Pre-Approval Request**.
2. Attach the four mandatory inputs from §2.
3. The CMM reviews within **5 business days**. Outcomes: Approved, Approved with conditions, Rejected with reason.
4. If Approved, your `preapproval_id` is valid for **90 days**. You must reference it on the final claim.
5. **Common gotcha**: a pre-approval is **not** a payment. The activity must still be executed and a claim filed.

## 4. Proof of execution — required documents

These must be uploaded to the claim before submission. Missing documents trigger automatic rejection with reason `DOC_INCOMPLETE`.

| Activity category | Required proof documents |
|-------------------|--------------------------|
| Digital — Programmatic, Paid Social, SEM | Final creative file (PNG/JPG/MP4); platform invoice; placement screenshot; date range of run |
| Digital — Email | Final email creative (HTML or screenshot); audience size; send date(s); platform invoice |
| Digital — Website | Live URL; screenshots of landing page; analytics screenshot for first 14 days post-launch |
| Digital — Content Syndication | Final asset; partner publisher invoice; placement screenshot |
| Digital — ABM Enterprise | Target Account List on file; campaign brief; vendor invoice(s); first-touch performance report |
| Event — Local / A+D / Hospitality | Invite; agenda; attendee list (≥10 attendees minimum); 5 in-event photos; vendor invoice |
| Event — NeoCon Regional / Trade Show | Booth contract; booth photos; lead-capture export; vendor invoices |
| Showroom — Refresh | Before / after photos; design plan; contractor invoice(s); brand-zone signage photo |
| Content — Literature | Final printed sample (PDF acceptable); print vendor invoice |
| Content — Video / Photography | Final asset; rights confirmation; vendor invoice |
| Content — Case Study / Ebook | Final asset; publishing date; promotion plan |
| Sponsorship | Sponsorship agreement; benefits list; in-context photo of Steelcase brand visibility |

**File format & size constraints:**
- Documents: PDF, DOCX up to 25 MB.
- Images: PNG, JPG up to 20 MB each (max 20 images).
- Video: MP4 or MOV up to 500 MB; link to YouTube/Vimeo also accepted.

## 5. Submitting the claim

In the dealer portal: **Claims > New Claim** (or **Convert pre-approval to claim**).

Fields:
- Activity type (must match the pre-approval, if any)
- Program (default: main co-op for your fiscal year)
- Execution dates
- Requested amount (USD; portal converts from local currency at posted spot rate)
- Pre-approval ID (if applicable)
- Upload all required proof documents (§4)
- Brand-compliance attestation (you confirm the creative meets `brand-compliance-spec.md`)
- Signature (dealer ops lead's portal account is sufficient)

## 6. Review timeline

| Stage | Owner | Target SLA | Status code |
|-------|-------|-----------|-------------|
| Brand-compliance review | Creative Review Pod | 3 business days | `Under_Review` |
| CMM review | Channel Marketing Manager | 5 business days | `Under_Review` |
| Decision logged | CMM | within 24h of review | `Approved` / `Rejected` |
| Finance disbursement | Finance Controller (Channel) | 10 business days | `Paid` |
| Total | | ~18 business days target | |

Cycle times are tracked in `claim_lifecycle` metric view.

## 7. Decisions

### 7.1 Approved
- The `approved_amount_usd` may be less than `requested_amount_usd` if part of the activity was ineligible. The CMM must cite the matrix section justifying any reduction.
- The reviewer note is visible to the dealer.
- The claim enters the Finance queue.

### 7.2 Rejected
- The CMM provides a rejection reason from this list: `MISSING_PREAPPROVAL`, `TIER_INELIGIBLE`, `OFF_BRAND`, `OUT_OF_REGION`, `DOC_INCOMPLETE`, `DOUBLE_DIP`, `OTHER`.
- The dealer has **15 business days** to remedy and resubmit. Resubmission after 15 days is treated as a fresh submission and may miss the FY-end deadline.

### 7.3 Appeals
A dealer may appeal a rejection or a reduced approval to the RMD. The RMD has **10 business days** to respond. Appeals may be escalated to the DPC, which meets quarterly.

## 8. Payment

Steelcase pays via the dealer's on-file ACH account (AMER) or bank transfer (EMEA, APAC). Currency conversion occurs at the spot rate on the **decision date**. Payment notification is emailed to the dealer's billing contact within 24h of disbursement.

## 9. After payment: closeout

The claim moves to `Paid` status. The dealer is not required to take further action. If the activity continues beyond the claim (e.g., a paid-social campaign with a longer run), a **supplemental claim** may be filed against the remaining allocation, treated as a new claim.

## 10. Escalation

- **Day-to-day questions** — CMM (your assigned regional contact).
- **Disputes / appeals** — RMD.
- **Policy interpretation** — Channel Marketing Office at `cmo@steelcase-demo.invalid`.
- **Suspected fraud** — Internal Audit at `audit-channel@steelcase-demo.invalid`.

## 11. Common errors and how to avoid them

| Error | Avoid by… |
|-------|-----------|
| Submitting before pre-approval is issued | Always check pre-approval status in portal before executing |
| Uploading low-resolution proof photos | Use phone in landscape, ≥ 1080p |
| Mismatched activity dates between proof and claim | Use the actual execution dates, not the planning window |
| Mixing two activities in one claim | File one claim per discrete activity |
| Currency mismatches | Let the portal convert; never hand-edit USD |
