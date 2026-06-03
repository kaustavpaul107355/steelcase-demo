"""Lakebase-backed action tools (standard / full modes).

Writes through to `compass.nudge_campaign` / `nudge_recipient`, `claim_review`,
`saved_view`, and emits an `audit_log` row per call.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..schemas import NudgeCampaign, SavedView


class LakebaseTools:
    def __init__(self, engine: Engine):
        self.engine = engine

    # ---- nudge -----------------------------------------------------

    def create_nudge_campaign(
        self,
        *,
        user_id: str,
        template_id: str,
        dealer_ids: list[str],
        deadline: date | None,
        notes: str | None,
    ) -> NudgeCampaign:
        call_hash = hashlib.sha256(
            f"{user_id}|{sorted(dealer_ids)}|{template_id}|{deadline}".encode()
        ).hexdigest()
        with self.engine.begin() as conn:
            # 5-min idempotency window on Drafts.
            existing = conn.execute(
                text(
                    """
                    SELECT campaign_id, campaign_code, created_at, status, notes
                      FROM compass.nudge_campaign
                     WHERE created_by = :uid
                       AND status = 'Draft'
                       AND dealer_filter_json->>'call_hash' = :h
                       AND created_at > now() - INTERVAL '5 minutes'
                     LIMIT 1
                    """
                ),
                {"uid": user_id, "h": call_hash},
            ).first()
            if existing:
                return NudgeCampaign(
                    campaign_id=str(existing.campaign_id),
                    campaign_code=existing.campaign_code,
                    created_by=user_id,
                    created_at=existing.created_at,
                    template_id=template_id,
                    deadline=deadline,
                    status=existing.status,
                    notes=existing.notes,
                    recipient_count=len(dealer_ids),
                )

            campaign_id = uuid.uuid4()
            short = call_hash[:6]
            campaign_code = (
                f"nudge-{datetime.now(timezone.utc).strftime('%Y%m')}-{short}"
            )
            dealer_filter = {"call_hash": call_hash, "dealer_ids": dealer_ids}
            conn.execute(
                text(
                    """
                    INSERT INTO compass.nudge_campaign
                        (campaign_id, campaign_code, created_by, template_id,
                         dealer_filter_json, deadline, status, notes)
                    VALUES
                        (:id, :code, :uid, :tpl, :df, :ddl, 'Draft', :notes)
                    """
                ),
                {
                    "id": campaign_id,
                    "code": campaign_code,
                    "uid": user_id,
                    "tpl": template_id,
                    "df": json.dumps(dealer_filter),
                    "ddl": deadline,
                    "notes": notes,
                },
            )
            # Recipient stubs — emails resolved from v_dealer if available.
            recipients = conn.execute(
                text(
                    """
                    SELECT dealer_id, dealer_name
                      FROM compass.v_dealer
                     WHERE dealer_id = ANY(:ids)
                    """
                ),
                {"ids": dealer_ids},
            ).fetchall()
            for r in recipients:
                conn.execute(
                    text(
                        """
                        INSERT INTO compass.nudge_recipient
                            (campaign_id, dealer_id, dealer_email, personalization_json, email_status)
                        VALUES
                            (:cid, :did, :email, :pers, 'Pending')
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "cid": campaign_id,
                        "did": r.dealer_id,
                        "email": f"{r.dealer_id.lower()}@example.invalid",
                        "pers": json.dumps({"dealer_name": r.dealer_name}),
                    },
                )

            conn.execute(
                text(
                    """
                    INSERT INTO compass.audit_log
                        (user_id, action, target_type, target_id, payload_json)
                    VALUES (:uid, 'create_nudge_campaign', 'nudge_campaign', :tid, :payload)
                    """
                ),
                {
                    "uid": user_id,
                    "tid": str(campaign_id),
                    "payload": json.dumps(
                        {
                            "template_id": template_id,
                            "deadline": deadline.isoformat() if deadline else None,
                            "recipient_count": len(dealer_ids),
                        }
                    ),
                },
            )

        return NudgeCampaign(
            campaign_id=str(campaign_id),
            campaign_code=campaign_code,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            template_id=template_id,
            deadline=deadline,
            status="Draft",
            notes=notes,
            recipient_count=len(dealer_ids),
        )

    # ---- claim -----------------------------------------------------

    def advance_claim(
        self,
        *,
        user_id: str,
        claim_id: str,
        decision: str,
        note: str | None,
        rejection_code: str | None,
    ) -> dict[str, Any]:
        new_status = "Approved" if decision == "Approve" else "Rejected"
        with self.engine.begin() as conn:
            existing = conn.execute(
                text(
                    "SELECT status FROM compass.claim_review WHERE claim_id = :cid"
                ),
                {"cid": claim_id},
            ).first()
            if existing and existing.status in ("Approved", "Rejected", "PaidStaged"):
                return {
                    "claim_id": claim_id,
                    "status": existing.status,
                    "was_idempotent": True,
                }
            conn.execute(
                text(
                    """
                    UPDATE compass.claim_review
                       SET status = :st,
                           reviewer_user_id = :uid,
                           decision_at = now(),
                           reviewer_note = :note,
                           rejection_code = :rc,
                           updated_at = now()
                     WHERE claim_id = :cid
                    """
                ),
                {
                    "st": new_status,
                    "uid": user_id,
                    "note": note,
                    "rc": rejection_code,
                    "cid": claim_id,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO compass.audit_log
                        (user_id, action, target_type, target_id, payload_json)
                    VALUES (:uid, 'advance_claim', 'claim', :cid, :payload)
                    """
                ),
                {
                    "uid": user_id,
                    "cid": claim_id,
                    "payload": json.dumps(
                        {"decision": decision, "note": note, "rejection_code": rejection_code}
                    ),
                },
            )
        return {"claim_id": claim_id, "status": new_status, "was_idempotent": False}

    # ---- saved view ------------------------------------------------

    def save_view(
        self,
        *,
        user_id: str,
        name: str,
        filter_payload: dict[str, Any],
        description: str | None,
        pinned: bool,
    ) -> SavedView:
        valid = {
            "coop_program_metrics",
            "forfeiture_risk",
            "dealer_performance",
            "claim_lifecycle",
            "activity_lift",
        }
        mv = filter_payload.get("metric_view")
        if mv not in valid:
            raise ValueError(f"filter_payload.metric_view must be one of {valid}; got {mv!r}")
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    INSERT INTO compass.saved_view
                        (user_id, name, description, filter_payload, pinned)
                    VALUES (:uid, :n, :d, :fp, :p)
                    ON CONFLICT (user_id, name) DO UPDATE
                       SET description = EXCLUDED.description,
                           filter_payload = EXCLUDED.filter_payload,
                           pinned = EXCLUDED.pinned,
                           last_used_at = now()
                    RETURNING view_id, created_at, last_used_at
                    """
                ),
                {
                    "uid": user_id,
                    "n": name,
                    "d": description,
                    "fp": json.dumps(filter_payload),
                    "p": pinned,
                },
            ).one()
        return SavedView(
            view_id=str(row.view_id),
            user_id=user_id,
            name=name,
            description=description,
            filter_payload=filter_payload,
            pinned=pinned,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
        )
