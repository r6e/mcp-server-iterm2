from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_iterm2.errors import Disconnected, ScopeUnavailable
from mcp_server_iterm2.output_cursor import decode_cursor, encode_cursor
from mcp_server_iterm2.server import create_server
from mcp_server_iterm2.tools.read import (
    get_recent_output_impl,
    get_screen_contents_impl,
    get_scrollback_impl,
    get_selection_impl,
    get_session_info_impl,
    get_variable_impl,
    list_profiles_impl,
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

    result = await get_screen_contents_impl(client, session_id_arg="sess-1", env_session_id=None)
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


def _line_info(overflow: int, total: int):
    """Build a fake SessionLineInfo. total = scrollback_buffer_height + mutable_area_height."""
    info = MagicMock()
    info.overflow = overflow
    info.scrollback_buffer_height = max(total - 20, 0)
    info.mutable_area_height = min(total, 20)
    return info


async def test_get_scrollback_default_returns_last_200_lines_when_available(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=1000))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"line{i}") for i in range(200)]
    )

    result = await get_scrollback_impl(
        client, session_id_arg="sess-1", env_session_id=None, n_lines=200
    )
    # Most recent 200 lines, in order.
    assert result["text"].startswith("line0\nline1")
    assert result["text"].endswith("line199")
    # range starts at (overflow + total - 200) = 800
    session.async_get_contents.assert_awaited_once_with(800, 200)


async def test_get_scrollback_capped_at_5000(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=100000))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string="x") for _ in range(5000)]
    )

    await get_scrollback_impl(client, session_id_arg="sess-1", env_session_id=None, n_lines=999999)
    session.async_get_contents.assert_awaited_once_with(95000, 5000)


async def test_get_scrollback_when_fewer_lines_than_requested(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=10))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(10)]
    )

    await get_scrollback_impl(client, session_id_arg="sess-1", env_session_id=None, n_lines=200)
    session.async_get_contents.assert_awaited_once_with(0, 10)


async def test_get_scrollback_when_no_lines_available(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=0))
    session.async_get_contents = AsyncMock()  # should NOT be called

    result = await get_scrollback_impl(
        client, session_id_arg="sess-1", env_session_id=None, n_lines=200
    )
    assert result == {"text": ""}
    session.async_get_contents.assert_not_awaited()


async def test_get_scrollback_overflow_offset_applied(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=100, total=1000))
    session.async_get_contents = AsyncMock(return_value=[MagicMock(string="x") for _ in range(200)])

    await get_scrollback_impl(client, session_id_arg="sess-1", env_session_id=None, n_lines=200)
    # start = overflow + total - take = 100 + 1000 - 200 = 900
    session.async_get_contents.assert_awaited_once_with(900, 200)


async def test_get_recent_output_no_cursor_returns_last_screenful_small(simple_app):
    """When total lines <= screen height, no-cursor returns all lines."""
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=5))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(5)]
    )

    result = await get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=None
    )
    assert result["text"] == "L0\nL1\nL2\nL3\nL4"
    assert result["cursor_expired"] is False
    sid, line = decode_cursor(result["cursor"])
    assert (sid, line) == ("sess-1", 4)


async def test_get_recent_output_no_cursor_bounded_to_screenful_with_large_buffer(simple_app):
    """No-cursor call on a session with 1000 lines must return only the screenful (~20)."""
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    # _line_info(overflow=0, total=1000) → scrollback=980, mutable=20
    info = _line_info(overflow=0, total=1000)
    session.async_get_line_info = AsyncMock(return_value=info)
    # Return 20 lines for the screenful fetch.
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(980, 1000)]
    )

    result = await get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=None
    )

    # Should have fetched exactly the mutable area (lines 980–999 = 20 lines).
    session.async_get_contents.assert_awaited_once_with(980, 20)
    assert result["cursor_expired"] is False
    sid, line = decode_cursor(result["cursor"])
    assert (sid, line) == ("sess-1", 999)


async def test_get_recent_output_advances_from_cursor(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=10))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(5, 10)]
    )

    prior = encode_cursor(session_id="sess-1", line_number=4)
    result = await get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=prior
    )
    assert result["text"] == "L5\nL6\nL7\nL8\nL9"
    assert result["cursor_expired"] is False
    session.async_get_contents.assert_awaited_once_with(5, 5)


async def test_get_recent_output_no_new_lines(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=10))
    session.async_get_contents = AsyncMock()

    prior = encode_cursor(session_id="sess-1", line_number=9)
    result = await get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=prior
    )
    assert result["text"] == ""
    assert result["cursor_expired"] is False
    session.async_get_contents.assert_not_awaited()


async def test_get_recent_output_cursor_expired(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    # Buffer now covers lines 500..699; old cursor at 100 is expired.
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=500, total=200))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(500, 700)]
    )

    prior = encode_cursor(session_id="sess-1", line_number=100)
    result = await get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=prior
    )
    assert result["cursor_expired"] is True
    session.async_get_contents.assert_awaited_once_with(500, 200)


async def test_get_recent_output_invalid_cursor_translates_to_runtime_error(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=5))

    mcp = create_server(client=client)
    tool = mcp._tool_manager.get_tool("get_recent_output")
    assert tool is not None

    with pytest.raises(RuntimeError) as exc_info:
        await tool.fn(session_id="sess-1", cursor="not-a-valid-cursor")

    assert "Invalid cursor" in str(exc_info.value)


async def test_get_variable_session_scope(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_variable = AsyncMock(return_value="zsh")

    result = await get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="session.username"
    )
    assert result == {"name": "session.username", "value": "zsh"}
    session.async_get_variable.assert_awaited_once_with("session.username")


async def test_get_variable_user_scope_reads_from_session(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_variable = AsyncMock(return_value="WORK")

    result = await get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="user.badge"
    )
    assert result == {"name": "user.badge", "value": "WORK"}
    session.async_get_variable.assert_awaited_once_with("user.badge")


async def test_get_variable_tab_scope_routes_to_tab(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    # session.tab is already wired by the fixture
    session.tab.async_get_variable = AsyncMock(return_value="42")

    result = await get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="tab.foo"
    )
    assert result == {"name": "tab.foo", "value": "42"}
    session.tab.async_get_variable.assert_awaited_once_with("tab.foo")


async def test_get_variable_window_scope_routes_to_window(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    window = simple_app.get_window_for_tab(session.tab.tab_id)
    window.async_get_variable = AsyncMock(return_value="my-window-name")

    result = await get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="window.foo"
    )
    assert result == {"name": "window.foo", "value": "my-window-name"}
    window.async_get_variable.assert_awaited_once_with("window.foo")


async def test_get_variable_tab_scope_raises_when_session_has_no_tab(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.tab = None  # buried session
    with pytest.raises(ScopeUnavailable) as exc:
        await get_variable_impl(
            client, session_id_arg="sess-1", env_session_id=None, name="tab.foo"
        )
    assert exc.value.scope == "tab"


async def test_get_variable_window_scope_raises_when_session_has_no_tab(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.tab = None
    with pytest.raises(ScopeUnavailable) as exc:
        await get_variable_impl(
            client, session_id_arg="sess-1", env_session_id=None, name="window.foo"
        )
    assert exc.value.scope == "tab"


async def test_get_variable_window_scope_raises_when_no_window_for_tab(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    simple_app.get_window_for_tab = MagicMock(return_value=None)
    with pytest.raises(ScopeUnavailable) as exc:
        await get_variable_impl(
            client, session_id_arg="sess-1", env_session_id=None, name="window.foo"
        )
    assert exc.value.scope == "window"


@patch("mcp_server_iterm2.tools.read.iterm2")
async def test_list_profiles_returns_name_and_guid(mock_iterm2):
    p1 = MagicMock()
    p1.name = "Default"
    p1.guid = "guid-1"
    p2 = MagicMock()
    p2.name = "Dark"
    p2.guid = "guid-2"
    mock_iterm2.PartialProfile.async_query = AsyncMock(return_value=[p1, p2])

    client = MagicMock()
    client.require_connection = MagicMock(return_value="<conn>")
    result = await list_profiles_impl(client)
    assert result == {
        "profiles": [
            {"name": "Default", "guid": "guid-1"},
            {"name": "Dark", "guid": "guid-2"},
        ]
    }
    mock_iterm2.PartialProfile.async_query.assert_awaited_once_with("<conn>")
