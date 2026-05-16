"""Persistent iTerm2 connection with reconnect."""

from __future__ import annotations

import asyncio
import logging
import os
from asyncio import sleep as _sleep
from typing import Any

import iterm2  # type: ignore[import-untyped]

from mcp_server_iterm2.cookie import request_cookie
from mcp_server_iterm2.errors import Disconnected

log = logging.getLogger(__name__)

_BACKOFF_BASE = 1
_BACKOFF_CAP = 30


def _backoff_seconds(attempt: int) -> int:
    """Exponential backoff: 1, 2, 4, 8, 16, 30 (cap)."""
    delay = _BACKOFF_BASE * (2**attempt)
    return min(delay, _BACKOFF_CAP)


class ITermClient:
    """Owns a persistent iTerm2 Connection + App, reconnecting on failure."""

    def __init__(self) -> None:
        self._connection: Any = None
        self._app: Any = None
        self._disconnect_event: asyncio.Event = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._app is not None

    @property
    def app(self) -> Any:
        return self._app

    def require_app(self) -> Any:
        """Return the app or raise Disconnected if not connected."""
        if self._app is None:
            raise Disconnected()
        return self._app

    def require_connection(self) -> Any:
        if self._connection is None:
            raise Disconnected()
        return self._connection

    def _install_disconnect_watcher(self) -> None:
        """Attach a done-callback to the SDK's internal dispatch task.

        When the WebSocket closes, the dispatch task finishes (done() == True)
        and fires this callback, which sets _disconnect_event so
        run_reconnect_loop can notice the drop without polling.

        The dispatch task is stored under the Python name-mangled attribute
        ``_Connection__dispatch_forever_future``. This is private SDK
        internals, but has been stable across all iterm2 PyPI releases; it
        is the only reliable zero-traffic disconnect signal when using
        ``Connection.async_create()`` (the callback list in
        ``iterm2.connection.gDisconnectCallbacks`` is only drained inside
        ``Connection.run()``, which we don't use).
        """
        dispatch_task = getattr(self._connection, "_Connection__dispatch_forever_future", None)
        if dispatch_task is not None:
            dispatch_task.add_done_callback(lambda _: self._disconnect_event.set())
        else:
            # SDK internals changed; log a warning so we don't silently lose
            # disconnect detection. The loop will still reconnect on the next
            # tool call that raises an SDK exception.
            log.warning("iterm2 SDK dispatch task not found; disconnect detection degraded")

    async def connect_once(self) -> None:
        """Establish a single connection attempt. Raises on failure."""
        cookie = request_cookie()
        os.environ["ITERM2_COOKIE"] = cookie
        self._connection = await iterm2.Connection.async_create()
        self._app = await iterm2.async_get_app(self._connection)
        log.info("connected to iTerm2")

    async def run_reconnect_loop(self) -> None:
        """Forever-running loop: connect, hold, reconnect with backoff."""
        attempt = 0
        while True:
            try:
                await self.connect_once()
                attempt = 0
                self._disconnect_event = asyncio.Event()
                self._install_disconnect_watcher()
                await self._disconnect_event.wait()
                # Disconnect observed; fall through to backoff retry.
                self._connection = None
                self._app = None
                raise ConnectionError("iTerm2 disconnected")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._connection = None
                self._app = None
                delay = _backoff_seconds(attempt)
                log.warning("iterm2 connection failed (%s); retrying in %ss", exc, delay)
                attempt += 1
                await _sleep(delay)
