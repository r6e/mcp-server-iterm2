from unittest.mock import MagicMock

from mcp_server_iterm2.server import create_server


def test_create_server_returns_fastmcp_with_expected_name():
    client = MagicMock()
    mcp = create_server(client=client)
    assert mcp.name == "iterm2"
