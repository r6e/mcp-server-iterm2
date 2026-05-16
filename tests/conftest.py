"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.fixtures import make_app, make_session, make_tab, make_window


@pytest.fixture
def simple_app() -> MagicMock:
    """One window, one tab, one session with id 'sess-1'."""
    s1 = make_session(session_id="sess-1", name="bash", is_active=True)
    t1 = make_tab(tab_id=1, sessions=[s1])
    w1 = make_window(window_id="win-1", tabs=[t1])
    return make_app(windows=[w1])
