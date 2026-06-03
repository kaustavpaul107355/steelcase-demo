"""Session/turn store interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class TurnRecord:
    turn_index: int
    role: str
    content: str
    trace_id: str | None = None
    latency_ms: int | None = None
    tool_name: str | None = None
    tool_payload: dict[str, Any] | None = None


class Memory(Protocol):
    def get_or_create_session(self, user_id: str, session_id: str | None) -> str: ...

    def append_turn(self, session_id: str, turn: TurnRecord) -> int: ...

    def latest_session(self, user_id: str) -> str | None: ...

    def recent_turns(self, session_id: str, limit: int = 8) -> list[dict[str, str]]:
        """Return the most recent `limit` turns as OpenAI-format messages.

        Used by the supervisor to keep multi-turn context without re-sending
        the entire transcript. Caller is responsible for pruning summaries.
        """
        ...

    def get_supervisor_state(self, session_id: str) -> dict[str, Any] | None:
        """Read the rolling-window summary state for the session."""
        ...

    def update_supervisor_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Write the rolling-window summary state."""
        ...
