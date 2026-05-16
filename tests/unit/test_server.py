from unittest.mock import MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected, to_error_text
from mcp_server_iterm2.server import create_server


def test_create_server_returns_fastmcp_with_expected_name():
    client = MagicMock()
    mcp = create_server(client=client)
    assert mcp.name == "iterm2"


def test_create_server_translates_mcpiterm2error_to_runtime_error():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    mcp = create_server(client=client)

    tool = mcp._tool_manager.get_tool("list_sessions")
    assert tool is not None

    with pytest.raises(RuntimeError) as exc_info:
        tool.fn()

    assert str(exc_info.value) == to_error_text(Disconnected())
