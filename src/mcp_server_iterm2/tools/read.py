"""Read-only tool implementations.

Each `*_impl(client, ...)` is pure-Python and unit-testable. The MCP
registration wrapper lives in `server.py` and adapts argument handling
and error translation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import iterm2  # type: ignore[import-untyped]

from mcp_server_iterm2.errors import InvalidArgument, ScopeUnavailable
from mcp_server_iterm2.output_cursor import (
    decode_cursor,
    diff_since,
    encode_cursor,
)
from mcp_server_iterm2.session import resolve_session

SCROLLBACK_MAX = 5000
_MAX_VAR_NAME = 256


def list_sessions_impl(client: Any) -> dict[str, Any]:
    """Return the windows → tabs → sessions hierarchy."""
    app = client.require_app()
    current_window = app.current_window
    current_window_id = getattr(current_window, "window_id", None)

    out_windows = []
    for window in app.windows:
        current_tab = window.current_tab
        current_tab_id = getattr(current_tab, "tab_id", None)
        out_tabs = []
        for tab in window.tabs:
            current_session = tab.current_session
            current_session_id = getattr(current_session, "session_id", None)
            out_sessions = [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "active": s.session_id == current_session_id
                    and tab.tab_id == current_tab_id
                    and window.window_id == current_window_id,
                }
                for s in tab.all_sessions
            ]
            out_tabs.append(
                {
                    "tab_id": tab.tab_id,
                    "active": tab.tab_id == current_tab_id
                    and window.window_id == current_window_id,
                    "sessions": out_sessions,
                }
            )
        out_windows.append({"window_id": window.window_id, "tabs": out_tabs})
    buried = getattr(app, "buried_sessions", []) or []
    out_buried = [{"session_id": s.session_id, "name": s.name} for s in buried]
    return {"windows": out_windows, "buried_sessions": out_buried}


async def get_session_info_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    """Return session metadata: title, working dir, profile, badge, dimensions, TTY.

    Buried sessions have no grid; `dimensions` is None in that case.
    """
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    grid = session.grid_size
    profile, working_directory, badge, tty = await asyncio.gather(
        session.async_get_profile(),
        session.async_get_variable("session.path"),
        session.async_get_variable("user.badge"),
        session.async_get_variable("session.tty"),
    )
    dimensions = {"cols": grid.width, "rows": grid.height} if grid is not None else None
    return {
        "session_id": session.session_id,
        "name": session.name,
        "working_directory": working_directory,
        "profile_name": profile.name,
        "badge": badge,
        "tty": tty,
        "dimensions": dimensions,
    }


async def get_screen_contents_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    """Return the visible buffer text and cursor position for a session."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    contents = await session.async_get_screen_contents()
    lines = [contents.line(i).string for i in range(contents.number_of_lines)]
    return {
        "text": "\n".join(lines),
        "cursor": {"row": contents.cursor_coord.y, "col": contents.cursor_coord.x},
    }


async def get_selection_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    """Return the currently-selected text in a session, or empty string if nothing is selected."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    selection = await session.async_get_selection()
    if not selection.sub_selections:
        return {"text": ""}
    text = await session.async_get_selection_text(selection)
    return {"text": text}


async def get_scrollback_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    n_lines: int = 200,
) -> dict[str, Any]:
    """Return the last N lines of scrollback (capped at SCROLLBACK_MAX)."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    conn = client.require_connection()
    async with iterm2.Transaction(conn):
        info = await session.async_get_line_info()
        total = info.scrollback_buffer_height + info.mutable_area_height
        take = min(max(n_lines, 0), SCROLLBACK_MAX, total)
        if take == 0:
            return {"text": ""}
        start = info.overflow + total - take
        line_contents = await session.async_get_contents(start, take)
    return {"text": "\n".join(lc.string for lc in line_contents)}


async def get_recent_output_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    cursor: str | None,
) -> dict[str, Any]:
    """Return output since the given cursor, or the visible screen if no cursor supplied."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    sid = session.session_id
    conn = client.require_connection()

    async with iterm2.Transaction(conn):
        info = await session.async_get_line_info()
        total = info.scrollback_buffer_height + info.mutable_area_height

        last_seen: int | None
        if cursor is None:
            # First call: bound fetch to the visible screen (mutable area) so we
            # don't dump the entire scrollback buffer on the caller.
            # When there is no scrollback yet (fresh session), the mutable area
            # starts at overflow itself, so there is nothing above to skip —
            # leave last_seen=None to fetch all available lines without marking
            # the cursor expired.
            if info.scrollback_buffer_height > 0:
                visible_start = info.overflow + info.scrollback_buffer_height
                last_seen = visible_start - 1  # pretend caller already saw everything above
            else:
                last_seen = None
        else:
            _, last_seen = decode_cursor(cursor, expected_session_id=sid)

        diff = diff_since(overflow=info.overflow, line_count=total, last_seen=last_seen)

        if diff.first_line is None:
            return {
                "text": "",
                "cursor": encode_cursor(session_id=sid, line_number=diff.new_last_seen),
                "cursor_expired": diff.cursor_expired,
            }

        # invariant: diff_since sets last_line whenever first_line is set
        assert diff.last_line is not None
        count = diff.last_line - diff.first_line + 1
        line_contents = await session.async_get_contents(diff.first_line, count)

    return {
        "text": "\n".join(lc.string for lc in line_contents),
        "cursor": encode_cursor(session_id=sid, line_number=diff.new_last_seen),
        "cursor_expired": diff.cursor_expired,
    }


async def get_variable_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    name: str,
) -> dict[str, Any]:
    """Read an iTerm2 variable by fully-qualified name, routing by scope prefix."""
    if len(name) > _MAX_VAR_NAME:
        raise InvalidArgument(f"variable name length {len(name)} exceeds limit {_MAX_VAR_NAME}")
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    if name.startswith("tab."):
        tab = session.tab
        if tab is None:
            raise ScopeUnavailable("tab")
        value = await tab.async_get_variable(name)
    elif name.startswith("window."):
        tab = session.tab
        if tab is None:
            raise ScopeUnavailable("tab")
        window = app.get_window_for_tab(tab.tab_id)
        if window is None:
            raise ScopeUnavailable("window")
        value = await window.async_get_variable(name)
    else:
        # session.* and user.* both live on the session; any unknown prefix is delegated
        # to the session and will fail with whatever iTerm2 returns.
        value = await session.async_get_variable(name)
    return {"name": name, "value": value}


async def list_profiles_impl(client: Any) -> dict[str, Any]:
    """Return all iTerm2 profiles as a list of name/GUID pairs."""
    conn = client.require_connection()
    profiles = await iterm2.PartialProfile.async_query(conn)
    return {"profiles": [{"name": p.name, "guid": p.guid} for p in profiles]}
