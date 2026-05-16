"""Resolve a target Session from explicit argument, env, or error."""

from __future__ import annotations

from typing import Any

from mcp_server_iterm2.errors import NoCurrentSession, SessionNotFound


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
