"""COMPASS app — FastAPI backend.

Mode is selected at import time via `COMPASS_AGENT_MODE`. The router, action-tool
implementation, and memory store are wired once at startup. Routes are
mode-agnostic; they fail with `feature_disabled_in_mode_<mode>` when called
outside the mode they support.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .auth import resolve_user
from .config import Settings
from .schemas import (
    AdvanceClaimRequest,
    ChatTurnRequest,
    ChatTurnResponse,
    ClaimReview,
    ConfigResponse,
    HomeResponse,
    MeResponse,
    NudgeCampaign,
    NudgeCampaignCreate,
    Persona,
    SavedView,
    SavedViewUpsert,
)
from .store.memory import TurnRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("compass")


# ---------------------------------------------------------------------
# Startup wiring
# ---------------------------------------------------------------------

settings = Settings.from_env()
log.info("Booting COMPASS app in mode=%s", settings.mode)

# Engine — only built when we need Lakebase.
engine: Engine | None = None
if settings.mode in ("standard", "full"):
    from .lakebase_token import LakebaseTokenManager, make_engine

    manager = LakebaseTokenManager(instance=settings.lakebase_instance)  # type: ignore[arg-type]
    lakebase_user = settings.lakebase_user
    if not lakebase_user:
        # Derive from the workspace identity calling generate_database_credential.
        # CLI user locally; App SP UUID in production.
        lakebase_user = manager._w.current_user.me().user_name
        log.info("COMPASS_LAKEBASE_USER unset; resolved to %s from WorkspaceClient", lakebase_user)
    engine = make_engine(
        host=settings.lakebase_host,  # type: ignore[arg-type]
        database=settings.lakebase_db,
        user=lakebase_user,  # type: ignore[arg-type]
        manager=manager,
    )

# Memory.
if engine is not None:
    from .store.memory_lakebase import LakebaseMemory

    memory = LakebaseMemory(engine)
else:
    from .store.memory_ephemeral import EphemeralMemory

    memory = EphemeralMemory()

# Action tools.
if engine is not None:
    from .tools.tools_lakebase import LakebaseTools

    tools = LakebaseTools(engine)
else:
    from .tools.tools_preview import PreviewTools

    tools = PreviewTools()

# Router.
if settings.mode == "full":
    from .agent.router_full import build_router as _build_full

    router = _build_full(settings, memory=memory)
else:
    from .agent.router_lite import build_router as _build_lite

    router = _build_lite(settings)

# MLflow tracing — optional. We gate the import so the app boots without mlflow installed.
_mlflow = None
if settings.mlflow_experiment_id:
    try:
        import mlflow as _mlflow_mod

        # Databricks Apps runtime auto-sets MLFLOW_TRACKING_URI; for local dev
        # we point at the workspace explicitly so we don't fall back to file-store.
        if not os.environ.get("MLFLOW_TRACKING_URI"):
            _mlflow_mod.set_tracking_uri("databricks")
        _mlflow_mod.set_experiment(experiment_id=settings.mlflow_experiment_id)
        _mlflow = _mlflow_mod
        log.info("MLflow tracing enabled → experiment %s", settings.mlflow_experiment_id)
    except Exception:
        log.exception("MLflow setup failed (continuing without tracing)")


@contextmanager
def _maybe_span(name: str, attributes: dict[str, Any] | None = None):
    """Use an MLflow span if MLflow is configured; otherwise no-op."""
    if _mlflow is None:
        yield None
        return
    with _mlflow.start_span(name=name) as span:
        if attributes:
            span.set_attributes({k: v for k, v in attributes.items() if v is not None})
        yield span


# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------

app = FastAPI(title="COMPASS Co-op Program Agent", version="0.7.0")


@app.on_event("startup")
def _prewarm_warehouse():
    """Fire a no-op SELECT at the SQL warehouse so the first Genie call doesn't pay cold start."""
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient()
        w.statement_execution.execute_statement(
            warehouse_id=settings.warehouse_id,
            statement="SELECT 1",
            wait_timeout="10s",
        )
        log.info("Pre-warm SQL warehouse OK")
    except Exception as e:
        log.warning("Pre-warm warehouse skipped: %s", e)

# Dev-only CORS (Vite dev server). Databricks Apps serves frontend + backend
# from the same origin, so this is a no-op in prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_lakebase():
    if engine is None:
        raise HTTPException(
            status_code=404,
            detail=f"feature_disabled_in_mode_{settings.mode}",
        )


# Per-request user resolution.
def get_user(req: Request):
    return resolve_user(req, settings, engine)


# ---------------------------------------------------------------------
# /api/me, /api/config, healthz
# ---------------------------------------------------------------------


@app.get("/healthz")
def healthz():
    return {"ok": True, "mode": settings.mode}


@app.get("/api/me", response_model=MeResponse)
def me(req: Request):
    r = resolve_user(req, settings, engine)
    return MeResponse(
        user_id=r.user.user_id,
        email=r.user.email,
        display_name=r.display_name,
        role=r.user.role,  # type: ignore[arg-type]
        region_id=r.user.region_id,
        default_tier_filter=r.user.default_tier_filter,
        dealer_id=r.user.dealer_id,
        mode=settings.mode,
    )


@app.get("/api/config", response_model=ConfigResponse)
def config():
    return ConfigResponse(
        mode=settings.mode,
        features=settings.enabled_features,
        genie_spaces={
            "utilization_and_risk": settings.genie_space_util_risk_id,
            "marketing_effectiveness": settings.genie_space_marketing_id,
        },
        ka_endpoint=settings.ka_endpoint,
        allow_persona_switch=settings.allow_persona_switch,
    )


@app.get("/api/personas", response_model=list[Persona])
def personas():
    """Return the seeded demo personas the UI can impersonate.

    Always reads from Lakebase in standard/full; returns a static list
    matching `lakebase/seed-data.sql` in lite. Order is fixed so the UI
    selector is stable across reloads.
    """
    if engine is not None:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT user_id, email, display_name, role, region_id, dealer_id
                      FROM compass.app_user
                     ORDER BY CASE role
                                WHEN 'channel_mgr' THEN 1
                                WHEN 'director'    THEN 2
                                WHEN 'rmd'         THEN 3
                                WHEN 'finance'     THEN 4
                                WHEN 'dealer'      THEN 5
                                ELSE 9 END,
                              display_name
                    """
                )
            ).mappings().fetchall()
        return [Persona(**dict(r)) for r in rows]
    # Lite mode — mirror the seed file so the switcher still works for screenshots.
    return [
        Persona(user_id="U-MAYA-001",   email="maya.demo@steelcase-demo.invalid",
                display_name="Maya Chen",     role="channel_mgr", region_id="RGN-AMER-EAST"),
        Persona(user_id="U-KAUSTAV-001",email="kaustav.paul@databricks.com",
                display_name="Kaustav Paul",  role="channel_mgr", region_id="RGN-AMER-EAST"),
        Persona(user_id="U-ELIOT-001",  email="eliot.demo@steelcase-demo.invalid",
                display_name="Eliot Vargas",  role="director"),
        Persona(user_id="U-RMD-EM-001", email="renske.demo@steelcase-demo.invalid",
                display_name="Renske de Boer",role="rmd",         region_id="RGN-EMEA-NORTH"),
        Persona(user_id="U-FIN-001",    email="jordan.demo@steelcase-demo.invalid",
                display_name="Jordan Patel",  role="finance"),
        Persona(user_id="U-PRIYA-001",  email="priya.demo@pivot-workplace.invalid",
                display_name="Priya Shah",    role="dealer",
                region_id="RGN-AMER-EAST",    dealer_id="D-04711"),
    ]


@app.get("/api/home", response_model=HomeResponse)
def home(req: Request):
    from databricks.sdk import WorkspaceClient

    from .home import build_home

    r = resolve_user(req, settings, engine)
    try:
        w = WorkspaceClient()
    except Exception:
        log.exception("WorkspaceClient init failed for /api/home")
        w = None
    return build_home(r.user, settings, engine, w)


# ---------------------------------------------------------------------
# /api/session/latest
# ---------------------------------------------------------------------


@app.get("/api/session/latest")
def session_latest(req: Request):
    r = resolve_user(req, settings, engine)
    sid = memory.latest_session(r.user.user_id)
    return {"session_id": sid}


# ---------------------------------------------------------------------
# /api/chat
# ---------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatTurnResponse)
def chat(req: Request, body: ChatTurnRequest):
    r = resolve_user(req, settings, engine)
    sid = memory.get_or_create_session(r.user.user_id, body.session_id)

    started = time.monotonic()
    trace_id: str | None = None
    with _maybe_span(
        "supervisor.turn",
        {
            "compass.mode": settings.mode,
            "compass.session_id": sid,
            "user.email": r.user.email,
            "user.role": r.user.role,
            "user.region": r.user.region_id or "",
        },
    ) as span:
        if _mlflow is not None:
            try:
                trace_id = _mlflow.get_current_active_span().trace_id  # type: ignore[union-attr]
            except Exception:
                trace_id = None
        result = router.route(
            body.message, r.user, route_hint=body.route_hint, session_id=sid,
        )
        if span is not None:
            try:
                span.set_attribute("tool.routed", result.route)
                if body.route_hint:
                    span.set_attribute("compass.route_hint", body.route_hint)
            except Exception:
                pass

    latency_ms = int((time.monotonic() - started) * 1000)
    user_idx = memory.append_turn(
        sid,
        TurnRecord(turn_index=0, role="user", content=body.message),
    )
    assistant_idx = memory.append_turn(
        sid,
        TurnRecord(
            turn_index=0,
            role="assistant",
            content=result.content,
            trace_id=trace_id,
            latency_ms=latency_ms,
        ),
    )
    return ChatTurnResponse(
        session_id=sid,
        turn_index=assistant_idx,
        route=result.route,
        content=result.content,
        citations=result.citations,
        genie=result.genie,
        tool_preview=result.tool_preview,
        trace_id=trace_id,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------
# /api/approvals
# ---------------------------------------------------------------------


@app.get("/api/approvals")
def approvals_list(req: Request):
    _require_lakebase()
    r = resolve_user(req, settings, engine)
    with engine.connect() as conn:  # type: ignore[union-attr]
        rows = conn.execute(
            text(
                """
                SELECT cr.claim_id, cr.dealer_id, vd.dealer_name, cr.status,
                       cr.reviewer_user_id, cr.decision_at, cr.reviewer_note,
                       cr.rejection_code, cr.brand_check_json, cr.created_at, cr.updated_at
                  FROM compass.claim_review cr
             LEFT JOIN compass.v_dealer vd USING (dealer_id)
                 WHERE cr.status = 'Pending'
                   AND (CAST(:region AS text) IS NULL OR vd.region_id = :region)
              ORDER BY cr.created_at DESC
                 LIMIT 100
                """
            ),
            {"region": r.user.region_id},
        ).mappings().fetchall()
    return [ClaimReview(**dict(row)) for row in rows]


@app.post("/api/approvals/{claim_id}/advance")
def approvals_advance(claim_id: str, body: AdvanceClaimRequest, req: Request):
    _require_lakebase()
    r = resolve_user(req, settings, engine)
    if body.decision == "Reject" and not body.rejection_code:
        raise HTTPException(status_code=400, detail="rejection_code required when decision=Reject")
    return tools.advance_claim(
        user_id=r.user.user_id,
        claim_id=claim_id,
        decision=body.decision,
        note=body.note,
        rejection_code=body.rejection_code,
    )


# ---------------------------------------------------------------------
# /api/nudge-campaigns
# ---------------------------------------------------------------------


@app.get("/api/nudge-campaigns")
def nudge_list(req: Request):
    _require_lakebase()
    r = resolve_user(req, settings, engine)
    with engine.connect() as conn:  # type: ignore[union-attr]
        rows = conn.execute(
            text(
                """
                SELECT nc.campaign_id, nc.campaign_code, nc.created_by, nc.created_at,
                       nc.template_id, nc.deadline, nc.status, nc.notes,
                       (SELECT count(*) FROM compass.nudge_recipient nr
                          WHERE nr.campaign_id = nc.campaign_id) AS recipient_count
                  FROM compass.nudge_campaign nc
                 WHERE nc.created_by = :uid
              ORDER BY nc.created_at DESC
                 LIMIT 50
                """
            ),
            {"uid": r.user.user_id},
        ).mappings().fetchall()
    return [NudgeCampaign(**dict(row)) for row in rows]


@app.post("/api/nudge-campaigns")
def nudge_create(body: NudgeCampaignCreate, req: Request):
    _require_lakebase()
    r = resolve_user(req, settings, engine)
    return tools.create_nudge_campaign(
        user_id=r.user.user_id,
        template_id=body.template_id,
        dealer_ids=body.dealer_ids,
        deadline=body.deadline,
        notes=body.notes,
    )


@app.post("/api/nudge-campaigns/{campaign_id}/queue")
def nudge_queue(campaign_id: str, req: Request):
    _require_lakebase()
    r = resolve_user(req, settings, engine)
    with engine.begin() as conn:  # type: ignore[union-attr]
        conn.execute(
            text(
                """
                UPDATE compass.nudge_campaign
                   SET status = 'Queued'
                 WHERE campaign_id = :cid AND created_by = :uid AND status = 'Draft'
                """
            ),
            {"cid": campaign_id, "uid": r.user.user_id},
        )
    return {"campaign_id": campaign_id, "status": "Queued"}


# ---------------------------------------------------------------------
# /api/saved-views
# ---------------------------------------------------------------------


@app.get("/api/saved-views")
def saved_views_list(req: Request):
    # In lite mode this returns [] — frontend handles localStorage itself.
    if engine is None:
        return []
    r = resolve_user(req, settings, engine)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT view_id, user_id, name, description, filter_payload,
                       pinned, created_at, last_used_at
                  FROM compass.saved_view
                 WHERE user_id = :uid
              ORDER BY pinned DESC, last_used_at DESC NULLS LAST
                 LIMIT 100
                """
            ),
            {"uid": r.user.user_id},
        ).mappings().fetchall()
    return [SavedView(**dict(row)) for row in rows]


@app.post("/api/saved-views", response_model=SavedView)
def saved_views_upsert(body: SavedViewUpsert, req: Request):
    if engine is None:
        # Lite — just echo back the payload as a synthetic view.
        from .tools.tools_preview import PreviewTools

        return PreviewTools().save_view(
            user_id="local",
            name=body.name,
            filter_payload=body.filter_payload,
            description=body.description,
            pinned=body.pinned,
        )
    r = resolve_user(req, settings, engine)
    try:
        return tools.save_view(
            user_id=r.user.user_id,
            name=body.name,
            filter_payload=body.filter_payload,
            description=body.description,
            pinned=body.pinned,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/saved-views/{view_id}/run")
def saved_views_run(view_id: str, req: Request):
    if engine is None:
        raise HTTPException(status_code=404, detail=f"feature_disabled_in_mode_{settings.mode}")
    with engine.connect() as conn:  # type: ignore[union-attr]
        row = conn.execute(
            text(
                "SELECT filter_payload FROM compass.saved_view WHERE view_id = :vid"
            ),
            {"vid": view_id},
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="view_not_found")
    return {"view_id": view_id, "filter_payload": row.filter_payload}


# ---------------------------------------------------------------------
# Optional: serve the React build alongside the API.
# ---------------------------------------------------------------------

_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
