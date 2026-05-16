"""Read-only tool implementations.

Each `*_impl(client, ...)` is pure-Python and unit-testable. The MCP
registration wrapper lives in `server.py` and adapts argument handling
and error translation.
"""

from __future__ import annotations

from typing import Any


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
