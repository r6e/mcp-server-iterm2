import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.read import get_session_info_impl, list_sessions_impl


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


def test_get_session_info_returns_expected_fields(simple_app):
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
    session.grid_size = MagicMock(return_value=MagicMock(width=120, height=40))
    session.name = "bash"

    result = asyncio.run(
        get_session_info_impl(client, session_id_arg="sess-1", env_session_id=None)
    )

    assert result == {
        "session_id": "sess-1",
        "name": "bash",
        "working_directory": "/Users/rob",
        "profile_name": "Default",
        "badge": "WORK",
        "tty": "/dev/ttys001",
        "dimensions": {"cols": 120, "rows": 40},
    }
