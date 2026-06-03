"""Lakebase-backed session memory (standard/full).

Writes to `compass.chat_session` and `compass.chat_turn`.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .memory import TurnRecord


class LakebaseMemory:
    def __init__(self, engine: Engine):
        self.engine = engine

    def get_or_create_session(self, user_id: str, session_id: str | None) -> str:
        with self.engine.begin() as conn:
            if session_id:
                exists = conn.execute(
                    text(
                        "SELECT 1 FROM compass.chat_session "
                        "WHERE session_id = :sid AND user_id = :uid"
                    ),
                    {"sid": session_id, "uid": user_id},
                ).first()
                if exists:
                    conn.execute(
                        text(
                            "UPDATE compass.chat_session SET last_active_at = now() "
                            "WHERE session_id = :sid"
                        ),
                        {"sid": session_id},
                    )
                    return session_id

            sid = uuid.uuid4()
            conn.execute(
                text(
                    """
                    INSERT INTO compass.chat_session (session_id, user_id)
                    VALUES (:sid, :uid)
                    """
                ),
                {"sid": sid, "uid": user_id},
            )
            return str(sid)

    def append_turn(self, session_id: str, turn: TurnRecord) -> int:
        with self.engine.begin() as conn:
            next_idx = conn.execute(
                text(
                    "SELECT COALESCE(MAX(turn_index), -1) + 1 AS n "
                    "FROM compass.chat_turn WHERE session_id = :sid"
                ),
                {"sid": session_id},
            ).scalar_one()
            conn.execute(
                text(
                    """
                    INSERT INTO compass.chat_turn
                        (session_id, turn_index, role, content, tool_name,
                         tool_payload_json, trace_id, latency_ms)
                    VALUES
                        (:sid, :idx, :role, :content, :tn, :tp, :trace, :lat)
                    """
                ),
                {
                    "sid": session_id,
                    "idx": next_idx,
                    "role": turn.role,
                    "content": turn.content,
                    "tn": turn.tool_name,
                    "tp": json.dumps(turn.tool_payload) if turn.tool_payload else None,
                    "trace": turn.trace_id,
                    "lat": turn.latency_ms,
                },
            )
            conn.execute(
                text(
                    "UPDATE compass.chat_session SET last_active_at = now() "
                    "WHERE session_id = :sid"
                ),
                {"sid": session_id},
            )
        return next_idx

    def latest_session(self, user_id: str) -> str | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT session_id FROM compass.chat_session
                     WHERE user_id = :uid
                  ORDER BY last_active_at DESC
                     LIMIT 1
                    """
                ),
                {"uid": user_id},
            ).first()
        return str(row.session_id) if row else None

    def recent_turns(self, session_id: str, limit: int = 8) -> list[dict[str, str]]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT role, content
                      FROM compass.chat_turn
                     WHERE session_id = :sid
                  ORDER BY turn_index DESC
                     LIMIT :lim
                    """
                ),
                {"sid": session_id, "lim": limit},
            ).mappings().fetchall()
        # Reverse to chronological order so the LLM sees user/assistant in sequence.
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def get_supervisor_state(self, session_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT supervisor_state FROM compass.chat_session "
                    "WHERE session_id = :sid"
                ),
                {"sid": session_id},
            ).first()
        if not row:
            return None
        state = row[0]
        # psycopg returns JSONB as a Python dict already; be defensive against str.
        if isinstance(state, str):
            try:
                return json.loads(state)
            except json.JSONDecodeError:
                return None
        return state

    def update_supervisor_state(self, session_id: str, state: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE compass.chat_session "
                    "   SET supervisor_state = CAST(:state AS jsonb) "
                    " WHERE session_id = :sid"
                ),
                {"sid": session_id, "state": json.dumps(state)},
            )
