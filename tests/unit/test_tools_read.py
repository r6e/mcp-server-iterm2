from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.read import (
    get_screen_contents_impl,
    get_selection_impl,
    get_session_info_impl,
    list_sessions_impl,
)


def test_list_sessions_returns_hierarchy(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    result = list_sessions_impl(client)
    assert result == {
        "windows": [
            {
                "window_id": "win-1",
                "tabs": [
                    {
                        "tab_id": 1,
                        "active": True,
                        "sessions": [
                            {
                                "session_id": "sess-1",
                                "name": "bash",
                                "active": True,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_list_sessions_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        list_sessions_impl(client)


async def test_get_session_info_returns_expected_fields(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_variable = AsyncMock(
        side_effect=lambda key: {
            "session.path": "/Users/rob",
            "user.badge": "WORK",
            "session.tty": "/dev/ttys001",
        }.get(key)
    )
    profile = MagicMock()
    profile.name = "Default"
    session.async_get_profile = AsyncMock(return_value=profile)
    session.grid_size = MagicMock(width=120, height=40)
    session.name = "bash"

    result = await get_session_info_impl(client, session_id_arg="sess-1", env_session_id=None)

    assert result == {
        "session_id": "sess-1",
        "name": "bash",
        "working_directory": "/Users/rob",
        "profile_name": "Default",
        "badge": "WORK",
        "tty": "/dev/ttys001",
        "dimensions": {"cols": 120, "rows": 40},
    }


async def test_get_screen_contents_returns_lines_and_cursor(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")

    contents = MagicMock()
    contents.number_of_lines = 2
    line0 = MagicMock(string="hello")
    line1 = MagicMock(string="world")
    contents.line = MagicMock(side_effect=[line0, line1])
    contents.cursor_coord = MagicMock(x=3, y=1)
    session.async_get_screen_contents = AsyncMock(return_value=contents)

    result = await get_screen_contents_impl(
        client, session_id_arg="sess-1", env_session_id=None
    )
    assert result == {
        "text": "hello\nworld",
        "cursor": {"row": 1, "col": 3},
    }


async def test_get_selection_returns_text(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    selection = MagicMock()
    selection.sub_selections = [MagicMock()]  # non-empty
    session.async_get_selection = AsyncMock(return_value=selection)
    session.async_get_selection_text = AsyncMock(return_value="copied text")

    result = await get_selection_impl(client, session_id_arg="sess-1", env_session_id=None)
    assert result == {"text": "copied text"}
    session.async_get_selection_text.assert_awaited_once_with(selection)


async def test_get_selection_empty_when_no_subselections(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    selection = MagicMock()
    selection.sub_selections = []  # empty: no current selection
    session.async_get_selection = AsyncMock(return_value=selection)
    session.async_get_selection_text = AsyncMock()  # should NOT be called

    result = await get_selection_impl(client, session_id_arg="sess-1", env_session_id=None)
    assert result == {"text": ""}
    session.async_get_selection_text.assert_not_awaited()
