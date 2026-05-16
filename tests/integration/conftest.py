"""Integration-test fixtures. Requires a running iTerm2 and ITERM_SESSION_ID."""

from __future__ import annotations

import os

import pytest

from mcp_server_iterm2.connection import ITermClient


@pytest.fixture(scope="module")
def iterm_session_id() -> str:
    sid = os.environ.get("ITERM_SESSION_ID")
    if not sid:
        pytest.skip("ITERM_SESSION_ID not set; integration tests require running inside iTerm2")
    return sid


@pytest.fixture(scope="module")
async def client() -> ITermClient:
    c = ITermClient()
    await c.connect_once()
    return c
