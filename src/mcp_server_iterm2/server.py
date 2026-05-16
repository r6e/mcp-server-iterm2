"""MCP server setup and main entry point."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_iterm2.connection import ITermClient
from mcp_server_iterm2.errors import (
    MCPIterm2Error,
    to_error_text,
)
from mcp_server_iterm2.tools import read as read_tools


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
            for _ in range(50):
                if client.connected:
                    break
                await asyncio.sleep(0.1)
            mcp = create_server(client=client)
            await mcp.run_stdio_async()
        finally:
            reconnect.cancel()

    asyncio.run(_run())
