"""Router interface — `route(turn, user) -> TurnResult`.

All three modes (lite / standard / full) implement this interface so the rest
of the backend doesn't branch on mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Protocol

from ..schemas import Citation, GenieResult, RouteHint


@dataclass
class TurnResult:
    route: Literal["genie", "ka", "tool", "refuse", "error"]
    content: str
    citations: list[Citation]
    genie: GenieResult | None = None
    tool_preview: dict[str, Any] | None = None


@dataclass
class UserContext:
    """Per-request user identity passed into the router (used for scoping)."""

    user_id: str
    email: str
    role: str
    region_id: str | None
    default_tier_filter: str | None
    dealer_id: str | None


class Router(Protocol):
    def route(
        self,
        message: str,
        user: UserContext,
        route_hint: Optional[RouteHint] = None,
        session_id: Optional[str] = None,
    ) -> TurnResult: ...
