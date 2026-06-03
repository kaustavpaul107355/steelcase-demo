"""Action-tool interface — `create_nudge_campaign`, `advance_claim`, `save_view`.

All three modes implement this Protocol. `tools_preview` is the lite default
(no persistence); `tools_lakebase` writes through to `compass.*`.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from ..schemas import NudgeCampaign, SavedView


class ActionTools(Protocol):
    def create_nudge_campaign(
        self,
        *,
        user_id: str,
        template_id: str,
        dealer_ids: list[str],
        deadline: date | None,
        notes: str | None,
    ) -> NudgeCampaign: ...

    def advance_claim(
        self,
        *,
        user_id: str,
        claim_id: str,
        decision: str,
        note: str | None,
        rejection_code: str | None,
    ) -> dict[str, Any]: ...

    def save_view(
        self,
        *,
        user_id: str,
        name: str,
        filter_payload: dict[str, Any],
        description: str | None,
        pinned: bool,
    ) -> SavedView: ...
