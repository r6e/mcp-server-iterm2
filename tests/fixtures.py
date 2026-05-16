"""Factory helpers for synthetic iTerm2 objects used in unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock


def make_session(
    *,
    session_id: str,
    name: str = "session",
) -> MagicMock:
    s = MagicMock(name=f"session-{session_id}")
    s.session_id = session_id
    s.name = name
    return s


def make_tab(
    *,
    tab_id: int,
    sessions: list[MagicMock],
    current: MagicMock | None = None,
) -> MagicMock:
    t = MagicMock(name=f"tab-{tab_id}")
    t.tab_id = tab_id
    t.sessions = sessions
    t.current_session = current or (sessions[0] if sessions else None)
    return t


def make_window(
    *,
    window_id: str,
    tabs: list[MagicMock],
    current: MagicMock | None = None,
) -> MagicMock:
    w = MagicMock(name=f"window-{window_id}")
    w.window_id = window_id
    w.tabs = tabs
    w.current_tab = current or (tabs[0] if tabs else None)
    return w


def make_app(
    *,
    windows: list[MagicMock],
    current_window: MagicMock | None = None,
) -> MagicMock:
    app = MagicMock(name="app")
    app.terminal_windows = windows
    app.current_terminal_window = current_window or (windows[0] if windows else None)

    sessions_by_id = {s.session_id: s for w in windows for t in w.tabs for s in t.sessions}
    app.get_session_by_id = lambda sid: sessions_by_id.get(sid)
    return app
