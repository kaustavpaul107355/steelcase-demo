"""Pydantic models shared across routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# /api/me, /api/config
# ---------------------------------------------------------------------


class MeResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: Literal["channel_mgr", "rmd", "director", "finance", "dealer", "guest"]
    region_id: str | None
    default_tier_filter: str | None
    dealer_id: str | None
    mode: Literal["lite", "standard", "full"]


class ConfigResponse(BaseModel):
    mode: Literal["lite", "standard", "full"]
    features: dict[str, bool]
    genie_spaces: dict[str, str]
    ka_endpoint: str
    allow_persona_switch: bool = False


# ---------------------------------------------------------------------
# /api/personas
# ---------------------------------------------------------------------


class Persona(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: Literal["channel_mgr", "rmd", "director", "finance", "dealer", "guest"]
    region_id: str | None = None
    dealer_id: str | None = None


# ---------------------------------------------------------------------
# /api/home (role-shaped KPI payload)
# ---------------------------------------------------------------------


class HomeTile(BaseModel):
    key: str
    label: str
    value: float | int | str | None = None
    sub_label: str | None = None
    format: Literal["currency", "percent", "count", "text"] = "text"
    intent: Literal["neutral", "good", "warn", "bad"] = "neutral"


class HomeRow(BaseModel):
    primary: str
    secondary: str | None = None
    metric: str | None = None
    intent: Literal["neutral", "good", "warn", "bad"] = "neutral"


class HomeResponse(BaseModel):
    role: str
    scope_label: str
    headline: str
    tiles: list[HomeTile] = []
    rows: list[HomeRow] = []


# ---------------------------------------------------------------------
# /api/chat
# ---------------------------------------------------------------------


RouteHint = Literal["auto", "genie_util", "genie_marketing", "ka"]


class ChatTurnRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=8000)
    route_hint: RouteHint | None = None


class Citation(BaseModel):
    """One KA corpus citation surfaced to the UI."""

    doc_id: str
    section: str | None = None
    excerpt: str | None = None


class GenieResult(BaseModel):
    """A Genie response shape that the UI can render as a 'Show metric & SQL' disclosure."""

    space_id: str
    query: str | None = None
    rows: list[dict[str, Any]] | None = None
    columns: list[str] | None = None
    description: str | None = None


class ChatTurnResponse(BaseModel):
    session_id: str
    turn_index: int
    route: Literal["genie", "ka", "tool", "refuse", "error"]
    content: str
    citations: list[Citation] = []
    genie: GenieResult | None = None
    tool_preview: dict[str, Any] | None = None
    trace_id: str | None = None
    latency_ms: int | None = None


# ---------------------------------------------------------------------
# /api/approvals
# ---------------------------------------------------------------------


class ClaimReview(BaseModel):
    claim_id: str
    dealer_id: str
    dealer_name: str | None = None
    status: Literal["Pending", "Approved", "Rejected", "PaidStaged"]
    reviewer_user_id: str | None = None
    decision_at: datetime | None = None
    reviewer_note: str | None = None
    rejection_code: str | None = None
    brand_check_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AdvanceClaimRequest(BaseModel):
    decision: Literal["Approve", "Reject"]
    note: str | None = None
    rejection_code: str | None = None


# ---------------------------------------------------------------------
# /api/nudge-campaigns
# ---------------------------------------------------------------------


class NudgeCampaignCreate(BaseModel):
    template_id: str
    dealer_ids: list[str]
    deadline: date | None = None
    notes: str | None = None


class NudgeCampaign(BaseModel):
    campaign_id: str
    campaign_code: str | None = None
    created_by: str
    created_at: datetime
    template_id: str
    deadline: date | None = None
    status: Literal["Draft", "Queued", "Sent", "Cancelled"]
    notes: str | None = None
    recipient_count: int = 0


# ---------------------------------------------------------------------
# /api/saved-views
# ---------------------------------------------------------------------


class SavedView(BaseModel):
    view_id: str
    user_id: str
    name: str
    description: str | None = None
    filter_payload: dict[str, Any]
    pinned: bool = False
    created_at: datetime | None = None
    last_used_at: datetime | None = None


class SavedViewUpsert(BaseModel):
    name: str
    description: str | None = None
    filter_payload: dict[str, Any]
    pinned: bool = False
