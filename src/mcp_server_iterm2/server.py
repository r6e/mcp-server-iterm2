"""MCP server setup and main entry point."""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_iterm2.connection import ITermClient
from mcp_server_iterm2.errors import (
    MCPIterm2Error,
    to_error_text,
)
from mcp_server_iterm2.tools import read as read_tools

_STARTUP_TIMEOUT_S = 5.0
_STARTUP_POLL_INTERVAL_S = 0.1


def create_server(*, client: Any) -> FastMCP:
    """Build a FastMCP instance with all tools wired to the given client.

    `client` is duck-typed: it must expose `require_app()` returning the
    iTerm2 App. In production it is an ITermClient; tests pass a mock.
    """
    mcp = FastMCP("iterm2")

    @mcp.tool()
    def list_sessions() -> dict[str, Any]:
        """List all windows, tabs, and sessions iTerm2 currently has open."""
        try:
            return read_tools.list_sessions_impl(client)
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    return mcp


def _env_session_id() -> str | None:
    return os.environ.get("ITERM_SESSION_ID")


def main() -> None:
    """Console script entry point."""

    async def _run() -> None:
        client = ITermClient()
        # Kick off the reconnect loop in the background.
        reconnect = asyncio.create_task(client.run_reconnect_loop())
        try:
            # Wait briefly for first connect so the user sees errors at startup.
            poll_count = round(_STARTUP_TIMEOUT_S / _STARTUP_POLL_INTERVAL_S)
            for _ in range(poll_count):
                if client.connected:
                    break
                await asyncio.sleep(_STARTUP_POLL_INTERVAL_S)
            mcp = create_server(client=client)
            await mcp.run_stdio_async()
        finally:
            reconnect.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reconnect

    asyncio.run(_run())
