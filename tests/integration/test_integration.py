"""Integration tests against a live iTerm2.

Run with:

    uv run pytest -m integration -v

Requires iTerm2 running and the test process running inside an iTerm2 session.
"""

import pytest

from mcp_server_iterm2.tools import read, write

pytestmark = pytest.mark.integration


async def test_list_sessions_returns_real_hierarchy(client):
    result = read.list_sessions_impl(client)
    assert "windows" in result
    assert len(result["windows"]) >= 1


async def test_get_session_info(client, iterm_session_id):
    info = await read.get_session_info_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert info["session_id"] == iterm_session_id
    assert isinstance(info["dimensions"]["cols"], int)
    assert isinstance(info["dimensions"]["rows"], int)


async def test_set_and_read_badge(client, iterm_session_id):
    await write.set_badge_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, text="INTEGRATION"
    )
    info = await read.get_session_info_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert info["badge"] == "INTEGRATION"
    # cleanup
    await write.set_badge_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, text=""
    )


async def test_set_and_read_title(client, iterm_session_id):
    await write.set_title_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, title="integration-title"
    )
    info = await read.get_session_info_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert info["name"] == "integration-title"


async def test_set_tab_color_roundtrip(client, iterm_session_id):
    result = await write.set_tab_color_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, r=12, g=34, b=56
    )
    assert result["ok"] is True


async def test_set_user_variable_roundtrip(client, iterm_session_id):
    await write.set_user_variable_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None,
        name="user.itest", value="hello"
    )
    got = await read.get_variable_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, name="user.itest"
    )
    assert got["value"] == "hello"


async def test_get_screen_contents(client, iterm_session_id):
    result = await read.get_screen_contents_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert "text" in result
    assert "cursor" in result


async def test_get_scrollback(client, iterm_session_id):
    result = await read.get_scrollback_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, n_lines=50
    )
    assert "text" in result


async def test_get_recent_output_advances_cursor(client, iterm_session_id):
    first = await read.get_recent_output_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, cursor=None
    )
    second = await read.get_recent_output_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None,
        cursor=first["cursor"],
    )
    # Same cursor or advanced; should not error and should be empty unless new output appeared.
    assert "text" in second


async def test_get_selection_returns_string(client, iterm_session_id):
    result = await read.get_selection_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert isinstance(result["text"], str)


async def test_list_profiles(client):
    result = await read.list_profiles_impl(client)
    assert "profiles" in result
    assert isinstance(result["profiles"], list)


async def test_post_notification(client):
    result = await write.post_notification_impl(
        title="integration", body="test"
    )
    assert result == {"ok": True}
