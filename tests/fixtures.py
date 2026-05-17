"""Factory helpers for synthetic iTerm2 objects used in unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock


def make_session(
    *,
    session_id: str,
    name: str = "session",
    buried: bool = False,
) -> MagicMock:
    s = MagicMock(name=f"session-{session_id}")
    s.session_id = session_id
    s.name = name
    s.buried = buried
    if buried:
        s.grid_size = None
    return s


def make_tab(
    *,
    tab_id: int,
    sessions: list[MagicMock],
    minimized: list[MagicMock] | None = None,
    current: MagicMock | None = None,
) -> MagicMock:
    minimized_list = minimized or []
    t = MagicMock(name=f"tab-{tab_id}")
    t.tab_id = tab_id
    t.sessions = sessions
    t.minimized_sessions = minimized_list
    t.all_sessions = sessions + minimized_list
    t.current_session = current or (sessions[0] if sessions else None)
    for s in sessions + minimized_list:
        s.tab = t
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
    buried_sessions: list[MagicMock] | None = None,
) -> MagicMock:
    app = MagicMock(name="app")
    chosen_current = current_window or (windows[0] if windows else None)
    buried = buried_sessions or []
    app.windows = windows
    app.current_window = chosen_current
    # Back-compat aliases so any caller still using the deprecated names sees the same data.
    app.terminal_windows = windows
    app.current_terminal_window = chosen_current
    app.buried_sessions = buried

    sessions_by_id = {s.session_id: s for w in windows for t in w.tabs for s in t.all_sessions}
    for s in buried:
        sessions_by_id[s.session_id] = s
    app.get_session_by_id = lambda sid: sessions_by_id.get(sid)

    tabs_by_id = {t.tab_id: t for w in windows for t in w.tabs}
    windows_by_tab_id = {t.tab_id: w for w in windows for t in w.tabs}
    app.get_tab_by_id = lambda tid: tabs_by_id.get(tid)
    app.get_window_for_tab = lambda tid: windows_by_tab_id.get(tid)
    return app
