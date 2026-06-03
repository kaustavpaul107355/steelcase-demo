"""Databricks Apps forwards the OAuth user identity in request headers.

Locally (no headers), we fall back to `COMPASS_DEV_USER_EMAIL` so the app is
boot-able for inner-loop dev. The fallback never short-circuits in production
because the FE proxy always sets X-Forwarded-Email.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .agent.router import UserContext
from .config import Settings


@dataclass
class ResolvedUser:
    user: UserContext
    display_name: str


_GUEST_FALLBACK = ResolvedUser(
    user=UserContext(
        user_id="guest",
        email="guest@local",
        role="guest",
        region_id=None,
        default_tier_filter=None,
        dealer_id=None,
    ),
    display_name="Guest (no Lakebase)",
)


def resolve_user(
    req: Request,
    settings: Settings,
    engine: Engine | None,
) -> ResolvedUser:
    forwarded_email = (
        req.headers.get("X-Forwarded-Email")
        or req.headers.get("X-Forwarded-Preferred-Username")
        or settings.dev_user_email
    )
    # Demo-only persona override. Gated by COMPASS_ALLOW_PERSONA_SWITCH so a
    # customer-handoff app cannot have its identity spoofed by a header.
    impersonate = req.headers.get("X-Compass-As-User")
    email = impersonate if (impersonate and settings.allow_persona_switch) else forwarded_email

    if engine is None:
        # Lite mode — derive a reasonable persona from the email so the persona
        # switcher renders correct chips and the home view uses the right role.
        # Mirrors lakebase/seed-data.sql so screenshots match live behaviour.
        e = email.lower()
        if "maya" in e or "kaustav" in e:
            role, region, dealer = "channel_mgr", "RGN-AMER-EAST", None
        elif "eliot" in e:
            role, region, dealer = "director", None, None
        elif "renske" in e:
            role, region, dealer = "rmd", "RGN-EMEA-NORTH", None
        elif "jordan" in e or "finance" in e:
            role, region, dealer = "finance", None, None
        elif "priya" in e or "pivot-workplace" in e:
            role, region, dealer = "dealer", "RGN-AMER-EAST", "D-04711"
        else:
            role, region, dealer = "channel_mgr", "RGN-AMER-EAST", None
        return ResolvedUser(
            user=UserContext(
                user_id=email,
                email=email,
                role=role,
                region_id=region,
                default_tier_filter="All" if role != "dealer" else None,
                dealer_id=dealer,
            ),
            display_name=email.split("@")[0].replace(".", " ").title(),
        )

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, display_name, role, region_id,
                       default_tier_filter, dealer_id
                  FROM compass.app_user
                 WHERE email = :email
                """
            ),
            {"email": email},
        ).first()
    if not row:
        return _GUEST_FALLBACK
    return ResolvedUser(
        user=UserContext(
            user_id=row.user_id,
            email=row.email,
            role=row.role,
            region_id=row.region_id,
            default_tier_filter=row.default_tier_filter,
            dealer_id=row.dealer_id,
        ),
        display_name=row.display_name,
    )
