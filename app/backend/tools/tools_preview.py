"""Preview-only tools — used in `lite` mode. No persistence.

Returns the same shapes as the persistent implementations so the frontend
can render preview cards without knowing the mode.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from typing import Any

from ..schemas import NudgeCampaign, SavedView


class PreviewTools:
    def create_nudge_campaign(
        self,
        *,
        user_id: str,
        template_id: str,
        dealer_ids: list[str],
        deadline: date | None,
        notes: str | None,
    ) -> NudgeCampaign:
        h = hashlib.sha256(
            f"{user_id}|{template_id}|{sorted(dealer_ids)}|{deadline}".encode()
        ).hexdigest()[:8]
        return NudgeCampaign(
            campaign_id=str(uuid.uuid4()),
            campaign_code=f"preview-{h}",
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            template_id=template_id,
            deadline=deadline,
            status="Draft",
            notes=notes,
            recipient_count=len(dealer_ids),
        )

    def advance_claim(
        self,
        *,
        user_id: str,
        claim_id: str,
        decision: str,
        note: str | None,
        rejection_code: str | None,
    ) -> dict[str, Any]:
        return {
            "claim_id": claim_id,
            "status": "Approved" if decision == "Approve" else "Rejected",
            "preview_only": True,
            "reviewer_user_id": user_id,
            "decision_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_note": note,
            "rejection_code": rejection_code,
        }

    def save_view(
        self,
        *,
        user_id: str,
        name: str,
        filter_payload: dict[str, Any],
        description: str | None,
        pinned: bool,
    ) -> SavedView:
        return SavedView(
            view_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            filter_payload=filter_payload,
            pinned=pinned,
            created_at=datetime.now(timezone.utc),
        )
