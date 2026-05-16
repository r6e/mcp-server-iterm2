import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.write import (
    post_notification_impl,
    set_badge_impl,
    set_tab_color_impl,
    set_title_impl,
    set_user_variable_impl,
)


async def test_set_badge_writes_user_badge_variable(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_variable = AsyncMock()

    result = await set_badge_impl(
        client, session_id_arg="sess-1", env_session_id=None, text="WORKING"
    )
    assert result == {"ok": True, "badge": "WORKING"}
    session.async_set_variable.assert_awaited_once_with("user.badge", "WORKING")


async def test_set_badge_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        await set_badge_impl(
            client, session_id_arg="sess-1", env_session_id=None, text="x"
        )


async def test_set_title_calls_async_set_name(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_name = AsyncMock()

    result = await set_title_impl(
        client, session_id_arg="sess-1", env_session_id=None, title="My Session"
    )
    assert result == {"ok": True, "title": "My Session"}
    session.async_set_name.assert_awaited_once_with("My Session")


async def test_set_title_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        await set_title_impl(
            client, session_id_arg="sess-1", env_session_id=None, title="x"
        )


@patch("mcp_server_iterm2.tools.write.iterm2")
async def test_set_tab_color_writes_profile_properties(mock_iterm2, simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_profile_properties = AsyncMock()

    fake_profile = MagicMock()
    mock_iterm2.LocalWriteOnlyProfile.return_value = fake_profile
    fake_color = MagicMock()
    mock_iterm2.Color.return_value = fake_color

    result = await set_tab_color_impl(
        client, session_id_arg="sess-1", env_session_id=None, r=255, g=128, b=64
    )
    assert result == {"ok": True, "rgb": [255, 128, 64]}
    mock_iterm2.Color.assert_called_once_with(255, 128, 64)
    fake_profile.set_tab_color.assert_called_once_with(fake_color)
    fake_profile.set_use_tab_color.assert_called_once_with(True)
    session.async_set_profile_properties.assert_awaited_once_with(fake_profile)


async def test_set_tab_color_rejects_out_of_range_values(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await set_tab_color_impl(
            client, session_id_arg="sess-1", env_session_id=None, r=300, g=0, b=0
        )


async def test_set_tab_color_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        await set_tab_color_impl(
            client, session_id_arg="sess-1", env_session_id=None, r=0, g=0, b=0
        )


async def test_set_user_variable_writes(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_variable = AsyncMock()

    result = await set_user_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None,
        name="user.task", value="refactor",
    )
    assert result == {"ok": True, "name": "user.task", "value": "refactor"}
    session.async_set_variable.assert_awaited_once_with("user.task", "refactor")


async def test_set_user_variable_rejects_non_user_prefix(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await set_user_variable_impl(
            client, session_id_arg="sess-1", env_session_id=None,
            name="session.path", value="oops",
        )


async def test_set_user_variable_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        await set_user_variable_impl(
            client, session_id_arg="sess-1", env_session_id=None,
            name="user.x", value="y",
        )


@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_invokes_osascript(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["osascript"], returncode=0, stdout="", stderr=""
    )
    result = await post_notification_impl(title="Done", body="The task is complete.")
    assert result == {"ok": True}
    args, _ = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "osascript"
    joined = " ".join(cmd)
    assert "The task is complete." in joined
    assert "Done" in joined


@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_propagates_osascript_failure(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["osascript"], returncode=1, stdout="", stderr="failed"
    )
    with pytest.raises(RuntimeError):
        await post_notification_impl(title="X", body="Y")


@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_escapes_double_quotes_in_body(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["osascript"], returncode=0, stdout="", stderr=""
    )
    await post_notification_impl(title="t", body='hello "world"')
    args, _ = mock_run.call_args
    script = args[0][2]  # the -e arg
    # Embedded quotes should be escaped (preceded by backslash) so the AppleScript parses.
    assert r'hello \"world\"' in script
