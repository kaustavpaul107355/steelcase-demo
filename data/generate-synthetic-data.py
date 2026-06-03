"""
COMPASS Demo — Synthetic Data Generator.

Generates plausible Steelcase Co-op program data for the demo:
  - 820 dealers across AMER/EMEA/APAC
  - 10 programs (6 active, 4 retired)
  - 22 activity types across 5 categories
  - ~6,500 allocations
  - ~28,000 claims with realistic state distribution
  - ~480,000 sell-through order lines
  - ~3,200 marketing events

Output: Parquet files under ./seed/ matching the silver schema, plus a single
multi-sheet Excel workbook `seed/compass-source.xlsx` that the Phase 1.5
bronze pipeline hydrates the four `bronze.*` raw tables from (Allocations,
ERP_Sales_Orders, Event_Registrations, Portal_Claims).

Planted signals:
  - "Forfeiture hotspot": 23 AMER East dealers with > $40K unused balance
    and < 60 days to expiration as of 2026-10-13.
  - "ROI activity": Digital — Programmatic Display in EMEA shows a clean
    lift signal vs control.

Usage:
  python generate-synthetic-data.py --out ./seed --as-of 2026-10-13

Dependencies: polars, mimesis (or faker), numpy, pandas, xlsxwriter.
  pip install polars mimesis numpy pandas xlsxwriter
"""

from __future__ import annotations

import argparse
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from mimesis import Generic, Finance
from mimesis.locales import Locale

SEED = 20260518
random.seed(SEED)
np.random.seed(SEED)
generic = Generic(locale=Locale.EN, seed=SEED)
finance = Finance(seed=SEED)

# ---------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------
REGIONS = [
    ("RGN-AMER-EAST",   "AMER", "East",     "USD", "US,CA"),
    ("RGN-AMER-WEST",   "AMER", "West",     "USD", "US,CA"),
    ("RGN-AMER-CENTRAL","AMER", "Central",  "USD", "US,CA,MX"),
    ("RGN-EMEA-NORTH",  "EMEA", "North",    "EUR", "GB,IE,NL,DE,DK,SE,NO,FI"),
    ("RGN-EMEA-SOUTH",  "EMEA", "South",    "EUR", "FR,ES,IT,PT,GR"),
    ("RGN-EMEA-EAST",   "EMEA", "East",     "EUR", "PL,CZ,HU,RO"),
    ("RGN-APAC-NORTH",  "APAC", "North",    "USD", "JP,KR,CN,TW"),
    ("RGN-APAC-SOUTH",  "APAC", "South",    "USD", "AU,NZ,SG,IN,TH"),
]

TIERS = ["Platinum", "Gold", "Silver", "Authorized"]
TIER_WEIGHTS = [0.05, 0.20, 0.40, 0.35]
TIER_BASE_ALLOCATION_USD = {
    "Platinum":   200_000,
    "Gold":        80_000,
    "Silver":      25_000,
    "Authorized":   8_000,
}

ACTIVITY_TYPES = [
    # (id, category, name, cofund_pct, requires_preapproval, threshold)
    ("ACT-DIG-PROG-DISPLAY",  "Digital",     "Programmatic Display",         50, True,  5000),
    ("ACT-DIG-PAID-SOCIAL",   "Digital",     "Paid Social",                  50, True,  5000),
    ("ACT-DIG-SEM",           "Digital",     "Search / SEM",                 50, True,  5000),
    ("ACT-DIG-EMAIL",         "Digital",     "Email Marketing",              50, False, None),
    ("ACT-DIG-WEBSITE",       "Digital",     "Website / Microsite",          50, True,  5000),
    ("ACT-EVT-DEALER-EVENT",  "Event",       "Local Dealer Event",           60, True,  5000),
    ("ACT-EVT-AD-EVENT",      "Event",       "Architecture+Design Event",    60, True,  5000),
    ("ACT-EVT-NEOCON-REG",    "Event",       "NeoCon Regional",              50, True,    0),
    ("ACT-EVT-CLIENT-EVT",    "Event",       "Client Hospitality",           50, True,  5000),
    ("ACT-EVT-TRADESHOW",     "Event",       "Trade Show",                   50, True,    0),
    ("ACT-SHO-REFRESH",       "Showroom",    "Showroom Refresh — Generic",   50, True,    0),
    ("ACT-SHO-HYBRID-ZONE",   "Showroom",    "Showroom Refresh — Hybrid",    60, True,    0),
    ("ACT-SHO-WELLBEING",     "Showroom",    "Showroom Refresh — Wellbeing", 60, True,    0),
    ("ACT-CON-LITERATURE",    "Content",     "Sales Literature",             50, False, None),
    ("ACT-CON-VIDEO",         "Content",     "Video / Photography",          50, True,  5000),
    ("ACT-CON-CASE-STUDY",    "Content",     "Case Study",                   50, False, None),
    ("ACT-CON-EBOOK",         "Content",     "Whitepaper / Ebook",           50, False, None),
    ("ACT-SPO-IIDA",          "Sponsorship", "IIDA Chapter",                 50, True,  2500),
    ("ACT-SPO-AIA",           "Sponsorship", "AIA Chapter",                  50, True,  2500),
    ("ACT-SPO-COMMUNITY",     "Sponsorship", "Community / Civic",            40, True,  2500),
    ("ACT-ABM-ENTERPRISE",    "Digital",     "Account-Based Marketing",      50, True, 10000),
    ("ACT-DIG-CONTENT-SYND",  "Digital",     "Content Syndication",          50, True,  5000),
]

PROGRAMS = [
    # (id, name, fy, method, default_cofund_pct, start, end)
    ("PRG-FY24-COOP-MAIN",  "Steelcase 2024 Co-op",            "FY24", "tier_based",   50, date(2023, 3, 1), date(2024, 2, 29)),
    ("PRG-FY25-COOP-MAIN",  "Steelcase 2025 Co-op",            "FY25", "tier_based",   50, date(2024, 3, 1), date(2025, 2, 28)),
    ("PRG-FY26-COOP-MAIN",  "Steelcase 2026 Co-op",            "FY26", "tier_based",   50, date(2026, 3, 1), date(2027, 2, 28)),
    ("PRG-FY26-WORKLIFE",   "WorkLife Marketing Lab",          "FY26", "performance",  60, date(2026, 3, 1), date(2027, 2, 28)),
    ("PRG-FY26-NETZERO",    "Net-Zero Showroom Refresh",       "FY26", "negotiated",   70, date(2026, 3, 1), date(2027, 2, 28)),
    ("PRG-FY26-DEALER-DEV", "Dealer Development Fund",         "FY26", "negotiated",   50, date(2026, 3, 1), date(2027, 2, 28)),
    ("PRG-FY25-WORKLIFE",   "WorkLife Marketing Lab (FY25)",   "FY25", "performance",  60, date(2024, 3, 1), date(2025, 2, 28)),
    ("PRG-FY24-WORKLIFE",   "WorkLife Marketing Lab (FY24)",   "FY24", "performance",  60, date(2023, 3, 1), date(2024, 2, 29)),
    ("PRG-FY26-EMEA-DIGI",  "EMEA Digital Accelerator",        "FY26", "performance",  50, date(2026, 3, 1), date(2027, 2, 28)),
    ("PRG-FY26-APAC-LAUNCH","APAC Brand Launch Fund",          "FY26", "negotiated",   60, date(2026, 3, 1), date(2027, 2, 28)),
]

CLAIM_STATUS_DIST = {
    "Draft":         0.05,
    "Submitted":     0.08,
    "Under_Review":  0.12,
    "Approved":      0.25,
    "Rejected":      0.08,
    "Paid":          0.38,
    "Expired":       0.04,
}

PRODUCT_FAMILIES = ["Seating", "Desks", "Storage", "Architecture", "Accessories"]

AS_OF_DEFAULT = date(2026, 10, 13)

# ---------------------------------------------------------------------
# PINNED HERO DEALERS  (drive the click-script's "$1.62M" hero moment)
# ---------------------------------------------------------------------
# 23 AMER East dealers with deterministic unused FY26 balances.
# Top 3 names match storyline/click-script verbatim.
# Sum of target_unused_usd = $1,619,400  =>  "$1.62M" headline.
HERO_REGION_ID = "RGN-AMER-EAST"
HERO_PROGRAM_ID = "PRG-FY26-COOP-MAIN"

HERO_DEALERS = [
    # (dealer_id, dealer_name, tier, country, target_unused_usd)
    ("D-04711", "Pivot Workplace Solutions",   "Silver", "US", 147_200.00),
    ("D-04712", "Halcyon Office Group",        "Gold",   "US", 118_400.00),
    ("D-04713", "Northpoint Workspaces",       "Silver", "US",  96_300.00),
    ("D-04714", "Beacon Contract Interiors",   "Gold",   "US",  92_800.00),
    ("D-04715", "Riverline Workspaces",        "Silver", "US",  86_400.00),
    ("D-04716", "Atlas Office Solutions",      "Silver", "US",  82_700.00),
    ("D-04717", "Cornerstone Workplace Co.",   "Gold",   "US",  78_900.00),
    ("D-04718", "Vantage Furniture Group",     "Silver", "US",  75_500.00),
    ("D-04719", "Skyline Office Partners",     "Silver", "CA",  72_800.00),
    ("D-04720", "Cascade Workspaces",          "Silver", "US",  69_500.00),
    ("D-04721", "Echelon Office Group",        "Gold",   "US",  67_100.00),
    ("D-04722", "Mosaic Interiors",            "Silver", "US",  64_700.00),
    ("D-04723", "Threshold Office Co.",        "Silver", "US",  62_400.00),
    ("D-04724", "Concord Workplace Solutions", "Silver", "US",  60_000.00),
    ("D-04725", "Forge Contract Interiors",    "Silver", "US",  57_500.00),
    ("D-04726", "Heritage Office Solutions",   "Gold",   "US",  55_100.00),
    ("D-04727", "Pinnacle Workspaces",         "Silver", "US",  52_700.00),
    ("D-04728", "Lattice Office Co.",          "Silver", "US",  50_400.00),
    ("D-04729", "Arbor Workplace Group",       "Silver", "US",  48_100.00),
    ("D-04730", "Solstice Office Partners",    "Silver", "US",  45_900.00),
    ("D-04731", "Lyra Contract Furniture",     "Silver", "US",  45_500.00),
    ("D-04732", "Hatch Office Solutions",      "Silver", "US",  45_200.00),
    ("D-04733", "Verity Workplace Co.",        "Silver", "US",  44_300.00),
]
HERO_DEALER_IDS = {h[0] for h in HERO_DEALERS}
# Allocation ratio: target_unused = 55% of allocated, so committed = 45% of allocated.
# allocated = target_unused / 0.55, committed_paid = allocated - target_unused.
HERO_UTILIZATION_PCT = 0.45

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def fiscal_year_for(d: date) -> str:
    if d >= date(2026, 3, 1):
        return "FY26"
    if d >= date(2025, 3, 1):
        return "FY25"
    if d >= date(2024, 3, 1):
        return "FY24"
    return "FY23"


def fiscal_period_for(d: date) -> str:
    fy_start = {
        "FY26": date(2026, 3, 1),
        "FY25": date(2025, 3, 1),
        "FY24": date(2024, 3, 1),
        "FY23": date(2023, 3, 1),
    }[fiscal_year_for(d)]
    months = (d.year - fy_start.year) * 12 + (d.month - fy_start.month)
    return f"P{months + 1:02d}"


def fiscal_quarter_for(d: date) -> str:
    period_num = int(fiscal_period_for(d)[1:])
    return f"Q{(period_num - 1) // 3 + 1}"


def random_date_between(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(0, delta)))


# ---------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------
def gen_regions() -> pl.DataFrame:
    return pl.DataFrame(
        [{"region_id": r[0], "region": r[1], "sub_region": r[2], "default_currency": r[3]} for r in REGIONS]
    )


def gen_programs() -> pl.DataFrame:
    return pl.DataFrame([
        {
            "program_id": p[0], "program_name": p[1], "fiscal_year": p[2],
            "allocation_method": p[3], "default_cofund_pct": p[4],
            "program_start": p[5], "program_end": p[6],
        } for p in PROGRAMS
    ])


def gen_activity_types() -> pl.DataFrame:
    return pl.DataFrame([
        {
            "activity_type_id": a[0], "category": a[1], "activity_name": a[2],
            "default_cofund_pct": a[3], "requires_preapproval": a[4],
            "preapproval_threshold_usd": a[5],
        } for a in ACTIVITY_TYPES
    ])


def gen_fiscal_calendar() -> pl.DataFrame:
    rows = []
    start = date(2023, 3, 1)
    end = date(2027, 2, 28)
    d = start
    while d <= end:
        rows.append({
            "date_key": d,
            "fiscal_year": fiscal_year_for(d),
            "fiscal_period": fiscal_period_for(d),
            "fiscal_week": ((d - {
                "FY23": date(2023, 3, 1),
                "FY24": date(2024, 3, 1),
                "FY25": date(2025, 3, 1),
                "FY26": date(2026, 3, 1),
            }[fiscal_year_for(d)]).days // 7) + 1,
            "fiscal_quarter": fiscal_quarter_for(d),
        })
        d += timedelta(days=1)
    return pl.DataFrame(rows)


def gen_dealers(n: int = 820) -> pl.DataFrame:
    # Region distribution: AMER 380, EMEA 260, APAC 180
    region_counts = {
        "RGN-AMER-EAST": 140,
        "RGN-AMER-WEST": 120,
        "RGN-AMER-CENTRAL": 120,
        "RGN-EMEA-NORTH": 95,
        "RGN-EMEA-SOUTH": 95,
        "RGN-EMEA-EAST": 70,
        "RGN-APAC-NORTH": 90,
        "RGN-APAC-SOUTH": 90,
    }
    rows = []
    counter = 1000
    for region_id, count in region_counts.items():
        countries = next(r[4] for r in REGIONS if r[0] == region_id).split(",")
        for _ in range(count):
            counter += 1
            tier = np.random.choice(TIERS, p=TIER_WEIGHTS)
            rows.append({
                "dealer_id": f"D-{counter:05d}",
                "salesforce_account_id": f"001{uuid.uuid4().hex[:15].upper()}",
                "dealer_name": _dealer_name(),
                "region_id": region_id,
                "country": random.choice(countries),
                "tier": tier,
                "sales_rep_id": f"REP-{random.randint(100, 999)}",
                "effective_from": date(2023, 1, 1),
                "effective_to": None,
                "is_current": True,
            })
    # Append pinned hero dealers (deterministic IDs, names, tiers).
    for dealer_id, dealer_name, tier, country, _unused in HERO_DEALERS:
        rows.append({
            "dealer_id": dealer_id,
            "salesforce_account_id": f"001{uuid.uuid4().hex[:15].upper()}",
            "dealer_name": dealer_name,
            "region_id": HERO_REGION_ID,
            "country": country,
            "tier": tier,
            "sales_rep_id": f"REP-{random.randint(100, 999)}",
            "effective_from": date(2023, 1, 1),
            "effective_to": None,
            "is_current": True,
        })
    return pl.DataFrame(rows)


def _dealer_name() -> str:
    """Plausible-sounding dealer/dealership names."""
    prefixes = ["Pivot", "Halcyon", "Northpoint", "Riverline", "Beacon", "Atlas",
                "Skyline", "Meridian", "Cascade", "Cornerstone", "Vantage", "Summit",
                "Keystone", "Pinnacle", "Heritage", "Forge", "Mosaic", "Lattice",
                "Threshold", "Concord", "Echelon", "Verity", "Hatch", "Quantum",
                "Plum", "Arbor", "Hearth", "Lyra", "Solstice", "Anvil"]
    cores  = ["Workplace", "Office", "Workspace", "Interiors", "Contract",
              "Furniture", "Studio", "Group", "Solutions", "Co.", "Collective",
              "Partners", "Works", "Design", "Build"]
    suffix = random.choice(["Solutions", "Group", "Inc.", "LLC", "Co.", "Partners", "", "", ""])
    parts = [random.choice(prefixes), random.choice(cores)]
    if suffix:
        parts.append(suffix)
    return " ".join(parts)


def gen_allocations(dealers: pl.DataFrame, programs: pl.DataFrame, as_of: date) -> pl.DataFrame:
    rows = []
    for d in dealers.iter_rows(named=True):
        if d["dealer_id"] in HERO_DEALER_IDS:
            continue  # hero allocations are emitted by gen_hero_allocations_and_claims
        base = TIER_BASE_ALLOCATION_USD[d["tier"]]
        for p in programs.iter_rows(named=True):
            # Only main co-op program for every dealer; specialty programs for subset
            if "COOP-MAIN" not in p["program_id"]:
                if random.random() > 0.18:
                    continue
                # EMEA dealers can be on EMEA digital, APAC on APAC launch, etc.
                if "EMEA" in p["program_id"] and not d["region_id"].startswith("RGN-EMEA"):
                    continue
                if "APAC" in p["program_id"] and not d["region_id"].startswith("RGN-APAC"):
                    continue
            if p["fiscal_year"] == "FY24" and random.random() > 0.7:
                continue  # not all dealers participated in older programs
            jitter = np.random.normal(loc=1.0, scale=0.20)
            allocated = max(2000.0, base * max(0.4, jitter))
            allocation_date = p["program_start"] + timedelta(days=random.randint(0, 30))
            rows.append({
                "allocation_id": f"AL-{uuid.uuid4().hex[:12].upper()}",
                "dealer_id": d["dealer_id"],
                "program_id": p["program_id"],
                "fiscal_year": p["fiscal_year"],
                "allocated_usd": round(allocated, 2),
                "allocation_date": allocation_date,
                "expiration_date": p["program_end"],
                "allocation_source": "initial",
            })
    return pl.DataFrame(rows)


def gen_claims(dealers: pl.DataFrame, allocations: pl.DataFrame,
               activity_types: pl.DataFrame, as_of: date) -> pl.DataFrame:
    rows = []
    statuses = list(CLAIM_STATUS_DIST.keys())
    weights = list(CLAIM_STATUS_DIST.values())
    act_lookup = {a["activity_type_id"]: a for a in activity_types.iter_rows(named=True)}
    dealer_lookup = {d["dealer_id"]: d for d in dealers.iter_rows(named=True)}
    # AMER East dealers: planted forfeiture hotspot
    amer_east_dealer_ids = [d["dealer_id"] for d in dealers.iter_rows(named=True)
                            if d["region_id"] == "RGN-AMER-EAST"]
    hotspot_ids = set(random.sample(amer_east_dealer_ids, 23))

    counter = 0
    for alloc in allocations.iter_rows(named=True):
        n_claims_for_alloc = max(1, int(np.random.gamma(shape=2.0, scale=1.8)))
        is_hotspot = alloc["dealer_id"] in hotspot_ids and alloc["fiscal_year"] == "FY26"
        if is_hotspot:
            n_claims_for_alloc = max(1, n_claims_for_alloc - 3)  # under-utilize

        for _ in range(n_claims_for_alloc):
            counter += 1
            sub_date = random_date_between(
                alloc["allocation_date"] + timedelta(days=15),
                min(as_of, alloc["expiration_date"]),
            )
            activity = random.choice(list(act_lookup.values()))
            requested = round(np.random.lognormal(mean=8.5, sigma=0.8), 2)
            requested = max(250.0, min(requested, 60_000.0))

            status = np.random.choice(statuses, p=weights)
            approved = None
            paid = None
            decision_date = None
            payment_date = None
            preapproval_id = None
            if activity["requires_preapproval"] and (activity["preapproval_threshold_usd"] is None
                                                    or requested >= (activity["preapproval_threshold_usd"] or 0)):
                if random.random() > 0.05:  # 95% have preapproval where required
                    preapproval_id = f"PA-{uuid.uuid4().hex[:8].upper()}"

            if status in ("Approved", "Paid"):
                approved = round(requested * np.random.uniform(0.85, 1.0), 2)
                decision_date = sub_date + timedelta(days=random.randint(3, 21))
            if status == "Paid":
                paid = round(approved * np.random.uniform(0.95, 1.0), 2)
                payment_date = decision_date + timedelta(days=random.randint(7, 30))
            if status == "Rejected":
                decision_date = sub_date + timedelta(days=random.randint(3, 14))
            if status == "Expired":
                decision_date = None

            # Plant ROI signal: EMEA + Programmatic Display gets boosted approval/paid rates
            if (activity["activity_type_id"] == "ACT-DIG-PROG-DISPLAY"
                    and dealer_lookup[alloc["dealer_id"]]["region_id"].startswith("RGN-EMEA")
                    and status in ("Approved", "Paid")):
                approved = round(requested * 1.0, 2)
                if status == "Paid":
                    paid = round(approved, 2)

            rows.append({
                "claim_id": f"CL-{alloc['fiscal_year']}-{counter:06d}",
                "dealer_id": alloc["dealer_id"],
                "program_id": alloc["program_id"],
                "activity_type_id": activity["activity_type_id"],
                "preapproval_id": preapproval_id,
                "submission_date": sub_date,
                "requested_amount_usd": requested,
                "approved_amount_usd": approved,
                "paid_amount_usd": paid,
                "status": status,
                "brand_compliance_score": random.randint(55, 100) if status != "Draft" else None,
                "reviewer_id": f"RV-{random.randint(10, 50)}" if status != "Draft" else None,
                "decision_date": decision_date,
                "payment_date": payment_date,
                "claim_doc_uri": f"/Volumes/steelcase_demo/raw/claims/{alloc['fiscal_year']}/CL-{counter:06d}.pdf",
                "fiscal_year": alloc["fiscal_year"],
            })
    return pl.DataFrame(rows)


def gen_sell_through(dealers: pl.DataFrame, as_of: date,
                     lines_per_dealer: tuple[int, int] = (300, 1200)) -> pl.DataFrame:
    rows = []
    for d in dealers.iter_rows(named=True):
        n = random.randint(*lines_per_dealer)
        tier_mult = {"Platinum": 4.0, "Gold": 2.0, "Silver": 1.0, "Authorized": 0.5}[d["tier"]]
        for _ in range(n):
            order_date = random_date_between(date(2023, 3, 1), as_of)
            rows.append({
                "order_line_id": f"OL-{uuid.uuid4().hex[:14].upper()}",
                "order_id": f"O-{uuid.uuid4().hex[:10].upper()}",
                "dealer_id": d["dealer_id"],
                "product_family": np.random.choice(
                    PRODUCT_FAMILIES, p=[0.35, 0.25, 0.15, 0.15, 0.10]
                ),
                "order_date": order_date,
                "ship_date": order_date + timedelta(days=random.randint(3, 35)),
                "net_revenue_usd": round(np.random.lognormal(mean=8.0, sigma=0.9) * tier_mult, 2),
                "fiscal_year": fiscal_year_for(order_date),
            })
    return pl.DataFrame(rows)


def gen_events(dealers: pl.DataFrame, activity_types: pl.DataFrame, as_of: date) -> pl.DataFrame:
    rows = []
    event_activity_ids = [a["activity_type_id"] for a in activity_types.iter_rows(named=True)
                          if a["category"] in ("Event", "Sponsorship")]
    for d in dealers.iter_rows(named=True):
        n = random.randint(0, 6)
        for _ in range(n):
            start = random_date_between(date(2023, 3, 1), as_of)
            end = start + timedelta(days=random.randint(0, 3))
            rows.append({
                "event_id": f"EV-{uuid.uuid4().hex[:12].upper()}",
                "dealer_id": d["dealer_id"],
                "activity_type_id": random.choice(event_activity_ids),
                "start_date": start,
                "end_date": end,
                "attendees": random.randint(15, 400),
                "event_cost_usd": round(np.random.lognormal(mean=9.0, sigma=0.7), 2),
                "claim_id_nullable": None,  # populated by enrichment step
                "fiscal_year": fiscal_year_for(start),
            })
    return pl.DataFrame(rows)


# ---------------------------------------------------------------------
# Hero dealer allocations + claims (deterministic; drives "$1.62M" demo)
# ---------------------------------------------------------------------
def gen_hero_allocations_and_claims(as_of: date) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Emit exact FY26 main-co-op allocations + Paid claims for hero dealers
    such that sum(unused) = sum(target_unused_usd) ≈ $1.62M."""
    alloc_rows: list[dict] = []
    claim_rows: list[dict] = []
    claim_counter = 900_000  # high range to avoid collision with regular claims

    paid_activity_pool = [
        "ACT-DIG-PAID-SOCIAL", "ACT-DIG-PROG-DISPLAY", "ACT-DIG-SEM",
        "ACT-EVT-DEALER-EVENT", "ACT-EVT-AD-EVENT", "ACT-CON-LITERATURE",
        "ACT-CON-VIDEO", "ACT-CON-CASE-STUDY",
    ]

    for dealer_id, _name, _tier, _country, target_unused in HERO_DEALERS:
        # allocated_usd chosen so committed/allocated = 1 - target_unused/allocated = 0.45
        allocated = round(target_unused / (1 - HERO_UTILIZATION_PCT), 2)
        target_committed = round(allocated - target_unused, 2)  # exact

        alloc_rows.append({
            "allocation_id": f"AL-HERO-{dealer_id}",
            "dealer_id": dealer_id,
            "program_id": HERO_PROGRAM_ID,
            "fiscal_year": "FY26",
            "allocated_usd": allocated,
            "allocation_date": date(2026, 3, 5),
            "expiration_date": date(2027, 2, 28),
            "allocation_source": "initial",
        })

        # Split committed into N Paid claims, sum exact (last claim absorbs rounding).
        n_claims = random.randint(6, 10)
        portions = np.random.dirichlet(np.ones(n_claims))
        amounts = np.round(portions * target_committed, 2)
        amounts[-1] = round(target_committed - amounts[:-1].sum(), 2)

        for amt in amounts:
            claim_counter += 1
            sub_date = random_date_between(
                date(2026, 3, 15),
                min(as_of - timedelta(days=25), date(2026, 9, 30)),
            )
            decision_date = sub_date + timedelta(days=random.randint(3, 14))
            payment_date = decision_date + timedelta(days=random.randint(7, 21))
            activity_id = random.choice(paid_activity_pool)
            claim_rows.append({
                "claim_id": f"CL-FY26-{claim_counter:06d}",
                "dealer_id": dealer_id,
                "program_id": HERO_PROGRAM_ID,
                "activity_type_id": activity_id,
                "preapproval_id": f"PA-{uuid.uuid4().hex[:8].upper()}" if amt >= 5000 else None,
                "submission_date": sub_date,
                "requested_amount_usd": float(amt),
                "approved_amount_usd": float(amt),
                "paid_amount_usd": float(amt),
                "status": "Paid",
                "brand_compliance_score": random.randint(75, 95),
                "reviewer_id": f"RV-{random.randint(10, 50)}",
                "decision_date": decision_date,
                "payment_date": payment_date,
                "claim_doc_uri": f"/Volumes/steelcase_demo/raw/claims/FY26/CL-FY26-{claim_counter:06d}.pdf",
                "fiscal_year": "FY26",
            })

    return pl.DataFrame(alloc_rows), pl.DataFrame(claim_rows)


# ---------------------------------------------------------------------
# Demo-shaping fixup: cap non-hero AMER East unused so hero cohort tops the list
# ---------------------------------------------------------------------
def _topoff_amer_east_non_hero(dealers: pl.DataFrame, allocations: pl.DataFrame,
                                claims: pl.DataFrame, as_of: date) -> pl.DataFrame:
    target_utilization = 0.92
    amer_east_non_hero = (dealers
        .filter((pl.col("region_id") == "RGN-AMER-EAST")
                & (~pl.col("dealer_id").is_in(list(HERO_DEALER_IDS))))
        .select("dealer_id"))

    target_allocs = (allocations
        .join(amer_east_non_hero, on="dealer_id", how="inner")
        .filter(pl.col("fiscal_year") == "FY26")
        .group_by(["dealer_id", "program_id", "fiscal_year"])
        .agg(pl.col("allocated_usd").sum().alias("allocated_usd"))
    )
    current_paid = (claims
        .filter((pl.col("status") == "Paid") & (pl.col("fiscal_year") == "FY26"))
        .group_by(["dealer_id", "program_id"])
        .agg(pl.col("paid_amount_usd").sum().alias("paid_usd"))
    )
    deficit = (target_allocs
        .join(current_paid, on=["dealer_id", "program_id"], how="left")
        .with_columns(pl.col("paid_usd").fill_null(0.0))
        .with_columns(
            (pl.col("allocated_usd") * target_utilization - pl.col("paid_usd"))
                .clip(0.0, None).alias("topoff_usd")
        )
        .filter(pl.col("topoff_usd") > 0)
    )

    topoff_rows: list[dict] = []
    counter = 950_000
    for r in deficit.iter_rows(named=True):
        counter += 1
        sub_date = random_date_between(date(2026, 3, 20), min(as_of - timedelta(days=20), date(2026, 9, 25)))
        decision_date = sub_date + timedelta(days=random.randint(3, 12))
        payment_date = decision_date + timedelta(days=random.randint(7, 18))
        amt = round(float(r["topoff_usd"]), 2)
        topoff_rows.append({
            "claim_id": f"CL-FY26-{counter:06d}",
            "dealer_id": r["dealer_id"],
            "program_id": r["program_id"],
            "activity_type_id": "ACT-DIG-PAID-SOCIAL",
            "preapproval_id": f"PA-{uuid.uuid4().hex[:8].upper()}" if amt >= 5000 else None,
            "submission_date": sub_date,
            "requested_amount_usd": amt,
            "approved_amount_usd": amt,
            "paid_amount_usd": amt,
            "status": "Paid",
            "brand_compliance_score": random.randint(75, 95),
            "reviewer_id": f"RV-{random.randint(10, 50)}",
            "decision_date": decision_date,
            "payment_date": payment_date,
            "claim_doc_uri": f"/Volumes/steelcase_demo/raw/claims/FY26/CL-FY26-{counter:06d}.pdf",
            "fiscal_year": "FY26",
        })

    if not topoff_rows:
        return claims
    return pl.concat([claims, pl.DataFrame(topoff_rows)], how="diagonal_relaxed")


# ---------------------------------------------------------------------
# Phase 1.5 — single source workbook with 4 sheets
#
# Hydrates the four `bronze.*` raw tables from one Excel file. Column
# names match the bronze DDL (`dealer_external_id`, `program_code`,
# `activity_code`, etc.) so the Phase 1.5 DLT pipeline can read each
# sheet straight into its target table without renames.
# ---------------------------------------------------------------------
def write_bronze_source_workbook(path: Path,
                                  allocations: pl.DataFrame,
                                  claims: pl.DataFrame,
                                  sell_through: pl.DataFrame,
                                  events: pl.DataFrame) -> None:
    import pandas as pd

    alloc_sheet = (allocations
        .rename({"dealer_id": "dealer_external_id",
                 "program_id": "program_code"})
        .select(["allocation_id", "dealer_external_id", "program_code",
                 "fiscal_year", "allocated_usd", "allocation_date",
                 "expiration_date", "allocation_source"])
    )

    erp_sheet = (sell_through
        .rename({"dealer_id": "dealer_external_id"})
        .with_columns(pl.lit("USD").alias("currency"))
        .select(["order_id", "order_line_id", "dealer_external_id",
                 "product_family", "order_date", "ship_date",
                 "net_revenue_usd", "currency"])
    )

    events_sheet = (events
        .rename({"dealer_id": "dealer_external_id",
                 "activity_type_id": "activity_code",
                 "claim_id_nullable": "claim_id"})
        .select(["event_id", "dealer_external_id", "activity_code",
                 "start_date", "end_date", "attendees",
                 "event_cost_usd", "claim_id"])
    )

    claims_sheet = (claims
        .rename({"dealer_id": "dealer_external_id",
                 "program_id": "program_code",
                 "activity_type_id": "activity_code",
                 "requested_amount_usd": "requested_amount",
                 "approved_amount_usd": "approved_amount",
                 "paid_amount_usd": "paid_amount"})
        .select(["claim_id", "dealer_external_id", "program_code",
                 "activity_code", "preapproval_id", "submission_date",
                 "requested_amount", "approved_amount", "paid_amount",
                 "status", "brand_compliance_score", "reviewer_id",
                 "decision_date", "payment_date", "claim_doc_uri"])
    )

    with pd.ExcelWriter(path, engine="xlsxwriter") as xl:
        alloc_sheet.to_pandas().to_excel(xl, sheet_name="Allocations", index=False)
        erp_sheet.to_pandas().to_excel(xl, sheet_name="ERP_Sales_Orders", index=False)
        events_sheet.to_pandas().to_excel(xl, sheet_name="Event_Registrations", index=False)
        claims_sheet.to_pandas().to_excel(xl, sheet_name="Portal_Claims", index=False)

    print(f"      wrote {path.name}: "
          f"Allocations={len(alloc_sheet):,}  "
          f"ERP_Sales_Orders={len(erp_sheet):,}  "
          f"Event_Registrations={len(events_sheet):,}  "
          f"Portal_Claims={len(claims_sheet):,}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="./seed")
    parser.add_argument("--as-of", type=str, default=AS_OF_DEFAULT.isoformat())
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    as_of = date.fromisoformat(args.as_of)

    print(f"[1/9] regions");        gen_regions().write_parquet(out / "region.parquet")
    print(f"[2/9] programs");       gen_programs().write_parquet(out / "program.parquet")
    print(f"[3/9] activity_types"); gen_activity_types().write_parquet(out / "activity_type.parquet")
    print(f"[4/9] fiscal_calendar");gen_fiscal_calendar().write_parquet(out / "fiscal_calendar.parquet")

    print(f"[5/9] dealers")
    dealers = gen_dealers()
    dealers.write_parquet(out / "dealer.parquet")

    print(f"[6/9] allocations (+ hero allocations)")
    programs = gen_programs()
    allocations = gen_allocations(dealers, programs, as_of)
    hero_allocs, hero_claims = gen_hero_allocations_and_claims(as_of)
    allocations = pl.concat([allocations, hero_allocs], how="diagonal_relaxed")
    allocations.write_parquet(out / "coop_allocation.parquet")

    print(f"[7/9] claims (~28k rows — this is the slow step)")
    activity_types = gen_activity_types()
    # gen_claims iterates allocations, but hero allocs are already in `allocations`.
    # To avoid double-claim generation for heroes, pass the non-hero subset.
    non_hero_allocs = allocations.filter(~pl.col("dealer_id").is_in(list(HERO_DEALER_IDS)))
    claims = gen_claims(dealers, non_hero_allocs, activity_types, as_of)
    claims = pl.concat([claims, hero_claims], how="diagonal_relaxed")

    # Top-off pass: for every non-hero AMER East dealer on FY26 main co-op, append a
    # synthetic Paid "balance-burn" claim sized so sum(paid) >= 0.92 * allocated.
    # Without this, random Platinum non-hero AMER East dealers (base alloc $200K, few
    # claims) end up with $150K+ unused and crowd the hero cohort out of the top 23.
    # The click-script's Act 2 names Pivot/Halcyon/Northpoint as top 3 — this fix is
    # what makes the hero cohort the actual top of `metric.forfeiture_risk` for AMER East.
    claims = _topoff_amer_east_non_hero(dealers, allocations, claims, as_of)
    claims.write_parquet(out / "coop_claim.parquet")

    print(f"[8/9] sell_through + events")
    sell_through = gen_sell_through(dealers, as_of)
    sell_through.write_parquet(out / "sell_through_order.parquet")
    events = gen_events(dealers, activity_types, as_of)
    events.write_parquet(out / "marketing_event.parquet")

    print(f"[9/9] compass-source.xlsx (4 sheets — Phase 1.5 bronze source)")
    write_bronze_source_workbook(out / "compass-source.xlsx",
                                  allocations=allocations,
                                  claims=claims,
                                  sell_through=sell_through,
                                  events=events)

    print("\nDone. Files written to", out.resolve())
    print(f"  dealers:        {len(dealers):>8}")
    print(f"  allocations:    {len(allocations):>8}")
    print(f"  claims:         {len(claims):>8}")
    print(f"  status mix:")
    for status, frac in claims.group_by("status").len().sort("len", descending=True).iter_rows():
        print(f"    {status:<14} {frac}")

    # Hero sanity check
    hero_alloc_total = (allocations
        .filter(pl.col("dealer_id").is_in(list(HERO_DEALER_IDS)))
        .select(pl.col("allocated_usd").sum()).item())
    hero_paid_total = (claims
        .filter(pl.col("dealer_id").is_in(list(HERO_DEALER_IDS)) & (pl.col("status") == "Paid"))
        .select(pl.col("paid_amount_usd").sum()).item())
    hero_unused = hero_alloc_total - hero_paid_total
    print(f"\n  HERO COHORT (23 AMER East dealers, FY26 main co-op):")
    print(f"    allocated:    ${hero_alloc_total:>12,.0f}")
    print(f"    paid:         ${hero_paid_total:>12,.0f}")
    print(f"    unused:       ${hero_unused:>12,.0f}   <-- target $1,619,400 (~$1.62M)")


if __name__ == "__main__":
    main()
