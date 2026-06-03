"""Full-mode router — hybrid Action-Gate + MAS read-side.

Phase 6 hybrid topology (demo-design.md §12):
 - The embedded supervisor (`databricks-claude-sonnet-4-6`) acts as an
   *action gate*: it only decides whether the turn is a question or one of the
   three write actions.
 - Read-side routing across the two Genie spaces + handbook KA is owned by the
   `compass-supervisor` Agent Bricks MAS (`workers.query_mas`).
 - Action tools (`advance_claim` / `create_nudge_campaign` / `save_view`) stay
   in this in-process router so the UI gets a `tool_preview` Confirm card
   before the BFF writes to Lakebase — preserves the §13.4 audit gate that
   MAS cannot today.

If `route_hint` is set (the UI's per-tab pins), both supervisors are bypassed
and the underlying Genie/KA worker is called directly. The action gate only
runs when the user is on the "Auto" tab.
"""

from __future__ import annotations

import logging
from typing import Any

from databricks.sdk import WorkspaceClient

from ..config import Settings
from ..schemas import RouteHint
from ..store.memory import Memory
from .router import Router, TurnResult, UserContext
from .supervisor import SupervisorAgent
from .workers import query_genie, query_ka, query_mas

log = logging.getLogger(__name__)


_QUERY_TOOL = "query"
_ACTION_TOOLS = {"advance_claim", "create_nudge_campaign", "save_view"}


class FullRouter:
    """Hybrid router: embedded action-gate + MAS for read-side."""

    def __init__(
        self,
        settings: Settings,
        memory: Memory | None = None,
        w: WorkspaceClient | None = None,
    ):
        self.s = settings
        self.memory = memory
        self._w = w
        if not settings.supervisor_endpoint:
            raise RuntimeError(
                "FullRouter requires COMPASS_SUPERVISOR_ENDPOINT (the compass-supervisor MAS endpoint)."
            )
        if not settings.fm_endpoint:
            raise RuntimeError(
                "FullRouter requires COMPASS_FM_ENDPOINT (the action-gate foundation model)."
            )
        self.supervisor = SupervisorAgent(settings, endpoint=settings.fm_endpoint, w=w)

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
        session_id: str | None = None,
    ) -> TurnResult:
        # Tab-pinned routing — bypass the supervisor entirely.
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

        # Auto — ask the action-gate supervisor.
        recent = (
            self.memory.recent_turns(session_id, limit=8)
            if self.memory and session_id
            else None
        )
        try:
            decision = self.supervisor.decide(message, user, recent_turns=recent)
        except Exception as e:
            log.exception("action-gate supervisor call failed")
            return TurnResult(
                route="error",
                content=f"Supervisor call failed: {e}",
                citations=[],
            )

        tool = decision.tool_name
        args = decision.tool_args or {}

        if tool == _QUERY_TOOL:
            question = args.get("question") or message
            return query_mas(w=self.w, settings=self.s, message=question, user=user)

        if tool == "refuse":
            reason = args.get("reason") or "That request is outside your governance scope."
            return TurnResult(route="refuse", content=reason, citations=[])

        if tool in _ACTION_TOOLS:
            # Don't write to Lakebase yet — the UI shows a confirmation card.
            # The existing /api/approvals/{id}/advance, /api/nudge-campaigns,
            # /api/saved-views endpoints execute on user confirm.
            content = decision.content or _action_preview_summary(tool, args)
            return TurnResult(
                route="tool",
                content=content,
                citations=[],
                tool_preview={"tool": tool, "args": args},
            )

        # Plain text fallback — model didn't pick a tool. Treat as a question and
        # forward to the MAS so the user still gets a routed answer.
        return query_mas(w=self.w, settings=self.s, message=message, user=user)


def _action_preview_summary(tool: str, args: dict[str, Any]) -> str:
    """One-line description shown in the chat bubble next to the preview card."""
    if tool == "advance_claim":
        decision = args.get("decision") or "?"
        claim = args.get("claim_id") or "?"
        return f"I'd like to {decision.lower()} {claim} — confirm?"
    if tool == "create_nudge_campaign":
        n = len(args.get("dealer_ids") or [])
        tpl = args.get("template_id") or "?"
        return f"I'd like to draft a {tpl} nudge for {n} dealer(s) — confirm?"
    if tool == "save_view":
        name = args.get("name") or "?"
        return f"I'd like to save this view as '{name}' — confirm?"
    return "Confirm to execute."


def build_router(settings: Settings, memory: Memory | None = None) -> Router:
    return FullRouter(settings, memory=memory)
