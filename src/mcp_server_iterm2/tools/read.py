"""Read-only tool implementations.

Each `*_impl(client, ...)` is pure-Python and unit-testable. The MCP
registration wrapper lives in `server.py` and adapts argument handling
and error translation.
"""

from __future__ import annotations

from typing import Any

from mcp_server_iterm2.session import resolve_session


def list_sessions_impl(client: Any) -> dict[str, Any]:
    """Return the windows → tabs → sessions hierarchy."""
    app = client.require_app()
    current_window = app.current_terminal_window
    current_window_id = getattr(current_window, "window_id", None)

    out_windows = []
    for window in app.terminal_windows:
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
                for s in tab.sessions
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
    return {"windows": out_windows}


async def get_session_info_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    """Return session metadata: title, working dir, profile, badge, dimensions, TTY."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    profile = await session.async_get_profile()
    grid = session.grid_size()
    return {
        "session_id": session.session_id,
        "name": session.name,
        "working_directory": await session.async_get_variable("session.path"),
        "profile_name": profile.name,
        "badge": await session.async_get_variable("user.badge"),
        "tty": await session.async_get_variable("session.tty"),
        "dimensions": {"cols": grid.width, "rows": grid.height},
    }
