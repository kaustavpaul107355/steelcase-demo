"""COMPASS action-gate supervisor — embedded LLM that decides 'ask vs do'.

Hybrid Phase 6 (per demo-design.md §12): the heavy read-side routing between
Genie spaces and the Knowledge Assistant is owned by the `compass-supervisor`
MAS (Agent Bricks). This embedded supervisor only decides whether the turn is:

  - a `query` → forward to the MAS endpoint (Genie/KA routing happens there)
  - an action (`advance_claim` / `create_nudge_campaign` / `save_view`) →
    return a `tool_preview` so the UI shows a Confirm card before the BFF
    writes to Lakebase (demo-design.md §13.4 audit gate)
  - a `refuse` → governance refusal (out-of-region / cross-dealer)

Keeping the action tools in this in-process supervisor is what lets us
preserve the Confirm-before-write UX; MAS executes tools server-side and
returns a final assistant turn, which loses the preview gate.

Flow per turn:
1. `decide(message, user, recent_turns)` — single LLM call to the foundation
   model with a 5-tool definition list. The model returns one tool_call.
2. The full-mode router executes the chosen tool:
   - `query` → `workers.query_mas` (forward to the MAS serving endpoint).
   - `advance_claim` / `create_nudge_campaign` / `save_view` → `tool_preview`.
   - `refuse` → governance refusal turn.
3. If no tool is chosen, return the model's plain text (fallback only).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from databricks.sdk import WorkspaceClient

from ..config import Settings
from .router import UserContext

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are COMPASS, the Co-op Program Analytics Agent for Steelcase.

Your job is to decide whether the user wants to ASK or DO something, and call the right tool.
You do NOT answer in prose; you call exactly one tool. The orchestrator runs the tool.

A downstream Multi-Agent Supervisor (Agent Bricks) handles all read-side routing between
the utilization/risk Genie space, the marketing Genie space, and the co-op handbook
Knowledge Assistant. You do NOT pick which one — you only decide that the turn is a
question and forward it via `query`.

Available tools:
- query(question): Forward a question (quantitative or policy) to the COMPASS read-side
  supervisor. Use this for anything the user is ASKING: utilization, forfeiture risk,
  ROI, lift, campaign effectiveness, eligibility, policy, how-to. The supervisor picks
  the right Genie space or KA.
- advance_claim(claim_id, decision, note, rejection_code): Approve or reject a pending
  claim. `decision` is "Approve" or "Reject". `rejection_code` is required when rejecting
  (one of: MISSING_PREAPPROVAL, TIER_INELIGIBLE, OFF_BRAND, OUT_OF_REGION, DOC_INCOMPLETE,
  DOUBLE_DIP, OTHER).
- create_nudge_campaign(dealer_ids, template_id, deadline, notes): Draft an outreach
  campaign to one or more dealers. Templates: "Q4_REMINDER", "FORFEITURE_WARNING",
  "TIER_UPGRADE_AVAILABLE". `deadline` is YYYY-MM-DD.
- save_view(name, filter_payload, description, pinned): Save a metric-view filter set
  for later. `filter_payload` is the JSON Genie produced (or a sketch of it).
- refuse(reason): Decline politely. Use when the user (role=channel_mgr) asks for data
  outside their region, or when a dealer asks about another dealer.

Routing rules:
1. If the user is ASKING for data, a number, a rule, an eligibility check, or a how-to →
   call `query` and pass the user's question.
2. If the user is asking you to DO something — approve/reject a claim, draft a nudge
   campaign, save a view → call the matching action tool.
3. If a channel_mgr asks about another region (EMEA / APAC when their region is
   AMER-EAST) → `refuse`.
4. If a dealer asks about another dealer → `refuse`.

Prefer one tool per turn. Never wrap a tool call in extra prose."""


# OpenAI-shaped tool definitions the LLM sees.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query",
            "description": "Forward a quantitative or policy question to the COMPASS read-side supervisor (MAS). The MAS chooses between util/risk Genie, marketing Genie, and the handbook KA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The user's question, rephrased if helpful for the downstream supervisor."},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "advance_claim",
            "description": "Approve or reject a pending claim.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "e.g. CL-FY26-009862"},
                    "decision": {"type": "string", "enum": ["Approve", "Reject"]},
                    "note": {"type": "string"},
                    "rejection_code": {
                        "type": "string",
                        "enum": ["MISSING_PREAPPROVAL", "TIER_INELIGIBLE", "OFF_BRAND",
                                 "OUT_OF_REGION", "DOC_INCOMPLETE", "DOUBLE_DIP", "OTHER"],
                    },
                },
                "required": ["claim_id", "decision"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_nudge_campaign",
            "description": "Draft an outreach campaign to one or more dealers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dealer_ids": {"type": "array", "items": {"type": "string"}},
                    "template_id": {
                        "type": "string",
                        "enum": ["Q4_REMINDER", "FORFEITURE_WARNING", "TIER_UPGRADE_AVAILABLE"],
                    },
                    "deadline": {"type": "string", "description": "YYYY-MM-DD"},
                    "notes": {"type": "string"},
                },
                "required": ["dealer_ids", "template_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_view",
            "description": "Save a metric-view filter set for later recall.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "filter_payload": {"type": "object"},
                    "description": {"type": "string"},
                    "pinned": {"type": "boolean"},
                },
                "required": ["name", "filter_payload"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refuse",
            "description": "Politely refuse a request that's outside the user's governance scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                },
                "required": ["reason"],
            },
        },
    },
]


@dataclass
class SupervisorDecision:
    """Result of one supervisor LLM call."""
    tool_name: str | None        # e.g. "query_util_risk", "advance_claim", or None for plain text
    tool_args: dict[str, Any]    # parsed JSON arguments
    content: str | None          # any plain text the model returned alongside the tool call
    raw_response: dict[str, Any] # for debugging / MLflow span attribution


class SupervisorAgent:
    """Embedded LLM-driven supervisor.

    Calls the workspace foundation model endpoint with the routing system
    prompt and tool definitions. Returns a structured decision the
    `router_full.FullRouter` can act on.
    """

    def __init__(
        self,
        settings: Settings,
        endpoint: str,
        w: WorkspaceClient | None = None,
    ):
        self.s = settings
        self.endpoint = endpoint
        self._w = w

    @property
    def w(self) -> WorkspaceClient:
        if self._w is None:
            self._w = WorkspaceClient()
        return self._w

    def _user_scope_message(self, user: UserContext) -> str:
        bits = [f"role={user.role}"]
        if user.region_id:
            bits.append(f"region={user.region_id}")
        if user.dealer_id:
            bits.append(f"dealer_id={user.dealer_id}")
        if user.default_tier_filter:
            bits.append(f"default_tier_filter={user.default_tier_filter}")
        return f"User scope: {', '.join(bits)}."

    def decide(
        self,
        message: str,
        user: UserContext,
        recent_turns: list[dict[str, str]] | None = None,
    ) -> SupervisorDecision:
        """One LLM call. Returns the parsed tool_call (or content fallback)."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": self._user_scope_message(user)},
        ]
        if recent_turns:
            messages.extend(recent_turns)
        messages.append({"role": "user", "content": message})

        cfg = self.w.config
        host = cfg.host.rstrip("/")
        url = f"{host}/serving-endpoints/{self.endpoint}/invocations"
        headers = cfg.authenticate()
        headers.setdefault("Content-Type", "application/json")
        payload = {
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
            "temperature": 0.0,
            "max_tokens": 512,
        }
        log.debug("supervisor request → %s", self.endpoint)
        resp = httpx.post(url, headers=headers, json=payload, timeout=45.0)
        resp.raise_for_status()
        data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            first = tool_calls[0]
            fn = first.get("function") or {}
            name = fn.get("name")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                log.warning("supervisor tool_call had invalid JSON args: %r", raw_args)
                args = {}
            return SupervisorDecision(
                tool_name=name,
                tool_args=args,
                content=msg.get("content"),
                raw_response=data,
            )

        return SupervisorDecision(
            tool_name=None,
            tool_args={},
            content=msg.get("content") or "",
            raw_response=data,
        )
