---
title: Co-op Eligibility Matrix (FY26)
doc_id: KA-ELIG-002
audience: internal,dealer
region: global
effective_date: 2026-03-01
expires: 2027-02-28
language: en
confidentiality: dealer-shareable
version: FY26.1
---

# Co-op Eligibility Matrix (FY26)

> *This is the authoritative answer to "Is activity X eligible?" and "What pre-approval applies?". Where a regional addendum overrides a row, the regional addendum governs for that region. Citations to this document should always reference both the section number and the row.*

## 1. Reading this matrix

Each row describes one activity type. Columns:

| Column | Meaning |
|--------|---------|
| Activity | Name as referenced in the dealer portal |
| Category | One of Digital, Event, Showroom, Content, Sponsorship |
| Co-fund % | Default Steelcase share. Dealer share = 100 - this value. |
| Pre-approval | Required (R), Required Above Threshold (RT), Not required (—) |
| Threshold | If RT, the USD-equivalent threshold |
| Tier eligibility | Which dealer tiers may claim |
| Notes |  |

## 2. The matrix

### 2.1 Digital

| # | Activity | Co-fund % | Pre-approval | Threshold | Tier eligibility |
|---|----------|-----------|--------------|-----------|------------------|
| 2.1.1 | Programmatic Display | 50% | RT | $5,000 | All |
| 2.1.2 | Paid Social | 50% | RT | $5,000 | All |
| 2.1.3 | Search / SEM | 50% | RT | $5,000 | All |
| 2.1.4 | Email Marketing | 50% | — | n/a | All |
| 2.1.5 | Website / Microsite | 50% | RT | $5,000 | Gold, Platinum |
| 2.1.6 | Content Syndication | 50% | RT | $5,000 | All |
| 2.1.7 | Account-Based Marketing (Enterprise) | 50% | R | $0 (always) | Platinum, Gold |

**Notes for §2.1:**
- Website / Microsite activities (2.1.5) are restricted to Gold and Platinum tiers. Silver and Authorized dealers may not claim against a website build. See `regional-addendum-amer.md §4` for the AMER exception covering co-branded landing pages under $2,500.
- ABM Enterprise (2.1.7) always requires pre-approval *and* an approved Target Account List on file with the CMM.

### 2.2 Event

| # | Activity | Co-fund % | Pre-approval | Threshold | Tier eligibility |
|---|----------|-----------|--------------|-----------|------------------|
| 2.2.1 | Local Dealer Event | 60% | RT | $5,000 | All |
| 2.2.2 | Architecture+Design Event | 60% | RT | $5,000 | All |
| 2.2.3 | NeoCon Regional | 50% | R | $0 (always) | All |
| 2.2.4 | Client Hospitality | 50% | RT | $5,000 | Gold, Platinum |
| 2.2.5 | Trade Show | 50% | R | $0 (always) | All |

**Notes for §2.2:**
- All Event activities require post-event documentation: attendee list, agenda, photos. See `claim-submission-playbook.md §4`.
- Client Hospitality (2.2.4) is restricted to Gold and Platinum tiers. Hospitality activities have stricter audit requirements; the entertainment vs marketing distinction is documented in `regional-addendum-amer.md §3` for AMER.

### 2.3 Showroom

| # | Activity | Co-fund % | Pre-approval | Threshold | Tier eligibility |
|---|----------|-----------|--------------|-----------|------------------|
| 2.3.1 | Showroom Refresh — Generic | 50% | R | $0 (always) | Gold, Platinum |
| 2.3.2 | Showroom Refresh — Hybrid Work Zone | 60% | R | $0 (always) | All |
| 2.3.3 | Showroom Refresh — Wellbeing Zone | 60% | R | $0 (always) | All |

**Notes for §2.3:**
- The Hybrid Work Zone (2.3.2) and Wellbeing Zone (2.3.3) carry a higher co-fund % because they reinforce strategic narratives; they are available to **all tiers including Authorized**.
- Net-Zero Showroom Refresh is funded out of a separate program (`PRG-FY26-NETZERO`) with its own application.

### 2.4 Content

| # | Activity | Co-fund % | Pre-approval | Threshold | Tier eligibility |
|---|----------|-----------|--------------|-----------|------------------|
| 2.4.1 | Sales Literature | 50% | — | n/a | All |
| 2.4.2 | Video / Photography | 50% | RT | $5,000 | All |
| 2.4.3 | Case Study | 50% | — | n/a | All |
| 2.4.4 | Whitepaper / Ebook | 50% | — | n/a | All |

### 2.5 Sponsorship

| # | Activity | Co-fund % | Pre-approval | Threshold | Tier eligibility |
|---|----------|-----------|--------------|-----------|------------------|
| 2.5.1 | IIDA Chapter | 50% | RT | $2,500 | All |
| 2.5.2 | AIA Chapter | 50% | RT | $2,500 | All |
| 2.5.3 | Community / Civic | 40% | RT | $2,500 | All |

**Notes for §2.5:**
- Community / Civic (2.5.3) carries a lower co-fund % because the marketing return is harder to attribute. Activities must demonstrate a Steelcase brand-visible component (e.g., signage, branded materials, event association).

## 3. Tier-specific eligibility — quick reference

### 3.1 Platinum dealers
All activities eligible. Pre-approval rules above apply.

### 3.2 Silver dealers (and Authorized, except where noted)
- **Eligible without pre-approval**: paid social up to $4,999/claim; sales literature; case studies; whitepapers/ebooks; email marketing; local dealer council events under $5K.
- **Eligible with pre-approval**: programmatic display, SEM, content syndication, video/photography, NeoCon Regional, trade shows, showroom Hybrid/Wellbeing zones, sponsorships (IIDA/AIA/community).
- **Ineligible regardless of pre-approval**: ABM Enterprise (Platinum/Gold only), Client Hospitality (Gold/Platinum only), Website/Microsite (Gold/Platinum only — except AMER exception, see §2.1 notes).

### 3.3 Authorized dealers
Same eligibility as Silver, with the additional exclusion of Showroom Refresh — Generic (Gold/Platinum only). Authorized dealers **may** participate in the Hybrid Work and Wellbeing zone refreshes.

## 4. Common rejection reasons (mapped to this matrix)

| Rejection code | Reason | Matrix section |
|----------------|--------|----------------|
| `MISSING_PREAPPROVAL` | Pre-approval required but not provided | §2 (any RT/R activity) |
| `TIER_INELIGIBLE` | Activity not available to dealer's tier | §3 |
| `OFF_BRAND` | Brand compliance score < 50 | `brand-compliance-spec.md` |
| `OUT_OF_REGION` | Activity executed outside dealer's region | (regional addenda) |
| `DOC_INCOMPLETE` | Required proof of execution missing | `claim-submission-playbook.md §4` |
| `DOUBLE_DIP` | Same activity claimed against multiple programs | this doc, §5 |

## 5. No double-dipping

A single activity (defined by execution date + venue/medium + creative) **may not** be claimed against two programs simultaneously. The dealer must elect which program to claim against on submission. If two claims for the same activity are filed against two different programs, the **earlier-submitted claim** is processed and the **later** claim is auto-rejected with code `DOUBLE_DIP`.
