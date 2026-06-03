"""Reusable Genie + KA worker calls.

Both the lite-mode regex router and the full-mode supervisor agent need to
invoke Genie spaces and the Knowledge Assistant; this module owns that logic
so neither has to duplicate the SDK shape gotchas (see `demo-design.md
§14.1`).

Functions here are stateless — they take a `WorkspaceClient` + `Settings`
and return a fully-formed `TurnResult`.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from contextlib import contextmanager
from typing import Any

import httpx
from databricks.sdk import WorkspaceClient

try:
    import mlflow as _mlflow  # type: ignore
except Exception:  # pragma: no cover
    _mlflow = None

from ..config import Settings
from ..schemas import Citation, GenieResult
from .router import TurnResult, UserContext

log = logging.getLogger(__name__)


@contextmanager
def _maybe_span(name: str, attributes: dict[str, Any] | None = None):
    if _mlflow is None:
        yield None
        return
    with _mlflow.start_span(name=name) as span:
        if attributes:
            try:
                span.set_attributes({k: v for k, v in attributes.items() if v is not None})
            except Exception:
                pass
        yield span


# ---------------------------------------------------------------------
# Genie
# ---------------------------------------------------------------------


def query_genie(
    *,
    w: WorkspaceClient,
    settings: Settings,
    space_id: str,
    message: str,
    user: UserContext,
) -> TurnResult:
    """Call a Genie space and re-run the generated SQL to get rows."""
    with _maybe_span(
        "genie.query",
        {
            "compass.space_id": space_id,
            "user.role": user.role,
            "user.region": user.region_id or "",
        },
    ):
        try:
            resp = w.genie.start_conversation_and_wait(
                space_id=space_id,
                content=message,
            )
        except Exception as e:  # pragma: no cover
            log.exception("Genie call failed")
            return TurnResult(
                route="error",
                content=f"Genie call failed: {e}",
                citations=[],
                genie=GenieResult(space_id=space_id),
            )

    query = _extract_genie_query(resp)
    rows, columns = _extract_genie_table(resp, w, settings.warehouse_id)
    description = _extract_genie_text(resp)
    content = description or _summarise_rows(rows, columns) or "Genie returned a result."
    return TurnResult(
        route="genie",
        content=content,
        citations=[],
        genie=GenieResult(
            space_id=space_id,
            query=query,
            rows=rows,
            columns=columns,
            description=description,
        ),
    )


# ---------------------------------------------------------------------
# Multi-Agent Supervisor (Agent Bricks MAS)
# ---------------------------------------------------------------------


def query_mas(
    *,
    w: WorkspaceClient,
    settings: Settings,
    message: str,
    user: UserContext,
) -> TurnResult:
    """Forward a read-side question to the `compass-supervisor` MAS endpoint.

    The MAS picks one of util_risk_analyst / marketing_analyst / handbook_expert
    and returns a Responses-shape payload whose final assistant message is the
    user-facing answer. We tag the resulting TurnResult with `genie`/`ka` based
    on which sub-agent ran so the existing UI keeps rendering the right disclosure.
    """
    endpoint = settings.supervisor_endpoint
    if not endpoint:
        return TurnResult(
            route="error",
            content="COMPASS_SUPERVISOR_ENDPOINT is not configured.",
            citations=[],
        )

    with _maybe_span(
        "mas.invoke",
        {
            "compass.mas_endpoint": endpoint,
            "user.role": user.role,
            "user.region": user.region_id or "",
        },
    ):
        try:
            data = _invoke_mas(w, endpoint, message)
        except Exception as e:  # pragma: no cover
            log.exception("MAS call failed")
            return TurnResult(
                route="error",
                content=f"Supervisor call failed: {e}",
                citations=[],
            )

    output = data.get("output") or []
    routed_agent = _mas_routed_agent(output)
    final_text = _mas_final_text(output) or "I couldn't get an answer from the supervisor."

    if routed_agent == "util_risk_analyst":
        return TurnResult(
            route="genie",
            content=final_text,
            citations=[],
            genie=GenieResult(
                space_id=settings.genie_space_util_risk_id,
                description=f"Routed by compass-supervisor → {routed_agent}",
            ),
        )
    if routed_agent == "marketing_analyst":
        return TurnResult(
            route="genie",
            content=final_text,
            citations=[],
            genie=GenieResult(
                space_id=settings.genie_space_marketing_id,
                description=f"Routed by compass-supervisor → {routed_agent}",
            ),
        )
    if routed_agent == "handbook_expert":
        citations = _extract_ka_citations({"output": output})
        if not citations:
            # Fall back to doc_id regex against the final supervisor text.
            citations = _doc_id_citations(final_text)
        return TurnResult(route="ka", content=final_text, citations=citations)

    return TurnResult(route="genie", content=final_text, citations=[])


def _invoke_mas(w: WorkspaceClient, endpoint: str, message: str) -> dict[str, Any]:
    cfg = w.config
    host = cfg.host.rstrip("/")
    url = f"{host}/serving-endpoints/{endpoint}/invocations"
    headers = cfg.authenticate()
    headers.setdefault("Content-Type", "application/json")
    resp = httpx.post(
        url,
        headers=headers,
        json={"input": [{"role": "user", "content": message}]},
        timeout=90.0,
    )
    resp.raise_for_status()
    return resp.json()


def _mas_routed_agent(output: list[Any]) -> str | None:
    """The first function_call's `name` is the sub-agent the supervisor picked."""
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "function_call":
            return item.get("name")
    # Some MAS responses embed <name>X</name> in an assistant message instead.
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for ch in item.get("content") or []:
            if not isinstance(ch, dict):
                continue
            t = ch.get("text") or ""
            if t.startswith("<name>") and t.endswith("</name>"):
                return t[len("<name>"):-len("</name>")]
    return None


def _mas_final_text(output: list[Any]) -> str | None:
    """Last assistant message text that isn't a `<name>X</name>` routing tag."""
    for item in reversed(output):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for ch in reversed(item.get("content") or []):
            if not isinstance(ch, dict):
                continue
            if ch.get("type") not in ("output_text", "text"):
                continue
            t = ch.get("text") or ""
            if t and not (t.startswith("<name>") and t.endswith("</name>")):
                return str(t)
    return None


def _doc_id_citations(text: str) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[str] = set()
    for m in _DOC_ID.finditer(text):
        doc_id = m.group(1).upper()
        section = m.group(2)
        if doc_id in seen:
            continue
        seen.add(doc_id)
        citations.append(Citation(doc_id=doc_id, section=section))
    return citations


# ---------------------------------------------------------------------
# Knowledge Assistant
# ---------------------------------------------------------------------


def query_ka(
    *,
    w: WorkspaceClient,
    settings: Settings,
    message: str,
    user: UserContext,
) -> TurnResult:
    """Invoke the Agent Bricks KA serving endpoint with the Responses-style payload."""
    with _maybe_span(
        "ka.invoke",
        {
            "compass.ka_endpoint": settings.ka_endpoint,
            "user.role": user.role,
            "user.region": user.region_id or "",
        },
    ):
        try:
            resp = _invoke_ka(w, settings.ka_endpoint, message)
        except Exception as e:  # pragma: no cover
            log.exception("KA call failed")
            return TurnResult(
                route="error",
                content=f"Knowledge Assistant call failed: {e}",
                citations=[],
            )

    content = _extract_ka_text(resp)
    citations = _extract_ka_citations(resp)
    if not citations:
        content = (
            "I don't have an authoritative source for that — please contact "
            "your Channel Marketing Manager."
        )
    return TurnResult(route="ka", content=content, citations=citations)


def _invoke_ka(w: WorkspaceClient, endpoint: str, message: str) -> dict[str, Any]:
    cfg = w.config
    host = cfg.host.rstrip("/")
    url = f"{host}/serving-endpoints/{endpoint}/invocations"
    headers = cfg.authenticate()
    headers.setdefault("Content-Type", "application/json")
    resp = httpx.post(
        url,
        headers=headers,
        json={"input": [{"role": "user", "content": message}]},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------
# Extraction helpers — defensive against SDK shape drift.
# ---------------------------------------------------------------------


def _extract_genie_query(resp: Any) -> str | None:
    attachments = getattr(resp, "attachments", None) or []
    for att in attachments:
        q = getattr(att, "query", None)
        if q is None and isinstance(att, dict):
            q = att.get("query")
        if q is None:
            continue
        sql = getattr(q, "query", None) or (q.get("query") if isinstance(q, dict) else None)
        if sql:
            return str(sql)
    return None


def _extract_genie_text(resp: Any) -> str | None:
    attachments = getattr(resp, "attachments", None) or []
    for att in attachments:
        t = getattr(att, "text", None) or (att.get("text") if isinstance(att, dict) else None)
        if t:
            content = getattr(t, "content", None) or (
                t.get("content") if isinstance(t, dict) else None
            )
            if content:
                return str(content)
        q = getattr(att, "query", None) or (att.get("query") if isinstance(att, dict) else None)
        if q:
            desc = (
                getattr(q, "description", None)
                or (q.get("description") if isinstance(q, dict) else None)
            )
            if desc:
                return str(desc)
    return None


def _extract_genie_table(
    resp: Any, w: WorkspaceClient, warehouse_id: str
) -> tuple[list[dict[str, Any]] | None, list[str] | None]:
    query = _extract_genie_query(resp)
    if not query:
        return None, None
    try:
        result = w.statement_execution.execute_statement(
            statement=query,
            warehouse_id=warehouse_id,
            wait_timeout="30s",
        )
        schema = result.manifest.schema if result.manifest else None
        columns = [c.name for c in (schema.columns or [])] if schema else []
        data = result.result.data_array if result.result else []
        rows = [dict(zip(columns, row)) for row in (data or [])][:50]
        return rows, columns
    except Exception:
        log.exception("Genie SQL re-run failed")
        return None, None


def _summarise_rows(
    rows: list[dict[str, Any]] | None, columns: list[str] | None
) -> str | None:
    if not rows or not columns:
        return None
    if len(rows) == 1:
        kv = ", ".join(f"{c}={rows[0].get(c)}" for c in columns)
        return f"Result: {kv}"
    head = rows[: min(3, len(rows))]
    bullets = "\n".join(
        "- " + ", ".join(f"{c}={r.get(c)}" for c in columns) for r in head
    )
    return f"{len(rows)} row(s); top {len(head)}:\n{bullets}"


def _extract_ka_text(resp: Any) -> str:
    d = resp if isinstance(resp, dict) else None

    choices = (d.get("choices") if d else None) or getattr(resp, "choices", None)
    if choices:
        first = choices[0]
        msg = first.get("message") if isinstance(first, dict) else getattr(first, "message", None)
        if msg:
            c = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if c:
                return str(c)

    output = d.get("output") if d else None
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for ch in item.get("content") or []:
                if not isinstance(ch, dict):
                    continue
                if ch.get("type") in ("output_text", "text"):
                    t = ch.get("text") or ch.get("content")
                    if t:
                        parts.append(str(t))
        if parts:
            return "\n\n".join(parts)

    for key in ("answer", "response", "output_text"):
        val = (d.get(key) if d else None) or getattr(resp, key, None)
        if isinstance(val, str) and val:
            return val
    return "I don't have an authoritative source for that — please contact your Channel Marketing Manager."


_DOC_ID = re.compile(r"\[?\b(KA-[A-Z]{3,4}-\d{3})\b\s*(§[\d.]+)?\]?", re.I)


def _extract_ka_citations(resp: Any) -> list[Citation]:
    d = resp if isinstance(resp, dict) else None
    citations: list[Citation] = []
    seen: set[str] = set()

    output = d.get("output") if d else None
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            for ch in item.get("content") or []:
                if not isinstance(ch, dict):
                    continue
                for ann in ch.get("annotations") or []:
                    if not isinstance(ann, dict):
                        continue
                    if ann.get("type") != "url_citation":
                        continue
                    title = ann.get("title") or ""
                    url = ann.get("url") or ""
                    doc_id = title or url.rsplit("/", 1)[-1].split("#")[0]
                    if not doc_id or doc_id in seen:
                        continue
                    seen.add(doc_id)
                    excerpt = _excerpt_from_url(url)
                    citations.append(Citation(doc_id=doc_id, excerpt=excerpt))

    if not citations:
        sources = (d.get("custom_outputs") if d else None) or {}
        raw = sources.get("sources_used") if isinstance(sources, dict) else None
        sources_used = raw if isinstance(raw, list) else []
        for src in sources_used:
            if not isinstance(src, dict):
                continue
            doc_id = src.get("doc_id") or src.get("id")
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                citations.append(
                    Citation(
                        doc_id=str(doc_id),
                        section=src.get("section"),
                        excerpt=src.get("excerpt"),
                    )
                )

    if not citations:
        text = _extract_ka_text(resp)
        for m in _DOC_ID.finditer(text):
            doc_id = m.group(1).upper()
            section = m.group(2)
            if doc_id in seen:
                continue
            seen.add(doc_id)
            citations.append(Citation(doc_id=doc_id, section=section))
    return citations


def _excerpt_from_url(url: str) -> str | None:
    if "#:~:text=" not in url:
        return None
    frag = url.split("#:~:text=", 1)[1]
    text = urllib.parse.unquote(frag).strip()
    return text[:280] + ("…" if len(text) > 280 else "")
