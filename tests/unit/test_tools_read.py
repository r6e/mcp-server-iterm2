from unittest.mock import MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.read import list_sessions_impl


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
