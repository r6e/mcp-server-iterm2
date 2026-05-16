"""Resolve a target Session from explicit argument, env, or error."""

from __future__ import annotations

from typing import Any

from mcp_server_iterm2.errors import NoCurrentSession, SessionNotFound


def normalize_iterm_session_id(value: str | None) -> str | None:
    """Strip the position prefix from $ITERM_SESSION_ID, if present.

    iTerm2 sets ITERM_SESSION_ID to "w<X>t<Y>p<Z>:<UUID>" (window/tab/pane
    position plus the session UUID). The iTerm2 Python API's
    get_session_by_id expects the bare UUID. Strip everything before the
    final colon. Returns None for None or empty input.
    """
    if not value:
        return None
    return value.rsplit(":", 1)[-1]


def resolve_session(app: Any, session_id_arg: str | None, env_session_id: str | None) -> Any:
    """Return the session for session_id_arg if set, else env_session_id.

    Raises NoCurrentSession if neither is provided. Raises SessionNotFound
    if a provided id does not match a live session.
    """
    requested = session_id_arg or env_session_id or None
    if not requested:
        raise NoCurrentSession()
    session = app.get_session_by_id(requested)
    if session is None:
        raise SessionNotFound(requested)
    return session
