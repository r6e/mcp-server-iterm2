import asyncio
import contextlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_iterm2.connection import ITermClient, _backoff_seconds
from mcp_server_iterm2.errors import Disconnected


def test_backoff_doubles_with_cap():
    assert _backoff_seconds(0) == 1
    assert _backoff_seconds(1) == 2
    assert _backoff_seconds(2) == 4
    assert _backoff_seconds(3) == 8
    assert _backoff_seconds(4) == 16
    assert _backoff_seconds(5) == 30
    assert _backoff_seconds(99) == 30


@pytest.mark.asyncio
@patch("mcp_server_iterm2.connection.request_cookie", return_value="cookie123")
@patch("mcp_server_iterm2.connection.iterm2")
async def test_start_connects_and_sets_cookie_env(mock_iterm2, _):
    fake_conn = MagicMock()
    fake_app = MagicMock()
    mock_iterm2.Connection.async_create = AsyncMock(return_value=fake_conn)
    mock_iterm2.async_get_app = AsyncMock(return_value=fake_app)

    client = ITermClient()
    await client.connect_once()

    assert os.environ["ITERM2_COOKIE"] == "cookie123"
    assert client.connected is True
    assert client.app is fake_app
    mock_iterm2.Connection.async_create.assert_awaited_once()
    mock_iterm2.async_get_app.assert_awaited_once_with(fake_conn)


def test_require_app_raises_disconnected_when_not_connected():
    client = ITermClient()
    with pytest.raises(Disconnected):
        client.require_app()


@pytest.mark.asyncio
@patch("mcp_server_iterm2.connection._sleep", new=AsyncMock())
@patch("mcp_server_iterm2.connection.request_cookie", return_value="cookie123")
@patch("mcp_server_iterm2.connection.iterm2")
async def test_run_reconnect_loop_retries_on_failure(mock_iterm2, _):
    fake_app = MagicMock()
    calls = {"n": 0}

    async def async_create_side_effect(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionRefusedError("nope")
        return MagicMock()

    mock_iterm2.Connection.async_create = AsyncMock(side_effect=async_create_side_effect)
    mock_iterm2.async_get_app = AsyncMock(return_value=fake_app)

    client = ITermClient()
    task = asyncio.create_task(client.run_reconnect_loop())
    for _ in range(50):
        if client.connected:
            break
        await asyncio.sleep(0)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    assert client.connected is True
    assert calls["n"] == 3


@pytest.mark.asyncio
@patch("mcp_server_iterm2.connection._sleep", new=AsyncMock())
@patch("mcp_server_iterm2.connection.request_cookie", return_value="cookie123")
@patch("mcp_server_iterm2.connection.iterm2")
async def test_run_reconnect_loop_reconnects_on_disconnect(mock_iterm2, _):
    """Simulating a mid-life disconnect: the loop should reconnect automatically."""
    mock_iterm2.Connection.async_create = AsyncMock(return_value=MagicMock())
    mock_iterm2.async_get_app = AsyncMock(return_value=MagicMock())

    client = ITermClient()
    # Override _install_disconnect_watcher so it's a no-op; we'll fire
    # _disconnect_event manually to simulate the websocket closing.
    client._install_disconnect_watcher = lambda: None  # type: ignore[method-assign]

    task = asyncio.create_task(client.run_reconnect_loop())

    # Wait for the first connection to establish.
    for _ in range(50):
        if client.connected:
            break
        await asyncio.sleep(0)
    assert client.connected, "should have connected on first attempt"

    # Simulate disconnect by firing the event.
    client._disconnect_event.set()

    # Give the loop a chance to detect the disconnect and reconnect.
    for _ in range(50):
        if mock_iterm2.Connection.async_create.await_count >= 2:
            break
        await asyncio.sleep(0)

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert mock_iterm2.Connection.async_create.await_count >= 2, (
        "should have reconnected after disconnect"
    )


@pytest.mark.asyncio
@patch("mcp_server_iterm2.connection.iterm2")
async def test_connect_once_does_not_block_event_loop(mock_iterm2, monkeypatch):
    """request_cookie is a synchronous subprocess call; it must run off the loop."""
    import threading

    called_off_main = {"flag": False}

    def blocking_request_cookie():
        called_off_main["flag"] = threading.current_thread() is not threading.main_thread()
        return "cookie-xyz"

    monkeypatch.setattr("mcp_server_iterm2.connection.request_cookie", blocking_request_cookie)
    mock_iterm2.Connection.async_create = AsyncMock(return_value=MagicMock())
    mock_iterm2.async_get_app = AsyncMock(return_value=MagicMock())

    client = ITermClient()
    await client.connect_once()

    assert called_off_main["flag"], "request_cookie must run in a thread, not on the loop"
