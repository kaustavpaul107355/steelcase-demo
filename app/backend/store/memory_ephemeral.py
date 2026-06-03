"""In-process session memory for `lite` mode. Lost on restart."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from .memory import TurnRecord


class EphemeralMemory:
    def __init__(self):
        self._sessions: dict[str, str] = {}  # user_id -> latest session_id
        self._turns: dict[str, list[TurnRecord]] = defaultdict(list)
        self._supervisor_state: dict[str, dict[str, Any]] = {}

    def get_or_create_session(self, user_id: str, session_id: str | None) -> str:
        if session_id and session_id in self._turns:
            return session_id
        sid = session_id or str(uuid.uuid4())
        self._sessions[user_id] = sid
        self._turns.setdefault(sid, [])
        return sid

    def append_turn(self, session_id: str, turn: TurnRecord) -> int:
        turns = self._turns[session_id]
        turn.turn_index = len(turns)
        turns.append(turn)
        return turn.turn_index

    def latest_session(self, user_id: str) -> str | None:
        return self._sessions.get(user_id)

    def recent_turns(self, session_id: str, limit: int = 8) -> list[dict[str, str]]:
        turns = self._turns.get(session_id) or []
        tail = turns[-limit:]
        return [{"role": t.role, "content": t.content} for t in tail]

    def get_supervisor_state(self, session_id: str) -> dict[str, Any] | None:
        return self._supervisor_state.get(session_id)

    def update_supervisor_state(self, session_id: str, state: dict[str, Any]) -> None:
        self._supervisor_state[session_id] = state
