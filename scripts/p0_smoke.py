#!/usr/bin/env python3
"""P0 smoke — A2 (backend paths) + A3 (Genie spaces).

Exercises the same WorkspaceClient calls the COMPASS BFF uses. Run after
granting the App SP CAN_QUERY on mas-2a692b50-endpoint:

    DATABRICKS_CONFIG_PROFILE=fevm python scripts/p0_smoke.py

Exit 0 if all checks pass; non-zero otherwise.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass

# Allow importing app backend when run from repo root.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "app"))

from databricks.sdk import WorkspaceClient

from backend.agent.router import UserContext
from backend.agent import workers
from backend.config import Settings

UTIL_SPACE = "01f152f8ed8a1682af57700b37fb11bb"
MKT_SPACE = "01f1532267c4147d9781fe17c1c6230f"
HERO_FORFEIT_LO = 1_600_000
HERO_FORFEIT_HI = 1_650_000


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _settings() -> Settings:
    os.environ.setdefault("COMPASS_GENIE_SPACE_UTIL_RISK_ID", UTIL_SPACE)
    os.environ.setdefault("COMPASS_GENIE_SPACE_MARKETING_ID", MKT_SPACE)
    os.environ.setdefault("COMPASS_KA_ENDPOINT", "ka-f000ded6-endpoint")
    os.environ.setdefault("COMPASS_WAREHOUSE_ID", "e6dc9b218651c48a")
    os.environ.setdefault("COMPASS_LAKEBASE_HOST", "ep-raspy-credit-d2yhs2ud.database.us-east-1.cloud.databricks.com")
    os.environ.setdefault("COMPASS_LAKEBASE_INSTANCE", "compass-lakebase-prov")
    os.environ.setdefault("COMPASS_FM_ENDPOINT", "databricks-claude-sonnet-4-6")
    os.environ.setdefault("COMPASS_SUPERVISOR_ENDPOINT", "mas-2a692b50-endpoint")
    os.environ["COMPASS_AGENT_MODE"] = "full"
    return Settings.from_env()


def _maya() -> UserContext:
    return UserContext(
        user_id="U-MAYA-001",
        email="maya.demo@steelcase-demo.invalid",
        role="channel_mgr",
        region_id="RGN-AMER-EAST",
        default_tier_filter="All",
        dealer_id=None,
    )


def _hero_forfeit_in_text(text: str) -> bool:
    import re

    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", text)]
    return any(HERO_FORFEIT_LO <= n <= HERO_FORFEIT_HI for n in nums)


def main() -> int:
    settings = _settings()
    user = _maya()
    w = WorkspaceClient()
    checks: list[Check] = []

    # --- A3: Genie Utilization & Risk ---
    q_util = "What's my Q4 forfeiture risk?"
    r_util = workers.query_genie(
        w=w, settings=settings, space_id=UTIL_SPACE, message=q_util, user=user
    )
    sql = (r_util.genie.query or "") if r_util.genie else ""
    rows = (r_util.genie.rows or []) if r_util.genie else []
    row_blob = json.dumps(rows, default=str)
    util_ok = (
        r_util.route == "genie"
        and (
            _hero_forfeit_in_text(r_util.content + (sql or "") + row_blob)
            or "forfeiture_risk" in sql.lower()
        )
    )
    checks.append(
        Check(
            "A3 Genie Utilization (forfeiture)",
            util_ok,
            f"route={r_util.route} sql_has_forfeiture={'forfeiture' in sql.lower()} "
            f"rows={len(rows)} content_snip={r_util.content[:120]!r}",
        )
    )

    # --- A3: Genie Marketing & ROI ---
    q_mkt = "Top 5 activities by revenue per co-op dollar in AMER East FY26."
    r_mkt = workers.query_genie(
        w=w, settings=settings, space_id=MKT_SPACE, message=q_mkt, user=user
    )
    mkt_sql = (r_mkt.genie.query or "") if r_mkt.genie else ""
    checks.append(
        Check(
            "A3 Genie Marketing (activity_lift)",
            r_mkt.route == "genie"
            and ("activity_lift" in mkt_sql.lower() or "programmatic" in r_mkt.content.lower()),
            f"route={r_mkt.route} sql_snip={mkt_sql[:160]!r}",
        )
    )

    # --- A2: MAS via compass-supervisor ---
    q_mas = "What is the expected forfeiture for AMER East FY26?"
    r_mas = workers.query_mas(w=w, settings=settings, message=q_mas, user=user)
    checks.append(
        Check(
            "A2 MAS Auto-path (forfeiture)",
            r_mas.route in ("genie", "ka", "tool") and r_mas.route != "error"
            and _hero_forfeit_in_text(r_mas.content),
            f"route={r_mas.route} content_snip={r_mas.content[:120]!r}",
        )
    )

    # --- A2: KA handbook ---
    q_ka = "Can a Silver-tier dealer submit a $25K digital ad claim?"
    r_ka = workers.query_ka(w=w, settings=settings, message=q_ka, user=user)
    checks.append(
        Check(
            "A2 KA (Silver $25K digital ad)",
            r_ka.route == "ka" and len(r_ka.citations) >= 1,
            f"route={r_ka.route} citations={len(r_ka.citations)} content_snip={r_ka.content[:100]!r}",
        )
    )

    print("COMPASS P0 smoke results\n" + "=" * 60)
    failed = 0
    for c in checks:
        mark = "PASS" if c.ok else "FAIL"
        print(f"[{mark}] {c.name}\n       {c.detail}\n")
        if not c.ok:
            failed += 1

    print(json.dumps({"passed": len(checks) - failed, "failed": failed, "total": len(checks)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
