from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.write import set_badge_impl, set_title_impl


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
