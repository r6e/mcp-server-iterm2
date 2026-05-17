from unittest.mock import MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected, ScopeUnavailable, to_error_text
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


async def test_create_server_get_variable_translates_scope_unavailable():
    client = MagicMock()
    app = MagicMock()
    session = MagicMock()
    session.tab = None
    app.get_session_by_id = MagicMock(return_value=session)
    client.require_app.return_value = app

    mcp = create_server(client=client)
    tool = mcp._tool_manager.get_tool("get_variable")
    with pytest.raises(RuntimeError) as exc:
        await tool.fn(name="tab.foo", session_id="sess-1")
    assert str(exc.value) == to_error_text(ScopeUnavailable("tab"))


def test_create_server_wraps_unknown_exceptions_as_generic_internal_error():
    """Unknown exceptions must not leak third-party error messages to the agent."""
    client = MagicMock()
    client.require_app.side_effect = RuntimeError(
        "internal: connection pool exhausted at 0xdeadbeef"
    )
    mcp = create_server(client=client)
    tool = mcp._tool_manager.get_tool("list_sessions")
    assert tool is not None
    with pytest.raises(RuntimeError) as exc_info:
        tool.fn()
    msg = str(exc_info.value)
    # The error message must NOT echo the inner message verbatim.
    assert "connection pool exhausted" not in msg
    assert "0xdeadbeef" not in msg
    # But it should clearly indicate an internal error occurred.
    assert "Internal error" in msg


async def test_create_server_surfaces_invalid_argument_detail_to_agent():
    """InvalidArgument errors must reach the agent with the actual message intact."""
    client = MagicMock()
    app = MagicMock()
    session = MagicMock()
    session.session_id = "sess-1"
    app.get_session_by_id = MagicMock(return_value=session)
    client.require_app.return_value = app

    mcp = create_server(client=client)
    tool = mcp._tool_manager.get_tool("set_badge")
    with pytest.raises(RuntimeError) as exc_info:
        await tool.fn(text="x" * 1000, session_id="sess-1")
    msg = str(exc_info.value)
    # Detail must survive the wrapper.
    assert "badge text length 1000 exceeds limit 256" in msg
    # And it must NOT be the generic Internal error envelope.
    assert "Internal error" not in msg
