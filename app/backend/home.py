"""Role-shaped home payload for /api/home.

Each role gets a small set of headline KPI tiles and an optional secondary
list (top dealers, by-region rollup, etc.). Queries the warehouse for live
numbers when the SQL warehouse is reachable; falls back to the hero values
from the storyline if it isn't.

The hero cohort is AMER East FY26 — expected_forfeit ≈ $1.62M, top-3 unused
Pivot $147.2K / Halcyon $118.4K / Northpoint $96.3K. Static fallbacks match.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .agent.router import UserContext
from .config import Settings
from .schemas import HomeResponse, HomeRow, HomeTile

log = logging.getLogger(__name__)


COMPASS_CATALOG = os.environ.get("COMPASS_CATALOG", "classic_stable_1zia5t_kp_catalog")
COMPASS_GOLD_SCHEMA = os.environ.get("COMPASS_GOLD_SCHEMA", "compass_gold")


def build_home(
    user: UserContext,
    settings: Settings,
    engine: Engine | None,
    w: Any | None = None,
) -> HomeResponse:
    role = user.role
    builders = {
        "channel_mgr": _channel_mgr,
        "rmd": _rmd,
        "director": _director,
        "finance": _finance,
        "dealer": _dealer,
    }
    builder = builders.get(role, _guest)
    try:
        return builder(user, settings, engine, w)
    except Exception:
        log.exception("home builder for role=%s failed; returning fallback", role)
        return _guest(user, settings, engine, w)


def _sql_one(w: Any, settings: Settings, query: str) -> dict[str, Any] | None:
    """Run a single-row query on the warehouse and return the first row as a dict."""
    try:
        result = w.statement_execution.execute_statement(
            statement=query,
            warehouse_id=settings.warehouse_id,
            wait_timeout="30s",
        )
        schema = result.manifest.schema if result.manifest else None
        columns = [c.name for c in (schema.columns or [])] if schema else []
        data = result.result.data_array if result.result else []
        if not data:
            return None
        return dict(zip(columns, data[0]))
    except Exception:
        log.exception("home SQL failed: %s", query[:120])
        return None


def _sql_rows(w: Any, settings: Settings, query: str) -> list[dict[str, Any]]:
    try:
        result = w.statement_execution.execute_statement(
            statement=query,
            warehouse_id=settings.warehouse_id,
            wait_timeout="30s",
        )
        schema = result.manifest.schema if result.manifest else None
        columns = [c.name for c in (schema.columns or [])] if schema else []
        data = result.result.data_array if result.result else []
        return [dict(zip(columns, row)) for row in (data or [])]
    except Exception:
        log.exception("home SQL rows failed: %s", query[:120])
        return []


# ----------------------------------------------------------------------
# Channel manager (Maya / Kaustav) — region-scoped scorecard
# ----------------------------------------------------------------------


def _channel_mgr(
    user: UserContext, settings: Settings, engine: Engine | None, w: Any | None
) -> HomeResponse:
    region = user.region_id or "RGN-AMER-EAST"
    pending = _pending_approvals_count(engine, region)

    tiles: list[HomeTile] = []
    rows: list[HomeRow] = []
    headline = f"You're scoped to {region} for FY26."

    if w is not None:
        summary = _sql_one(
            w,
            settings,
            f"""
            SELECT
              SUM(unused_usd)         AS unused_usd,
              SUM(allocated_usd)      AS allocated_usd,
              SUM(paid_usd)           AS paid_usd,
              COUNT(DISTINCT dealer_id) AS dealer_count
            FROM {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.fact_coop_utilization_daily f
            JOIN {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.dim_dealer d
              USING (dealer_id)
            WHERE f.fiscal_year = 'FY26'
              AND d.region_id = '{region}'
            """,
        )
        at_risk = _sql_rows(
            w,
            settings,
            f"""
            SELECT d.dealer_name, ROUND(SUM(f.unused_usd)) AS unused_usd
            FROM {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.fact_coop_utilization_daily f
            JOIN {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.dim_dealer d
              USING (dealer_id)
            WHERE f.fiscal_year = 'FY26'
              AND d.region_id = '{region}'
            GROUP BY d.dealer_name
            HAVING SUM(f.unused_usd) > 40000
            ORDER BY unused_usd DESC
            LIMIT 5
            """,
        )
        if summary:
            tiles.append(
                HomeTile(
                    key="forfeiture_risk",
                    label="FY26 forfeiture risk",
                    value=_to_int(summary.get("unused_usd")) or 1_619_574,
                    format="currency",
                    intent="bad",
                )
            )
            tiles.append(
                HomeTile(
                    key="utilization_rate",
                    label="Region utilization",
                    value=_pct(summary.get("paid_usd"), summary.get("allocated_usd")),
                    format="percent",
                    intent="warn",
                )
            )
        tiles.append(
            HomeTile(
                key="at_risk_dealers",
                label="Dealers > $40K unused",
                value=len(at_risk) if at_risk else 17,
                format="count",
                intent="warn",
            )
        )
        rows = [
            HomeRow(
                primary=r["dealer_name"],
                secondary=f"${_to_int(r.get('unused_usd')):,} unused",
                intent="warn",
            )
            for r in at_risk
        ]

    if not tiles:
        # Lite / SQL-unavailable fallback — hero storyline numbers.
        tiles = [
            HomeTile(key="forfeiture_risk", label="FY26 forfeiture risk",
                     value=1_619_574, format="currency", intent="bad"),
            HomeTile(key="utilization_rate", label="Region utilization",
                     value=63.4, format="percent", intent="warn"),
            HomeTile(key="at_risk_dealers", label="Dealers > $40K unused",
                     value=17, format="count", intent="warn"),
        ]
        rows = [
            HomeRow(primary="Pivot Workplace Solutions", secondary="$147,200 unused", intent="warn"),
            HomeRow(primary="Halcyon Office Group",      secondary="$118,400 unused", intent="warn"),
            HomeRow(primary="Northpoint Workspaces",     secondary="$96,300 unused",  intent="warn"),
        ]

    tiles.append(
        HomeTile(
            key="pending_approvals",
            label="Pending approvals",
            value=pending if pending is not None else 5,
            format="count",
            intent="neutral" if (pending or 0) < 10 else "warn",
        )
    )

    return HomeResponse(
        role="channel_mgr",
        scope_label=region,
        headline=headline,
        tiles=tiles,
        rows=rows,
    )


# ----------------------------------------------------------------------
# RMD — region rollup (same shape as channel_mgr, different copy)
# ----------------------------------------------------------------------


def _rmd(
    user: UserContext, settings: Settings, engine: Engine | None, w: Any | None
) -> HomeResponse:
    payload = _channel_mgr(user, settings, engine, w)
    return HomeResponse(
        role="rmd",
        scope_label=payload.scope_label,
        headline=f"Regional Marketing Director view — {payload.scope_label}.",
        tiles=payload.tiles,
        rows=payload.rows,
    )


# ----------------------------------------------------------------------
# Director — global portfolio
# ----------------------------------------------------------------------


def _director(
    user: UserContext, settings: Settings, engine: Engine | None, w: Any | None
) -> HomeResponse:
    tiles: list[HomeTile] = []
    rows: list[HomeRow] = []

    if w is not None:
        summary = _sql_one(
            w,
            settings,
            f"""
            SELECT
              SUM(unused_usd)    AS unused_usd,
              SUM(paid_usd)      AS paid_usd,
              SUM(allocated_usd) AS allocated_usd
            FROM {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.fact_coop_utilization_daily
            WHERE fiscal_year = 'FY26'
            """,
        )
        by_region = _sql_rows(
            w,
            settings,
            f"""
            SELECT
              r.region,
              ROUND(SUM(f.unused_usd)) AS unused_usd,
              ROUND(100.0 * SUM(f.paid_usd) / NULLIF(SUM(f.allocated_usd),0), 1) AS util_pct
            FROM {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.fact_coop_utilization_daily f
            JOIN {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.dim_dealer d USING (dealer_id)
            JOIN {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.dim_region r ON d.region_id = r.region_id
            WHERE f.fiscal_year = 'FY26'
            GROUP BY r.region
            ORDER BY unused_usd DESC
            """,
        )
        if summary:
            tiles.append(HomeTile(key="global_forfeiture", label="Global FY26 forfeiture risk",
                                  value=_to_int(summary.get("unused_usd")), format="currency", intent="bad"))
            tiles.append(HomeTile(key="global_utilization", label="Global utilization",
                                  value=_pct(summary.get("paid_usd"), summary.get("allocated_usd")),
                                  format="percent", intent="warn"))
            tiles.append(HomeTile(key="global_paid", label="Paid YTD",
                                  value=_to_int(summary.get("paid_usd")), format="currency", intent="good"))
        rows = [
            HomeRow(primary=r["region"],
                    secondary=f"util {r.get('util_pct')}%",
                    metric=f"${_to_int(r.get('unused_usd')):,}",
                    intent="warn")
            for r in by_region
        ]

    if not tiles:
        tiles = [
            HomeTile(key="global_forfeiture", label="Global FY26 forfeiture risk",
                     value=4_280_000, format="currency", intent="bad"),
            HomeTile(key="global_utilization", label="Global utilization",
                     value=68.2, format="percent", intent="warn"),
            HomeTile(key="global_paid", label="Paid YTD",
                     value=12_400_000, format="currency", intent="good"),
        ]
        rows = [
            HomeRow(primary="AMER", secondary="util 63.4%", metric="$1.62M", intent="warn"),
            HomeRow(primary="EMEA", secondary="util 71.1%", metric="$1.18M", intent="warn"),
            HomeRow(primary="APAC", secondary="util 74.9%", metric="$1.48M", intent="neutral"),
        ]

    return HomeResponse(
        role="director",
        scope_label="Global",
        headline="Global co-op portfolio — FY26 to date.",
        tiles=tiles,
        rows=rows,
    )


# ----------------------------------------------------------------------
# Finance — forfeiture exposure focus
# ----------------------------------------------------------------------


def _finance(
    user: UserContext, settings: Settings, engine: Engine | None, w: Any | None
) -> HomeResponse:
    tiles: list[HomeTile] = []
    if w is not None:
        summary = _sql_one(
            w,
            settings,
            f"""
            SELECT
              SUM(unused_usd)    AS unused_usd,
              SUM(paid_usd)      AS paid_usd,
              SUM(committed_usd) AS committed_usd,
              SUM(approved_usd)  AS approved_usd
            FROM {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.fact_coop_utilization_daily
            WHERE fiscal_year = 'FY26'
            """,
        )
        if summary:
            tiles = [
                HomeTile(key="exposure", label="Forfeiture exposure",
                         value=_to_int(summary.get("unused_usd")), format="currency", intent="bad"),
                HomeTile(key="paid_ytd", label="Paid YTD",
                         value=_to_int(summary.get("paid_usd")), format="currency", intent="good"),
                HomeTile(key="accrual", label="Approved, not paid",
                         value=max(0, (_to_int(summary.get("approved_usd")) or 0)
                                   - (_to_int(summary.get("paid_usd")) or 0)),
                         format="currency", intent="neutral"),
                HomeTile(key="committed", label="Committed",
                         value=_to_int(summary.get("committed_usd")), format="currency", intent="neutral"),
            ]
    if not tiles:
        tiles = [
            HomeTile(key="exposure", label="Forfeiture exposure", value=4_280_000, format="currency", intent="bad"),
            HomeTile(key="paid_ytd", label="Paid YTD", value=12_400_000, format="currency", intent="good"),
            HomeTile(key="accrual", label="Approved, not paid", value=2_150_000, format="currency", intent="neutral"),
            HomeTile(key="committed", label="Committed", value=18_900_000, format="currency", intent="neutral"),
        ]
    return HomeResponse(
        role="finance",
        scope_label="Global, FY26",
        headline="Forfeiture exposure and FY26 accrual.",
        tiles=tiles,
        rows=[],
    )


# ----------------------------------------------------------------------
# Dealer — scoped to their dealer_id
# ----------------------------------------------------------------------


def _dealer(
    user: UserContext, settings: Settings, engine: Engine | None, w: Any | None
) -> HomeResponse:
    dealer_id = user.dealer_id or "D-04711"
    tiles: list[HomeTile] = []
    headline = f"Your dealership ({dealer_id}) — FY26 to date."
    if w is not None:
        summary = _sql_one(
            w,
            settings,
            f"""
            SELECT
              SUM(unused_usd)    AS unused_usd,
              SUM(paid_usd)      AS paid_usd,
              SUM(allocated_usd) AS allocated_usd,
              SUM(approved_usd)  AS approved_usd
            FROM {COMPASS_CATALOG}.{COMPASS_GOLD_SCHEMA}.fact_coop_utilization_daily
            WHERE fiscal_year = 'FY26'
              AND dealer_id = '{dealer_id}'
            """,
        )
        if summary:
            tiles = [
                HomeTile(key="available", label="Available balance",
                         value=_to_int(summary.get("unused_usd")), format="currency", intent="good"),
                HomeTile(key="allocation", label="FY26 allocation",
                         value=_to_int(summary.get("allocated_usd")), format="currency", intent="neutral"),
                HomeTile(key="approved", label="Approved YTD",
                         value=_to_int(summary.get("approved_usd")), format="currency", intent="good"),
                HomeTile(key="paid", label="Paid YTD",
                         value=_to_int(summary.get("paid_usd")), format="currency", intent="good"),
            ]
    if not tiles:
        tiles = [
            HomeTile(key="available", label="Available balance", value=147_200, format="currency", intent="good"),
            HomeTile(key="allocation", label="FY26 allocation", value=400_000, format="currency", intent="neutral"),
            HomeTile(key="approved", label="Approved YTD", value=180_300, format="currency", intent="good"),
            HomeTile(key="paid", label="Paid YTD", value=145_900, format="currency", intent="good"),
        ]
    return HomeResponse(
        role="dealer",
        scope_label=dealer_id,
        headline=headline,
        tiles=tiles,
        rows=[],
    )


# ----------------------------------------------------------------------
# Guest fallback
# ----------------------------------------------------------------------


def _guest(
    user: UserContext, settings: Settings, engine: Engine | None, w: Any | None
) -> HomeResponse:
    return HomeResponse(
        role=user.role or "guest",
        scope_label="—",
        headline="Sign in with a known persona to see your scorecard.",
        tiles=[],
        rows=[],
    )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _pending_approvals_count(engine: Engine | None, region_id: str | None) -> int | None:
    if engine is None:
        return None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT count(*)
                      FROM compass.claim_review cr
                 LEFT JOIN compass.v_dealer vd USING (dealer_id)
                     WHERE cr.status = 'Pending'
                       AND (CAST(:region AS text) IS NULL OR vd.region_id = :region)
                    """
                ),
                {"region": region_id},
            ).first()
        return int(row[0]) if row else 0
    except Exception:
        log.exception("pending approvals count failed")
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def _pct(num: Any, denom: Any) -> float | None:
    n, d = _to_int(num), _to_int(denom)
    if not d:
        return None
    return round(100.0 * (n or 0) / d, 1)
