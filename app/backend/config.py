"""COMPASS app configuration — env-var driven, mode-aware.

A single `COMPASS_AGENT_MODE` env var (`lite` | `standard` | `full`) decides
which downstream phases the app expects to be live, and which env vars are
*required*. Required vars for higher modes are silently ignored in lower
modes so the same image can boot in any configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["lite", "standard", "full"]


class ConfigError(RuntimeError):
    """Raised at startup when the configured mode lacks its required env vars."""


# Always-required env vars (any mode).
_ALWAYS_REQUIRED = [
    "COMPASS_GENIE_SPACE_UTIL_RISK_ID",
    "COMPASS_GENIE_SPACE_MARKETING_ID",
    "COMPASS_KA_ENDPOINT",
    "COMPASS_WAREHOUSE_ID",
]

# Additionally required for standard / full (Lakebase-backed).
# COMPASS_LAKEBASE_USER is intentionally optional: when absent, main.py derives
# it from the WorkspaceClient identity (CLI user locally, App SP in prod).
_LAKEBASE_REQUIRED = [
    "COMPASS_LAKEBASE_HOST",
    "COMPASS_LAKEBASE_INSTANCE",
]

# Additionally required for full (hybrid action-gate + MAS).
# Full mode needs BOTH:
#  - COMPASS_SUPERVISOR_ENDPOINT — the `compass-supervisor` Agent Bricks MAS
#    endpoint that routes read-side queries between Genie spaces + the KA.
#  - COMPASS_FM_ENDPOINT — a foundation-model endpoint (e.g.
#    databricks-claude-sonnet-4-6) that powers the embedded action-gate
#    supervisor (decides ask-vs-do and emits tool_preview cards).
_FULL_REQUIRED = [
    "COMPASS_SUPERVISOR_ENDPOINT",
    "COMPASS_FM_ENDPOINT",
]


@dataclass(frozen=True)
class Settings:
    mode: Mode

    genie_space_util_risk_id: str
    genie_space_marketing_id: str
    ka_endpoint: str
    warehouse_id: str

    lakebase_host: str | None
    lakebase_db: str
    lakebase_instance: str | None
    lakebase_user: str | None

    supervisor_endpoint: str | None
    fm_endpoint: str | None
    mlflow_experiment_id: str | None

    # Demo defaults — overridable via env. Used by the BFF to pick a "current user"
    # when running locally without OAuth headers.
    dev_user_email: str = "maya.demo@steelcase-demo.invalid"

    # When true, accept X-Compass-As-User header and switch the resolved
    # identity to that email. Demo-only; off in customer hand-off configs.
    allow_persona_switch: bool = False

    enabled_features: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        mode: Mode = os.environ.get("COMPASS_AGENT_MODE", "lite").lower()  # type: ignore[assignment]
        if mode not in ("lite", "standard", "full"):
            raise ConfigError(f"COMPASS_AGENT_MODE must be lite|standard|full, got {mode!r}")

        required = list(_ALWAYS_REQUIRED)
        if mode in ("standard", "full"):
            required.extend(_LAKEBASE_REQUIRED)
        if mode == "full":
            required.extend(_FULL_REQUIRED)

        missing = [v for v in required if not os.environ.get(v)]
        if missing:
            raise ConfigError(
                f"Mode {mode!r} requires env vars: {', '.join(missing)}"
            )

        return cls(
            mode=mode,
            genie_space_util_risk_id=os.environ["COMPASS_GENIE_SPACE_UTIL_RISK_ID"],
            genie_space_marketing_id=os.environ["COMPASS_GENIE_SPACE_MARKETING_ID"],
            ka_endpoint=os.environ["COMPASS_KA_ENDPOINT"],
            warehouse_id=os.environ["COMPASS_WAREHOUSE_ID"],
            lakebase_host=os.environ.get("COMPASS_LAKEBASE_HOST"),
            lakebase_db=os.environ.get("COMPASS_LAKEBASE_DB", "databricks_postgres"),
            lakebase_instance=os.environ.get("COMPASS_LAKEBASE_INSTANCE"),
            lakebase_user=os.environ.get("COMPASS_LAKEBASE_USER"),
            supervisor_endpoint=os.environ.get("COMPASS_SUPERVISOR_ENDPOINT"),
            fm_endpoint=os.environ.get("COMPASS_FM_ENDPOINT"),
            mlflow_experiment_id=os.environ.get("COMPASS_MLFLOW_EXPERIMENT_ID"),
            dev_user_email=os.environ.get(
                "COMPASS_DEV_USER_EMAIL", "maya.demo@steelcase-demo.invalid"
            ),
            allow_persona_switch=os.environ.get(
                "COMPASS_ALLOW_PERSONA_SWITCH", ""
            ).lower() in ("1", "true", "yes"),
            enabled_features=_features_for_mode(mode),
        )


def _features_for_mode(mode: Mode) -> dict[str, bool]:
    """Drives the frontend's tab visibility via /api/config."""
    return {
        "chat": True,
        "saved_views": True,
        "saved_views_persistent": mode in ("standard", "full"),
        "approvals": mode in ("standard", "full"),
        "nudges": mode in ("standard", "full"),
        "agent_routing": mode == "full",
        "preview_only_actions": mode in ("lite", "standard"),
    }
