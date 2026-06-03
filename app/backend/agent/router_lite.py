"""Lite-mode router — BFF owns intent routing.

Regex on verbs + a few metric-name signals picks Genie vs KA. Falls back to KA
for policy-shaped phrases ("can a Silver dealer..", "is it eligible"). No LLM
classifier on the fast path — keeps the lite tier free of supervisor cost.

If you find this regex set drifting, prefer routing via the (full-mode) MAS
supervisor instead — see `router_full.py`.
"""

from __future__ import annotations

import logging
import re

from databricks.sdk import WorkspaceClient

from ..config import Settings
from ..schemas import RouteHint
from .router import Router, TurnResult, UserContext
from .workers import query_genie, query_ka

log = logging.getLogger(__name__)


_REFUSE_OTHER_REGION = re.compile(
    r"\b(other|another|different)\s+region\b|"
    r"\b(europe|emea|apac|asia)\b",
    re.I,
)
_QUANT_VERBS = re.compile(
    r"\b(how many|count|sum|total|show|list|top \d+|which dealers?|what.*rate|"
    r"average|p50|p90|trend|by region|by tier|forfeit(ure)?|unused|paid|claim cycle)\b",
    re.I,
)
_POLICY_VERBS = re.compile(
    r"\b(eligib|policy|rule|allowed|permitted|why|what.*counts as|brand|pre[- ]?approval|"
    r"how do i submit|deadline|tier .*qualif|reimburs|matrix)\b",
    re.I,
)
_MARKETING_SIGNALS = re.compile(
    r"\b(activity|lift|roi|sell[- ]?through|campaign|programmatic|attribution|revenue per)\b",
    re.I,
)


class LiteRouter:
    """Regex-routed Genie + KA. No persistence."""

    def __init__(self, settings: Settings, w: WorkspaceClient | None = None):
        self.s = settings
        self._w = w  # lazy — don't auth at import time

    @property
    def w(self) -> WorkspaceClient:
        if self._w is None:
            self._w = WorkspaceClient()
        return self._w

    def route(
        self,
        message: str,
        user: UserContext,
        route_hint: RouteHint | None = None,
        session_id: str | None = None,  # ignored — lite has no memory-aware routing
    ) -> TurnResult:
        if route_hint == "ka":
            return query_ka(w=self.w, settings=self.s, message=message, user=user)
        if route_hint == "genie_util":
            return query_genie(
                w=self.w, settings=self.s,
                space_id=self.s.genie_space_util_risk_id,
                message=message, user=user,
            )
        if route_hint == "genie_marketing":
            return query_genie(
                w=self.w, settings=self.s,
                space_id=self.s.genie_space_marketing_id,
                message=message, user=user,
            )

        if user.role == "channel_mgr" and _REFUSE_OTHER_REGION.search(message):
            return TurnResult(
                route="refuse",
                content=(
                    f"Your view is scoped to {user.region_id or 'your region'}. "
                    "Ask about that region, or reach out to a director for cross-region access."
                ),
                citations=[],
            )

        if _QUANT_VERBS.search(message):
            space_id = (
                self.s.genie_space_marketing_id
                if _MARKETING_SIGNALS.search(message)
                else self.s.genie_space_util_risk_id
            )
            return query_genie(
                w=self.w, settings=self.s,
                space_id=space_id, message=message, user=user,
            )
        if _POLICY_VERBS.search(message):
            return query_ka(w=self.w, settings=self.s, message=message, user=user)
        return query_ka(w=self.w, settings=self.s, message=message, user=user)


def build_router(settings: Settings) -> Router:
    return LiteRouter(settings)
