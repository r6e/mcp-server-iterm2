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
from mcp_server_iterm2.tools import write as write_tools

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

    @mcp.tool()
    async def get_session_info(session_id: str | None = None) -> dict[str, Any]:
        """Return title, working dir, profile, badge, dimensions, TTY for a session."""
        try:
            return await read_tools.get_session_info_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def get_screen_contents(session_id: str | None = None) -> dict[str, Any]:
        """Return the visible buffer text and cursor position for a session."""
        try:
            return await read_tools.get_screen_contents_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def get_selection(session_id: str | None = None) -> dict[str, Any]:
        """Return currently-selected text in the session, or empty string."""
        try:
            return await read_tools.get_selection_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def get_scrollback(
        session_id: str | None = None, n_lines: int = 200
    ) -> dict[str, Any]:
        """Return the last N lines of scrollback (default 200, max 5000)."""
        try:
            return await read_tools.get_scrollback_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                n_lines=n_lines,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def get_recent_output(
        session_id: str | None = None, cursor: str | None = None
    ) -> dict[str, Any]:
        """Return output since the given cursor (or the full available buffer if no cursor)."""
        try:
            return await read_tools.get_recent_output_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                cursor=cursor,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def get_variable(name: str, session_id: str | None = None) -> dict[str, Any]:
        """Read an iTerm2 variable by fully-qualified name.

        Examples: session.path, user.badge, tab.title, window.name.
        """
        try:
            return await read_tools.get_variable_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                name=name,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def list_profiles() -> dict[str, Any]:
        """List available iTerm2 profiles by name and GUID."""
        try:
            return await read_tools.list_profiles_impl(client)
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def set_badge(text: str, session_id: str | None = None) -> dict[str, Any]:
        """Set the session badge text. Requires \\(user.badge) in the profile's badge format."""
        try:
            return await write_tools.set_badge_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                text=text,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e

    @mcp.tool()
    async def set_title(title: str, session_id: str | None = None) -> dict[str, Any]:
        """Override the session title. Rendering depends on profile title settings."""
        try:
            return await write_tools.set_title_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                title=title,
            )
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
