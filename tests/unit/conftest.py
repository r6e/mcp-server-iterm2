"""Unit-test fixtures local to tests/unit."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def stub_iterm2_transaction(monkeypatch):
    """Replace iterm2.Transaction with a no-op async context manager.

    Tests that want to verify Transaction usage explicitly should
    monkeypatch `mcp_server_iterm2.tools.read.iterm2.Transaction` with
    their own mock inside the test body.
    """

    @asynccontextmanager
    async def _noop(_conn):
        yield

    monkeypatch.setattr(
        "mcp_server_iterm2.tools.read.iterm2.Transaction",
        MagicMock(side_effect=lambda conn: _noop(conn)),
    )
