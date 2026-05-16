# mcp-server-iterm2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server exposing iTerm2 to agents for observation and non-destructive annotation (8 read tools + 5 write tools), distributed via PyPI as `mcp-server-iterm2`.

**Architecture:** stdio MCP server using FastMCP. On startup it requests an iTerm2 cookie via AppleScript, opens a persistent WebSocket connection via the official `iterm2` SDK, and serves tool calls. Caller's session (`$ITERM_SESSION_ID`) is the default for session-targeted tools, with optional explicit override. Background reconnect with exponential backoff handles iTerm2 quit/restart.

**Tech Stack:** Python 3.12+, `mcp` Python SDK (FastMCP), `iterm2` SDK, `uv`, `ruff`, `ty` (Astral), `pytest`. MIT license.

**Reference spec:** `docs/superpowers/specs/2026-05-16-mcp-server-iterm2-design.md`

**Repo:** `/Users/rob/Projects/Code/mcp-server-iterm2` (already initialized; spec committed on `main`).

---

## File Structure

Production code in `src/mcp_server_iterm2/`:

| File                | Responsibility                                                     |
| ------------------- | ------------------------------------------------------------------ |
| `__init__.py`       | Package version (`__version__ = "0.1.0"`)                          |
| `py.typed`          | PEP 561 marker (empty file) — signals package ships type info      |
| `errors.py`         | Exception types + `to_error_text()` for MCP error envelopes        |
| `cookie.py`         | `request_cookie()` shells out to osascript, returns cookie token   |
| `connection.py`     | `ITermClient` class — owns iTerm2 Connection + App, reconnect loop |
| `session.py`        | `resolve_session(app, session_id_arg, env_session_id) -> Session`  |
| `output_cursor.py`  | Opaque cursor encode/decode + `diff_since(line_info, last_seen)`   |
| `server.py`         | `create_server() -> FastMCP`, `main()` entry point                 |
| `tools/__init__.py` | (empty)                                                            |
| `tools/read.py`     | 8 read tools                                                       |
| `tools/write.py`    | 5 write tools                                                      |

Tests in `tests/`:

| File                              | Responsibility                                                 |
| --------------------------------- | -------------------------------------------------------------- |
| `__init__.py`                     | (empty)                                                        |
| `conftest.py`                     | Shared fixtures: `fake_app`, `fake_session`, `fake_connection` |
| `fixtures.py`                     | Factory functions for synthetic iTerm2 objects                 |
| `unit/__init__.py`                | (empty)                                                        |
| `unit/test_errors.py`             | Error envelope tests                                           |
| `unit/test_cookie.py`             | Cookie acquisition tests (mocked subprocess)                   |
| `unit/test_connection.py`         | Connection + reconnect tests (mocked SDK + fake clock)         |
| `unit/test_session.py`            | Session resolution tests                                       |
| `unit/test_output_cursor.py`      | Cursor encode/decode/diff tests                                |
| `unit/test_server.py`             | FastMCP server skeleton test                                   |
| `unit/test_tools_read.py`         | Read tool unit tests                                           |
| `unit/test_tools_write.py`        | Write tool unit tests                                          |
| `integration/__init__.py`         | (empty)                                                        |
| `integration/conftest.py`         | Live iTerm2 fixture                                            |
| `integration/test_integration.py` | End-to-end tests against real iTerm2                           |

Scaffolding/config (repo root):

| File                            | Responsibility                                    |
| ------------------------------- | ------------------------------------------------- |
| `pyproject.toml`                | Project metadata, deps, ruff + ty + pytest config |
| `.python-version`               | `3.12`                                            |
| `.gitignore`                    | Standard Python ignores                           |
| `LICENSE`                       | MIT                                               |
| `README.md`                     | Install, configure, first-run notes               |
| `CHANGELOG.md`                  | Keep-a-changelog format, starts at 0.1.0          |
| `scripts/smoke.py`              | Manual smoke test                                 |
| `.pre-commit-config.yaml`       | Ruff + ty + pytest unit hooks                     |
| `.github/workflows/ci.yml`      | Lint + typecheck + unit tests on 3.12/3.13        |
| `.github/workflows/publish.yml` | Tag-triggered PyPI publish                        |

---

## Task 1: Project scaffold

**Files:**

- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `LICENSE`, `README.md`, `CHANGELOG.md`, `src/mcp_server_iterm2/__init__.py`, `src/mcp_server_iterm2/py.typed`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`

- [ ] **Step 1: Create `.python-version`**

```plaintext
3.12
```

- [ ] **Step 2: Create `.gitignore`**

```plaintext
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.venv/
.pytest_cache/
.ruff_cache/
.ty_cache/
build/
dist/
.coverage
htmlcov/
.DS_Store
.remember/
```

- [ ] **Step 3: Create `LICENSE` (MIT)**

```plaintext
MIT License

Copyright (c) 2026 Rob Trame

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Create `pyproject.toml`**

```toml
[project]
name = "mcp-server-iterm2"
version = "0.1.0"
description = "MCP server exposing iTerm2 to agents for observation and non-destructive annotation."
readme = "README.md"
requires-python = ">=3.12"
license = { file = "LICENSE" }
authors = [{ name = "Rob Trame", email = "me@r6e.dev" }]
keywords = ["mcp", "iterm2", "claude", "ai", "agent"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: MacOS",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "mcp>=1.12",
    "iterm2>=2.7",
]

[project.scripts]
mcp-server-iterm2 = "mcp_server_iterm2.server:main"

[project.urls]
Homepage = "https://github.com/rtrame/mcp-server-iterm2"
Repository = "https://github.com/rtrame/mcp-server-iterm2"
Issues = "https://github.com/rtrame/mcp-server-iterm2/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_server_iterm2"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.7",
    "ty>=0.0.1a1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: requires a running iTerm2 (opt-in; not run by default)",
]
addopts = "-m 'not integration'"
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.format]
quote-style = "double"

[tool.ty]
# ty config; if ty stumbles on FastMCP decorators or iterm2 stubs,
# add narrowly-scoped ignores here. See docs/superpowers/specs.
```

- [ ] **Step 5: Create `README.md`**

````markdown
# mcp-server-iterm2

A Model Context Protocol (MCP) server that exposes iTerm2 to agents for **observation** and **non-destructive annotation**.

Agents can read sessions and decorate them (badge, title, tab color, user variables, notifications) but cannot inject keystrokes, close or spawn sessions, or otherwise alter the user's working environment.

## Install

```json
{
  "mcpServers": {
    "iterm2": {
      "command": "uvx",
      "args": ["mcp-server-iterm2"]
    }
  }
}
```

## First run

On first use, iTerm2 will prompt you to authorize the script's API access. Approve it once and subsequent runs are silent.

Status: 0.1.0 — see [CHANGELOG](CHANGELOG.md).

````

- [ ] **Step 6: Create `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-16

### Added
- Initial release.
````

- [ ] **Step 7: Create `src/mcp_server_iterm2/__init__.py`**

```python
"""mcp-server-iterm2: MCP server for iTerm2."""

__version__ = "0.1.0"
```

- [ ] **Step 8: Create `src/mcp_server_iterm2/py.typed`**

Empty file (PEP 561 marker).

- [ ] **Step 9: Create `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`**

All empty.

- [ ] **Step 10: Sync dependencies and verify tooling**

```bash
cd /Users/rob/Projects/Code/mcp-server-iterm2
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Expected:

- `uv sync` creates `.venv/` and installs deps
- `ruff check` passes (no Python files yet to lint besides `__init__.py`)
- `ruff format --check` passes
- `pytest` collects 0 tests, exits 0

If `ty>=0.0.1a1` is not on PyPI yet, pin to whatever Astral's currently-published version is. Run `uv run ty check src` and confirm it executes (errors about no files are fine).

- [ ] **Step 11: Commit**

```bash
cd /Users/rob/Projects/Code/mcp-server-iterm2
git add -A
git commit -m "chore: project scaffold (uv, ruff, ty, pytest, MIT)"
```

---

## Task 2: Errors module

**Files:**

- Create: `src/mcp_server_iterm2/errors.py`
- Test: `tests/unit/test_errors.py`

The error types and the helper that converts them into the text returned by tool calls. Tools never raise raw tracebacks; they always return an error envelope.

- [ ] **Step 1: Write the failing test**

`tests/unit/test_errors.py`:

```python
from mcp_server_iterm2.errors import (
    AuthDenied,
    Disconnected,
    ITermNotRunning,
    NoCurrentSession,
    SessionNotFound,
    to_error_text,
)


def test_iterm_not_running_message():
    assert to_error_text(ITermNotRunning()) == (
        "iTerm2 is not running. Start iTerm2 and try again."
    )


def test_auth_denied_message():
    assert to_error_text(AuthDenied()) == (
        "iTerm2 denied API authorization. "
        "Re-enable in iTerm2 → Preferences → General → Magic."
    )


def test_disconnected_message():
    assert to_error_text(Disconnected()) == "iTerm2 unavailable, reconnecting."


def test_no_current_session_message():
    assert to_error_text(NoCurrentSession()) == (
        "No current session — pass session_id or run the MCP server "
        "from inside an iTerm2 session."
    )


def test_session_not_found_message():
    err = SessionNotFound(session_id="abc-123")
    assert to_error_text(err) == "session_id abc-123 not found."


def test_unknown_exception_falls_through_as_internal_error():
    assert to_error_text(ValueError("oops")) == "Internal error: oops"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_errors.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_server_iterm2.errors'`.

- [ ] **Step 3: Write minimal implementation**

`src/mcp_server_iterm2/errors.py`:

```python
"""Exception types and tool-error formatting."""


class MCPIterm2Error(Exception):
    """Base for all expected errors surfaced to MCP tool callers."""


class ITermNotRunning(MCPIterm2Error):
    """iTerm2 process not running at server startup."""


class AuthDenied(MCPIterm2Error):
    """User declined the cookie authorization prompt."""


class Disconnected(MCPIterm2Error):
    """Connection to iTerm2 is currently down; reconnect in progress."""


class NoCurrentSession(MCPIterm2Error):
    """No session_id provided and ITERM_SESSION_ID is not set."""


class SessionNotFound(MCPIterm2Error):
    """A session_id was provided but does not match a live session."""

    def __init__(self, session_id: str) -> None:
        super().__init__(session_id)
        self.session_id = session_id


def to_error_text(err: BaseException) -> str:
    """Render an exception as actionable text for an MCP tool error response."""
    match err:
        case ITermNotRunning():
            return "iTerm2 is not running. Start iTerm2 and try again."
        case AuthDenied():
            return (
                "iTerm2 denied API authorization. "
                "Re-enable in iTerm2 → Preferences → General → Magic."
            )
        case Disconnected():
            return "iTerm2 unavailable, reconnecting."
        case NoCurrentSession():
            return (
                "No current session — pass session_id or run the MCP server "
                "from inside an iTerm2 session."
            )
        case SessionNotFound() as e:
            return f"session_id {e.session_id} not found."
        case _:
            return f"Internal error: {err}"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_errors.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/errors.py tests/unit/test_errors.py
git commit -m "feat: error types and tool-error text formatting"
```

---

## Task 3: Cookie acquisition

**Files:**

- Create: `src/mcp_server_iterm2/cookie.py`
- Test: `tests/unit/test_cookie.py`

Shells out to `osascript` to request an iTerm2 API cookie. Translates failures into `ITermNotRunning` / `AuthDenied`.

- [ ] **Step 1: Write the failing test**

`tests/unit/test_cookie.py`:

```python
import subprocess
from unittest.mock import patch

import pytest

from mcp_server_iterm2.cookie import request_cookie
from mcp_server_iterm2.errors import AuthDenied, ITermNotRunning


def _fake_completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=["osascript"], returncode=returncode, stdout=stdout, stderr=stderr
    )


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_returns_cookie_on_success(mock_run):
    mock_run.return_value = _fake_completed(stdout="abc123\n")
    assert request_cookie() == "abc123"


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_iterm_not_running_when_osascript_says_so(mock_run):
    mock_run.return_value = _fake_completed(
        returncode=1, stderr='execution error: iTerm2 got an error: Application isn’t running.'
    )
    with pytest.raises(ITermNotRunning):
        request_cookie()


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_auth_denied_when_user_rejects(mock_run):
    mock_run.return_value = _fake_completed(
        returncode=1, stderr="User did not authorize API access."
    )
    with pytest.raises(AuthDenied):
        request_cookie()


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_other_failure_reraised_as_authdenied(mock_run):
    # Conservative: any other non-zero exit on cookie request → AuthDenied.
    mock_run.return_value = _fake_completed(returncode=1, stderr="some other failure")
    with pytest.raises(AuthDenied):
        request_cookie()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_cookie.py -v
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/mcp_server_iterm2/cookie.py`:

```python
"""Request an iTerm2 API cookie via AppleScript."""

import subprocess

from mcp_server_iterm2.errors import AuthDenied, ITermNotRunning

_OSASCRIPT_COMMAND = [
    "osascript",
    "-e",
    'tell application "iTerm2" to request cookie',
]


def request_cookie() -> str:
    """Run osascript to request a one-time cookie.

    Returns the cookie string. Raises ITermNotRunning if iTerm2 is not
    running, or AuthDenied if the user rejects the prompt (or any other
    osascript failure occurs).
    """
    result = subprocess.run(  # noqa: S603 - fixed argv, no user input
        _OSASCRIPT_COMMAND,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    stderr = result.stderr.lower()
    if "isn’t running" in result.stderr or "application isn't running" in stderr:
        raise ITermNotRunning()
    raise AuthDenied()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_cookie.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/cookie.py tests/unit/test_cookie.py
git commit -m "feat: iTerm2 cookie acquisition via osascript"
```

---

## Task 4: Connection lifecycle

**Files:**

- Create: `src/mcp_server_iterm2/connection.py`
- Test: `tests/unit/test_connection.py`

`ITermClient` owns the persistent `iterm2.Connection` + `iterm2.App` pair. Sets `ITERM2_COOKIE` from `request_cookie()` and calls `iterm2.Connection.async_create()`. Exposes `connected` flag, `app` accessor, and a `start()` coroutine that runs a reconnect loop with exponential backoff.

- [ ] **Step 1: Write the failing test**

`tests/unit/test_connection.py`:

```python
import asyncio
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
    assert _backoff_seconds(5) == 30  # capped
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
    await client._connect_once()

    assert os.environ["ITERM2_COOKIE"] == "cookie123"
    assert client.connected is True
    assert client.app is fake_app
    mock_iterm2.Connection.async_create.assert_awaited_once()
    mock_iterm2.async_get_app.assert_awaited_once_with(fake_conn)


@pytest.mark.asyncio
async def test_require_app_raises_disconnected_when_not_connected():
    client = ITermClient()
    with pytest.raises(Disconnected):
        client.require_app()


@pytest.mark.asyncio
@patch("mcp_server_iterm2.connection.asyncio.sleep", new=AsyncMock())
@patch("mcp_server_iterm2.connection.request_cookie", return_value="cookie123")
@patch("mcp_server_iterm2.connection.iterm2")
async def test_run_reconnect_loop_retries_on_failure(mock_iterm2, _, _sleep_stub):
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
    # Run reconnect loop in background; stop it once we observe success.
    task = asyncio.create_task(client.run_reconnect_loop())
    for _ in range(50):
        if client.connected:
            break
        await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert client.connected is True
    assert calls["n"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_connection.py -v
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/mcp_server_iterm2/connection.py`:

```python
"""Persistent iTerm2 connection with reconnect."""

from __future__ import annotations

import asyncio
import logging
import os
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

    async def _connect_once(self) -> None:
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
                await self._connect_once()
                attempt = 0
                # Hold open. If iterm2 raises, we exit this await and retry.
                # (The iterm2 SDK does not currently surface disconnects via
                # an awaitable; in practice the SDK will raise on next call.)
                await asyncio.Event().wait()  # pragma: no cover
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._connection = None
                self._app = None
                delay = _backoff_seconds(attempt)
                log.warning("iterm2 connection failed (%s); retrying in %ss", exc, delay)
                attempt += 1
                await asyncio.sleep(delay)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_connection.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/connection.py tests/unit/test_connection.py
git commit -m "feat: persistent iTerm2 connection with exponential-backoff reconnect"
```

---

## Task 5: Session resolution

**Files:**

- Create: `src/mcp_server_iterm2/session.py`
- Test: `tests/unit/test_session.py`

Pure function: given the app, an optional explicit `session_id`, and the env var, return a Session or raise.

- [ ] **Step 1: Write the failing test**

`tests/unit/test_session.py`:

```python
from unittest.mock import MagicMock

import pytest

from mcp_server_iterm2.errors import NoCurrentSession, SessionNotFound
from mcp_server_iterm2.session import resolve_session


def _app_with(sessions: dict[str, MagicMock]) -> MagicMock:
    app = MagicMock()
    app.get_session_by_id = MagicMock(side_effect=lambda sid: sessions.get(sid))
    return app


def test_explicit_session_id_wins():
    s_explicit = MagicMock(name="explicit")
    app = _app_with({"explicit-id": s_explicit})
    result = resolve_session(app, session_id_arg="explicit-id", env_session_id="env-id")
    assert result is s_explicit


def test_falls_back_to_env_session_id():
    s_env = MagicMock(name="env")
    app = _app_with({"env-id": s_env})
    result = resolve_session(app, session_id_arg=None, env_session_id="env-id")
    assert result is s_env


def test_no_current_session_when_both_missing():
    app = _app_with({})
    with pytest.raises(NoCurrentSession):
        resolve_session(app, session_id_arg=None, env_session_id=None)


def test_no_current_session_when_env_is_empty_string():
    app = _app_with({})
    with pytest.raises(NoCurrentSession):
        resolve_session(app, session_id_arg=None, env_session_id="")


def test_session_not_found_raises_with_id():
    app = _app_with({})
    with pytest.raises(SessionNotFound) as exc:
        resolve_session(app, session_id_arg="missing-id", env_session_id=None)
    assert exc.value.session_id == "missing-id"


def test_session_not_found_for_stale_env_id():
    app = _app_with({})
    with pytest.raises(SessionNotFound) as exc:
        resolve_session(app, session_id_arg=None, env_session_id="stale-id")
    assert exc.value.session_id == "stale-id"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_session.py -v
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/mcp_server_iterm2/session.py`:

```python
"""Resolve a target Session from explicit argument, env, or error."""

from __future__ import annotations

from typing import Any

from mcp_server_iterm2.errors import NoCurrentSession, SessionNotFound


def resolve_session(
    app: Any, session_id_arg: str | None, env_session_id: str | None
) -> Any:
    """Return the session for session_id_arg if set, else env_session_id.

    Raises NoCurrentSession if neither is provided. Raises SessionNotFound
    if a provided id does not match a live session.
    """
    requested = session_id_arg or env_session_id or None
    if not requested:
        raise NoCurrentSession()
    session = app.get_session_by_id(requested)
    if session is None:
        raise SessionNotFound(requested)
    return session
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_session.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/session.py tests/unit/test_session.py
git commit -m "feat: session resolution from explicit arg, env, or error"
```

---

## Task 6: Output cursor

**Files:**

- Create: `src/mcp_server_iterm2/output_cursor.py`
- Test: `tests/unit/test_output_cursor.py`

Opaque cursor encoding for `get_recent_output`. Cursor is base64-encoded JSON `{"sid": <session_id>, "line": <absolute_line_number>}`. The diff function takes the current `overflow` and `count` from iTerm2 line info and returns the line range to fetch (or `None` if no new lines) along with the new cursor and an expired flag.

- [ ] **Step 1: Write the failing test**

`tests/unit/test_output_cursor.py`:

```python
import pytest

from mcp_server_iterm2.output_cursor import (
    CursorInvalid,
    decode_cursor,
    diff_since,
    encode_cursor,
)


def test_encode_decode_roundtrip():
    raw = encode_cursor(session_id="abc-123", line_number=42)
    assert decode_cursor(raw) == ("abc-123", 42)


def test_decode_invalid_string_raises():
    with pytest.raises(CursorInvalid):
        decode_cursor("not-a-real-cursor")


def test_decode_cursor_from_wrong_session_raises():
    raw = encode_cursor(session_id="abc-123", line_number=10)
    with pytest.raises(CursorInvalid):
        decode_cursor(raw, expected_session_id="other-id")


def test_diff_since_no_cursor_returns_last_screenful():
    # No prior cursor; line_count=200; should return the last 200 (all of them).
    result = diff_since(overflow=0, line_count=200, last_seen=None)
    assert result.first_line == 0
    assert result.last_line == 199
    assert result.cursor_expired is False
    assert result.new_last_seen == 199


def test_diff_since_advances_from_last_seen():
    # last_seen=99; current state: overflow=0, count=200 → lines 0..199 available.
    result = diff_since(overflow=0, line_count=200, last_seen=99)
    assert result.first_line == 100
    assert result.last_line == 199
    assert result.cursor_expired is False
    assert result.new_last_seen == 199


def test_diff_since_no_new_lines_returns_empty_range():
    result = diff_since(overflow=0, line_count=200, last_seen=199)
    assert result.first_line is None
    assert result.last_line is None
    assert result.new_last_seen == 199
    assert result.cursor_expired is False


def test_diff_since_cursor_expired_when_below_overflow():
    # Buffer is now lines 500..699; cursor at 100 is gone.
    result = diff_since(overflow=500, line_count=200, last_seen=100)
    assert result.first_line == 500
    assert result.last_line == 699
    assert result.cursor_expired is True
    assert result.new_last_seen == 699


def test_diff_since_empty_session_returns_empty():
    result = diff_since(overflow=0, line_count=0, last_seen=None)
    assert result.first_line is None
    assert result.last_line is None
    assert result.cursor_expired is False
    assert result.new_last_seen == -1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_output_cursor.py -v
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

`src/mcp_server_iterm2/output_cursor.py`:

```python
"""Opaque cursor encoding + scrollback diff logic for get_recent_output."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass


class CursorInvalid(ValueError):
    """The supplied cursor string could not be parsed or belongs to a different session."""


def encode_cursor(*, session_id: str, line_number: int) -> str:
    payload = json.dumps({"sid": session_id, "line": line_number}).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_cursor(cursor: str, *, expected_session_id: str | None = None) -> tuple[str, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        sid = data["sid"]
        line = int(data["line"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CursorInvalid(str(exc)) from exc
    if expected_session_id is not None and sid != expected_session_id:
        raise CursorInvalid("cursor session_id mismatch")
    return sid, line


@dataclass(frozen=True)
class DiffResult:
    """The range of absolute line numbers to fetch (inclusive), or None if no new lines."""

    first_line: int | None
    last_line: int | None
    new_last_seen: int
    cursor_expired: bool


def diff_since(*, overflow: int, line_count: int, last_seen: int | None) -> DiffResult:
    """Compute the range of new lines since last_seen.

    iTerm2 line numbering is monotonically increasing. The currently
    addressable range is [overflow, overflow + line_count - 1].
    """
    if line_count == 0:
        return DiffResult(None, None, -1, False)

    highest = overflow + line_count - 1
    lowest = overflow

    if last_seen is None:
        # First read: return the entire currently-available buffer.
        return DiffResult(lowest, highest, highest, False)

    if last_seen < lowest:
        # Cursor aged out; return everything we still have.
        return DiffResult(lowest, highest, highest, True)

    if last_seen >= highest:
        # Caller already saw everything.
        return DiffResult(None, None, last_seen, False)

    return DiffResult(last_seen + 1, highest, highest, False)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_output_cursor.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/output_cursor.py tests/unit/test_output_cursor.py
git commit -m "feat: opaque cursor and scrollback diff logic for get_recent_output"
```

---

## Task 7: MCP server skeleton + list_sessions tool

**Files:**

- Create: `src/mcp_server_iterm2/server.py`, `src/mcp_server_iterm2/tools/__init__.py`, `src/mcp_server_iterm2/tools/read.py`
- Test: `tests/conftest.py`, `tests/fixtures.py`, `tests/unit/test_server.py`, `tests/unit/test_tools_read.py`

This task gets the server end-to-end and implements the first tool. Subsequent tools just add `@mcp.tool()`-decorated functions in `tools/read.py` or `tools/write.py`.

- [ ] **Step 1: Write shared test fixtures**

`tests/fixtures.py`:

```python
"""Factory helpers for synthetic iTerm2 objects used in unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock


def make_session(
    *,
    session_id: str,
    name: str = "session",
    is_active: bool = False,
) -> MagicMock:
    s = MagicMock(name=f"session-{session_id}")
    s.session_id = session_id
    s.name = name
    s.is_active_synthetic = is_active  # purely for fixture wiring
    return s


def make_tab(
    *,
    tab_id: int,
    sessions: list[MagicMock],
    current: MagicMock | None = None,
) -> MagicMock:
    t = MagicMock(name=f"tab-{tab_id}")
    t.tab_id = tab_id
    t.sessions = sessions
    t.current_session = current or (sessions[0] if sessions else None)
    return t


def make_window(
    *,
    window_id: str,
    tabs: list[MagicMock],
    current: MagicMock | None = None,
) -> MagicMock:
    w = MagicMock(name=f"window-{window_id}")
    w.window_id = window_id
    w.tabs = tabs
    w.current_tab = current or (tabs[0] if tabs else None)
    return w


def make_app(
    *,
    windows: list[MagicMock],
    current_window: MagicMock | None = None,
) -> MagicMock:
    app = MagicMock(name="app")
    app.terminal_windows = windows
    app.current_terminal_window = current_window or (windows[0] if windows else None)

    sessions_by_id = {
        s.session_id: s for w in windows for t in w.tabs for s in t.sessions
    }
    app.get_session_by_id = lambda sid: sessions_by_id.get(sid)
    return app
```

`tests/conftest.py`:

```python
"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.fixtures import make_app, make_session, make_tab, make_window


@pytest.fixture
def simple_app() -> MagicMock:
    """One window, one tab, one session with id 'sess-1'."""
    s1 = make_session(session_id="sess-1", name="bash", is_active=True)
    t1 = make_tab(tab_id=1, sessions=[s1])
    w1 = make_window(window_id="win-1", tabs=[t1])
    return make_app(windows=[w1])
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_server.py`:

```python
from unittest.mock import MagicMock

from mcp_server_iterm2.server import create_server


def test_create_server_returns_fastmcp_with_expected_name():
    client = MagicMock()
    mcp = create_server(client=client)
    assert mcp.name == "iterm2"
```

`tests/unit/test_tools_read.py`:

```python
from unittest.mock import MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.read import list_sessions_impl


def test_list_sessions_returns_hierarchy(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    result = list_sessions_impl(client)
    assert result == {
        "windows": [
            {
                "window_id": "win-1",
                "tabs": [
                    {
                        "tab_id": 1,
                        "active": True,
                        "sessions": [
                            {
                                "session_id": "sess-1",
                                "name": "bash",
                                "active": True,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_list_sessions_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        list_sessions_impl(client)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_server.py tests/unit/test_tools_read.py -v
```

Expected: FAIL — modules not found.

- [ ] **Step 4: Write minimal implementation**

`src/mcp_server_iterm2/tools/__init__.py`:

```python
"""MCP tool implementations."""
```

`src/mcp_server_iterm2/tools/read.py`:

```python
"""Read-only tool implementations.

Each `*_impl(client, ...)` is pure-Python and unit-testable. The MCP
registration wrapper lives in `server.py` and adapts argument handling
and error translation.
"""

from __future__ import annotations

from typing import Any


def list_sessions_impl(client: Any) -> dict[str, Any]:
    """Return the windows → tabs → sessions hierarchy."""
    app = client.require_app()
    current_window = app.current_terminal_window
    current_window_id = getattr(current_window, "window_id", None)

    out_windows = []
    for window in app.terminal_windows:
        current_tab = window.current_tab
        current_tab_id = getattr(current_tab, "tab_id", None)
        out_tabs = []
        for tab in window.tabs:
            current_session = tab.current_session
            current_session_id = getattr(current_session, "session_id", None)
            out_sessions = [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "active": s.session_id == current_session_id
                    and tab.tab_id == current_tab_id
                    and window.window_id == current_window_id,
                }
                for s in tab.sessions
            ]
            out_tabs.append(
                {
                    "tab_id": tab.tab_id,
                    "active": tab.tab_id == current_tab_id
                    and window.window_id == current_window_id,
                    "sessions": out_sessions,
                }
            )
        out_windows.append({"window_id": window.window_id, "tabs": out_tabs})
    return {"windows": out_windows}
```

`src/mcp_server_iterm2/server.py`:

```python
"""MCP server setup and main entry point."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server_iterm2.connection import ITermClient
from mcp_server_iterm2.errors import (
    Disconnected,
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all unit tests pass.

- [ ] **Step 6: Smoke-check the entry point**

```bash
uv run mcp-server-iterm2 --help 2>&1 | head -5 || true
```

`uvx`-style entry point doesn't accept `--help` by default; we just want to confirm the script exists and starts (and exits when stdin closes). If you have iTerm2 running, this should hang waiting on stdin; cancel with Ctrl-C. If iTerm2 is not running, expect a clean shutdown after the first-connect timeout.

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server_iterm2/server.py src/mcp_server_iterm2/tools/ \
        tests/conftest.py tests/fixtures.py \
        tests/unit/test_server.py tests/unit/test_tools_read.py
git commit -m "feat: MCP server skeleton with list_sessions tool"
```

---

## Task 8: get_session_info tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`
- Modify: `tests/unit/test_tools_read.py`

Returns session metadata: title (name), working directory, profile name, badge, dimensions, TTY path. Pulls from iTerm2 session variables (`session.path`, `session.username`, etc.) and `session.async_get_profile()`.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
import asyncio
from unittest.mock import AsyncMock

from mcp_server_iterm2.tools.read import get_session_info_impl


def _async_value(v):
    f = asyncio.get_event_loop().create_future() if False else None  # placeholder
    return AsyncMock(return_value=v)


def test_get_session_info_returns_expected_fields(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_variable = AsyncMock(side_effect=lambda key: {
        "session.path": "/Users/rob",
        "user.badge": "WORK",
        "session.tty": "/dev/ttys001",
    }.get(key))
    profile = MagicMock()
    profile.name = "Default"
    session.async_get_profile = AsyncMock(return_value=profile)
    session.grid_size = MagicMock(return_value=MagicMock(width=120, height=40))
    session.name = "bash"

    result = asyncio.run(get_session_info_impl(client, session_id_arg="sess-1", env_session_id=None))

    assert result == {
        "session_id": "sess-1",
        "name": "bash",
        "working_directory": "/Users/rob",
        "profile_name": "Default",
        "badge": "WORK",
        "tty": "/dev/ttys001",
        "dimensions": {"cols": 120, "rows": 40},
    }
```

(Note: the existing tests at the top of the file already import `MagicMock` via the test we wrote in Task 7; ensure imports cover `AsyncMock`. If not, add `from unittest.mock import AsyncMock, MagicMock` at the top.)

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_get_session_info_returns_expected_fields -v
```

Expected: FAIL — `get_session_info_impl` not defined.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
from mcp_server_iterm2.session import resolve_session


async def get_session_info_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    profile = await session.async_get_profile()
    grid = session.grid_size()
    return {
        "session_id": session.session_id,
        "name": session.name,
        "working_directory": await session.async_get_variable("session.path"),
        "profile_name": profile.name,
        "badge": await session.async_get_variable("user.badge"),
        "tty": await session.async_get_variable("session.tty"),
        "dimensions": {"cols": grid.width, "rows": grid.height},
    }
```

Register the tool in `src/mcp_server_iterm2/server.py` inside `create_server`, after the existing `list_sessions` registration:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_read.py
git commit -m "feat: get_session_info tool"
```

---

## Task 9: get_screen_contents tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_read.py`

Returns the visible buffer text plus cursor position. Uses `session.async_get_screen_contents()`, which returns a `ScreenContents` with `cursor_coord`, `number_of_lines`, and `line(i)` for each row.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
from mcp_server_iterm2.tools.read import get_screen_contents_impl


def test_get_screen_contents_returns_lines_and_cursor(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")

    contents = MagicMock()
    contents.number_of_lines = 2
    line0 = MagicMock(string="hello")
    line1 = MagicMock(string="world")
    contents.line = MagicMock(side_effect=[line0, line1])
    contents.cursor_coord = MagicMock(x=3, y=1)
    session.async_get_screen_contents = AsyncMock(return_value=contents)

    result = asyncio.run(get_screen_contents_impl(
        client, session_id_arg="sess-1", env_session_id=None
    ))
    assert result == {
        "text": "hello\nworld",
        "cursor": {"row": 1, "col": 3},
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_get_screen_contents_returns_lines_and_cursor -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
async def get_screen_contents_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    contents = await session.async_get_screen_contents()
    lines = [contents.line(i).string for i in range(contents.number_of_lines)]
    return {
        "text": "\n".join(lines),
        "cursor": {"row": contents.cursor_coord.y, "col": contents.cursor_coord.x},
    }
```

Register in `server.py` inside `create_server`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_read.py
git commit -m "feat: get_screen_contents tool"
```

---

## Task 10: get_selection tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_read.py`

Returns currently-selected text via `session.async_get_selection_text()`.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
from mcp_server_iterm2.tools.read import get_selection_impl


def test_get_selection_returns_text(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_selection_text = AsyncMock(return_value="copied text")
    result = asyncio.run(get_selection_impl(
        client, session_id_arg="sess-1", env_session_id=None
    ))
    assert result == {"text": "copied text"}


def test_get_selection_empty(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_selection_text = AsyncMock(return_value="")
    result = asyncio.run(get_selection_impl(
        client, session_id_arg="sess-1", env_session_id=None
    ))
    assert result == {"text": ""}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_get_selection_returns_text -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
async def get_selection_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    text = await session.async_get_selection_text()
    return {"text": text}
```

Register in `server.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_read.py
git commit -m "feat: get_selection tool"
```

---

## Task 11: get_scrollback tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_read.py`

Returns the last N lines of scrollback. Uses `session.async_get_line_info()` to find the addressable range, then `session.async_get_contents(first_line, count)` to fetch the lines.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
from mcp_server_iterm2.tools.read import get_scrollback_impl


def _line_info(overflow: int, count: int):
    info = MagicMock()
    info.overflow = overflow
    info.number_of_lines = count
    return info


def test_get_scrollback_default_returns_last_200_lines_when_available(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, count=1000))

    contents = MagicMock()
    contents.number_of_lines = 200
    contents.line = MagicMock(side_effect=[MagicMock(string=f"line{i}") for i in range(200)])
    session.async_get_contents = AsyncMock(return_value=contents)

    result = asyncio.run(get_scrollback_impl(
        client, session_id_arg="sess-1", env_session_id=None, n_lines=200
    ))
    # Most recent 200 lines, in order.
    assert result["text"].startswith("line0\nline1")
    assert result["text"].endswith("line199")
    # async_get_contents should have been called for the last 200 lines:
    # range starts at (overflow + count - 200) = 800
    session.async_get_contents.assert_awaited_once_with(800, 200)


def test_get_scrollback_capped_at_5000(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, count=100000))
    contents = MagicMock()
    contents.number_of_lines = 5000
    contents.line = MagicMock(side_effect=[MagicMock(string="x") for _ in range(5000)])
    session.async_get_contents = AsyncMock(return_value=contents)

    asyncio.run(get_scrollback_impl(
        client, session_id_arg="sess-1", env_session_id=None, n_lines=999999
    ))
    # cap kicks in: requested count == 5000, starting at (100000 - 5000) = 95000
    session.async_get_contents.assert_awaited_once_with(95000, 5000)


def test_get_scrollback_when_fewer_lines_than_requested(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, count=10))
    contents = MagicMock()
    contents.number_of_lines = 10
    contents.line = MagicMock(side_effect=[MagicMock(string=f"L{i}") for i in range(10)])
    session.async_get_contents = AsyncMock(return_value=contents)

    asyncio.run(get_scrollback_impl(
        client, session_id_arg="sess-1", env_session_id=None, n_lines=200
    ))
    session.async_get_contents.assert_awaited_once_with(0, 10)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_get_scrollback_default_returns_last_200_lines_when_available -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
SCROLLBACK_MAX = 5000


async def get_scrollback_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    n_lines: int = 200,
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    info = await session.async_get_line_info()
    overflow = info.overflow
    total = info.number_of_lines
    take = min(max(n_lines, 0), SCROLLBACK_MAX, total)
    if take == 0:
        return {"text": ""}
    start = overflow + total - take
    contents = await session.async_get_contents(start, take)
    lines = [contents.line(i).string for i in range(contents.number_of_lines)]
    return {"text": "\n".join(lines)}
```

Register in `server.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_read.py
git commit -m "feat: get_scrollback tool"
```

---

## Task 12: get_recent_output tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_read.py`

Returns output since a cursor marker. Uses the cursor module from Task 6 and `session.async_get_contents(start, count)` from Task 11.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
from mcp_server_iterm2.output_cursor import decode_cursor, encode_cursor
from mcp_server_iterm2.tools.read import get_recent_output_impl


def test_get_recent_output_no_cursor_returns_last_screenful(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, count=5))

    contents = MagicMock()
    contents.number_of_lines = 5
    contents.line = MagicMock(side_effect=[MagicMock(string=f"L{i}") for i in range(5)])
    session.async_get_contents = AsyncMock(return_value=contents)

    result = asyncio.run(get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=None
    ))
    assert result["text"] == "L0\nL1\nL2\nL3\nL4"
    assert result["cursor_expired"] is False
    sid, line = decode_cursor(result["cursor"])
    assert (sid, line) == ("sess-1", 4)


def test_get_recent_output_advances_from_cursor(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, count=10))

    contents = MagicMock()
    contents.number_of_lines = 5
    contents.line = MagicMock(side_effect=[MagicMock(string=f"L{i}") for i in range(5, 10)])
    session.async_get_contents = AsyncMock(return_value=contents)

    prior = encode_cursor(session_id="sess-1", line_number=4)
    result = asyncio.run(get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=prior
    ))
    assert result["text"] == "L5\nL6\nL7\nL8\nL9"
    assert result["cursor_expired"] is False
    session.async_get_contents.assert_awaited_once_with(5, 5)


def test_get_recent_output_no_new_lines(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, count=10))
    session.async_get_contents = AsyncMock()

    prior = encode_cursor(session_id="sess-1", line_number=9)
    result = asyncio.run(get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=prior
    ))
    assert result["text"] == ""
    assert result["cursor_expired"] is False
    session.async_get_contents.assert_not_awaited()


def test_get_recent_output_cursor_expired(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    # Buffer is now lines 500..699; old cursor at 100 is expired.
    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=500, count=200))
    contents = MagicMock()
    contents.number_of_lines = 200
    contents.line = MagicMock(side_effect=[MagicMock(string=f"L{i}") for i in range(500, 700)])
    session.async_get_contents = AsyncMock(return_value=contents)

    prior = encode_cursor(session_id="sess-1", line_number=100)
    result = asyncio.run(get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=prior
    ))
    assert result["cursor_expired"] is True
    session.async_get_contents.assert_awaited_once_with(500, 200)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_get_recent_output_no_cursor_returns_last_screenful -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
from mcp_server_iterm2.output_cursor import (
    decode_cursor,
    diff_since,
    encode_cursor,
)


async def get_recent_output_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    cursor: str | None,
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    sid = session.session_id

    last_seen: int | None
    if cursor is None:
        last_seen = None
    else:
        _, last_seen = decode_cursor(cursor, expected_session_id=sid)

    info = await session.async_get_line_info()
    diff = diff_since(
        overflow=info.overflow, line_count=info.number_of_lines, last_seen=last_seen
    )

    if diff.first_line is None:
        return {
            "text": "",
            "cursor": encode_cursor(session_id=sid, line_number=diff.new_last_seen),
            "cursor_expired": diff.cursor_expired,
        }

    count = diff.last_line - diff.first_line + 1
    contents = await session.async_get_contents(diff.first_line, count)
    lines = [contents.line(i).string for i in range(contents.number_of_lines)]
    return {
        "text": "\n".join(lines),
        "cursor": encode_cursor(session_id=sid, line_number=diff.new_last_seen),
        "cursor_expired": diff.cursor_expired,
    }
```

Register in `server.py`:

```python
    @mcp.tool()
    async def get_recent_output(
        session_id: str | None = None, cursor: str | None = None
    ) -> dict[str, Any]:
        """Return output since the given cursor (or last screenful if no cursor)."""
        try:
            return await read_tools.get_recent_output_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                cursor=cursor,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_read.py
git commit -m "feat: get_recent_output tool with cursor-based diffing"
```

---

## Task 13: get_variable tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_read.py`

Reads a variable by fully-qualified name. The scope prefix (`session.`, `tab.`, `window.`, `user.`) determines which object the call routes to.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
from mcp_server_iterm2.tools.read import get_variable_impl


def test_get_variable_session_scope(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_variable = AsyncMock(return_value="zsh")
    result = asyncio.run(get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="session.username"
    ))
    assert result == {"name": "session.username", "value": "zsh"}
    session.async_get_variable.assert_awaited_once_with("session.username")


def test_get_variable_user_scope(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_get_variable = AsyncMock(return_value="WORK")
    result = asyncio.run(get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="user.badge"
    ))
    assert result == {"name": "user.badge", "value": "WORK"}


def test_get_variable_tab_scope_routes_to_tab(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    # Wire the containing tab via app.get_tab_by_id
    tab = MagicMock()
    tab.async_get_variable = AsyncMock(return_value="42")
    simple_app.get_tab_by_id = MagicMock(return_value=tab)
    # session needs a reference to its tab via app lookup; we expose tab_id on session
    session.tab_id = 1

    result = asyncio.run(get_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None, name="tab.foo"
    ))
    assert result == {"name": "tab.foo", "value": "42"}
    tab.async_get_variable.assert_awaited_once_with("tab.foo")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_get_variable_session_scope -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
async def get_variable_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    name: str,
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    if name.startswith("tab."):
        tab = app.get_tab_by_id(session.tab_id)
        value = await tab.async_get_variable(name)
    elif name.startswith("window."):
        tab = app.get_tab_by_id(session.tab_id)
        window = app.get_window_for_tab(tab.tab_id)
        value = await window.async_get_variable(name)
    else:
        # session.* and user.* both live on the session
        value = await session.async_get_variable(name)
    return {"name": name, "value": value}
```

Register in `server.py`:

```python
    @mcp.tool()
    async def get_variable(
        name: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Read a variable by fully-qualified name (e.g. session.path, user.badge)."""
        try:
            return await read_tools.get_variable_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                name=name,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_read.py
git commit -m "feat: get_variable tool with scope-aware routing"
```

---

## Task 14: list_profiles tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_read.py`

Lists iTerm2 profiles via `iterm2.PartialProfile.async_query(connection)`.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_read.py`:

```python
from unittest.mock import patch

from mcp_server_iterm2.tools.read import list_profiles_impl


@patch("mcp_server_iterm2.tools.read.iterm2")
def test_list_profiles_returns_name_and_guid(mock_iterm2):
    p1 = MagicMock()
    p1.name = "Default"
    p1.guid = "guid-1"
    p2 = MagicMock()
    p2.name = "Dark"
    p2.guid = "guid-2"
    mock_iterm2.PartialProfile.async_query = AsyncMock(return_value=[p1, p2])

    client = MagicMock()
    client.require_connection = MagicMock(return_value="<conn>")
    result = asyncio.run(list_profiles_impl(client))
    assert result == {
        "profiles": [
            {"name": "Default", "guid": "guid-1"},
            {"name": "Dark", "guid": "guid-2"},
        ]
    }
    mock_iterm2.PartialProfile.async_query.assert_awaited_once_with("<conn>")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_read.py::test_list_profiles_returns_name_and_guid -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Add a `require_connection` accessor to `ITermClient` in `src/mcp_server_iterm2/connection.py`:

```python
    def require_connection(self) -> Any:
        if self._connection is None:
            raise Disconnected()
        return self._connection
```

Append to `src/mcp_server_iterm2/tools/read.py`:

```python
import iterm2  # type: ignore[import-untyped]


async def list_profiles_impl(client: Any) -> dict[str, Any]:
    conn = client.require_connection()
    profiles = await iterm2.PartialProfile.async_query(conn)
    return {
        "profiles": [{"name": p.name, "guid": p.guid} for p in profiles]
    }
```

Register in `server.py`:

```python
    @mcp.tool()
    async def list_profiles() -> dict[str, Any]:
        """List available iTerm2 profiles by name and GUID."""
        try:
            return await read_tools.list_profiles_impl(client)
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/connection.py \
        src/mcp_server_iterm2/server.py tests/unit/test_tools_read.py
git commit -m "feat: list_profiles tool"
```

---

## Task 15: set_badge tool

**Files:**

- Create: `tests/unit/test_tools_write.py`
- Create: `src/mcp_server_iterm2/tools/write.py`
- Modify: `src/mcp_server_iterm2/server.py`

iTerm2's badge is set by writing to the session's `user.badge` variable. The badge format in the user's profile must include `\(user.badge)` for it to render (documented in README).

- [ ] **Step 1: Write the failing test**

`tests/unit/test_tools_write.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_iterm2.errors import Disconnected
from mcp_server_iterm2.tools.write import set_badge_impl


def test_set_badge_writes_user_badge_variable(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_variable = AsyncMock()

    result = asyncio.run(set_badge_impl(
        client, session_id_arg="sess-1", env_session_id=None, text="WORKING"
    ))
    assert result == {"ok": True, "badge": "WORKING"}
    session.async_set_variable.assert_awaited_once_with("user.badge", "WORKING")


def test_set_badge_propagates_disconnected():
    client = MagicMock()
    client.require_app.side_effect = Disconnected()
    with pytest.raises(Disconnected):
        asyncio.run(set_badge_impl(
            client, session_id_arg="sess-1", env_session_id=None, text="x"
        ))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_write.py -v
```

Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

`src/mcp_server_iterm2/tools/write.py`:

```python
"""Non-destructive write tool implementations."""

from __future__ import annotations

from typing import Any

from mcp_server_iterm2.session import resolve_session


async def set_badge_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    text: str,
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_variable("user.badge", text)
    return {"ok": True, "badge": text}
```

Add to `server.py`:

```python
from mcp_server_iterm2.tools import write as write_tools
```

and inside `create_server`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_write.py
git commit -m "feat: set_badge tool"
```

---

## Task 16: set_title tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_write.py`

Calls `session.async_set_name(name)`. Whether iTerm2 renders the new title depends on the profile's title settings — documented in README, not the tool's problem.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_write.py`:

```python
from mcp_server_iterm2.tools.write import set_title_impl


def test_set_title_calls_async_set_name(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_name = AsyncMock()

    result = asyncio.run(set_title_impl(
        client, session_id_arg="sess-1", env_session_id=None, title="My Session"
    ))
    assert result == {"ok": True, "title": "My Session"}
    session.async_set_name.assert_awaited_once_with("My Session")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_write.py::test_set_title_calls_async_set_name -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/write.py`:

```python
async def set_title_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    title: str,
) -> dict[str, Any]:
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_name(title)
    return {"ok": True, "title": title}
```

Register in `server.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_write.py
git commit -m "feat: set_title tool"
```

---

## Task 17: set_tab_color tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_write.py`

Uses `iterm2.LocalWriteOnlyProfile` + `iterm2.Color(r, g, b)` + `session.async_set_profile_properties()`.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_write.py`:

```python
from unittest.mock import patch

from mcp_server_iterm2.tools.write import set_tab_color_impl


@patch("mcp_server_iterm2.tools.write.iterm2")
def test_set_tab_color_writes_profile_properties(mock_iterm2, simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_profile_properties = AsyncMock()

    fake_profile = MagicMock()
    mock_iterm2.LocalWriteOnlyProfile.return_value = fake_profile
    fake_color = MagicMock()
    mock_iterm2.Color.return_value = fake_color

    result = asyncio.run(set_tab_color_impl(
        client, session_id_arg="sess-1", env_session_id=None, r=255, g=128, b=64
    ))
    assert result == {"ok": True, "rgb": [255, 128, 64]}
    mock_iterm2.Color.assert_called_once_with(255, 128, 64)
    fake_profile.set_tab_color.assert_called_once_with(fake_color)
    fake_profile.set_use_tab_color.assert_called_once_with(True)
    session.async_set_profile_properties.assert_awaited_once_with(fake_profile)


def test_set_tab_color_rejects_out_of_range_values(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        asyncio.run(set_tab_color_impl(
            client, session_id_arg="sess-1", env_session_id=None, r=300, g=0, b=0
        ))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_write.py::test_set_tab_color_writes_profile_properties -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/write.py`:

```python
import iterm2  # type: ignore[import-untyped]


async def set_tab_color_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    r: int,
    g: int,
    b: int,
) -> dict[str, Any]:
    for name, v in (("r", r), ("g", g), ("b", b)):
        if not (0 <= v <= 255):
            raise ValueError(f"{name}={v} out of range; expected 0-255")
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_tab_color(iterm2.Color(r, g, b))
    profile.set_use_tab_color(True)
    await session.async_set_profile_properties(profile)
    return {"ok": True, "rgb": [r, g, b]}
```

Register in `server.py`:

```python
    @mcp.tool()
    async def set_tab_color(
        r: int, g: int, b: int, session_id: str | None = None
    ) -> dict[str, Any]:
        """Set the tab tint as RGB (each component 0-255)."""
        try:
            return await write_tools.set_tab_color_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                r=r,
                g=g,
                b=b,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_write.py
git commit -m "feat: set_tab_color tool"
```

---

## Task 18: set_user_variable tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_write.py`

Only `user.*` variables can be set per iTerm2 API. We enforce the prefix to give a clean error if the caller forgets it.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_write.py`:

```python
from mcp_server_iterm2.tools.write import set_user_variable_impl


def test_set_user_variable_writes(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_variable = AsyncMock()

    result = asyncio.run(set_user_variable_impl(
        client, session_id_arg="sess-1", env_session_id=None,
        name="user.task", value="refactor",
    ))
    assert result == {"ok": True, "name": "user.task", "value": "refactor"}
    session.async_set_variable.assert_awaited_once_with("user.task", "refactor")


def test_set_user_variable_rejects_non_user_prefix(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        asyncio.run(set_user_variable_impl(
            client, session_id_arg="sess-1", env_session_id=None,
            name="session.path", value="oops",
        ))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_write.py::test_set_user_variable_writes -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/write.py`:

```python
async def set_user_variable_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    name: str,
    value: str,
) -> dict[str, Any]:
    if not name.startswith("user."):
        raise ValueError(
            f"variable name must start with 'user.' (got {name!r})"
        )
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_variable(name, value)
    return {"ok": True, "name": name, "value": value}
```

Register in `server.py`:

```python
    @mcp.tool()
    async def set_user_variable(
        name: str, value: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Set a user-scoped session variable. Name must start with 'user.'."""
        try:
            return await write_tools.set_user_variable_impl(
                client,
                session_id_arg=session_id,
                env_session_id=_env_session_id(),
                name=name,
                value=value,
            )
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_write.py
git commit -m "feat: set_user_variable tool"
```

---

## Task 19: post_notification tool

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`, `src/mcp_server_iterm2/server.py`, `tests/unit/test_tools_write.py`

Posts a macOS notification via `osascript -e 'display notification ...'`. iTerm2 SDK does not expose user-notification posting; we use the macOS-native path.

- [ ] **Step 1: Add the failing test**

Append to `tests/unit/test_tools_write.py`:

```python
import subprocess

from mcp_server_iterm2.tools.write import post_notification_impl


@patch("mcp_server_iterm2.tools.write.subprocess.run")
def test_post_notification_invokes_osascript(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["osascript"], returncode=0, stdout="", stderr=""
    )
    result = asyncio.run(post_notification_impl(
        title="Done", body="The task is complete."
    ))
    assert result == {"ok": True}
    args, _ = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "osascript"
    # The full applescript text contains both the title and body.
    joined = " ".join(cmd)
    assert "The task is complete." in joined
    assert "Done" in joined


@patch("mcp_server_iterm2.tools.write.subprocess.run")
def test_post_notification_propagates_osascript_failure(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["osascript"], returncode=1, stdout="", stderr="failed"
    )
    with pytest.raises(RuntimeError):
        asyncio.run(post_notification_impl(title="X", body="Y"))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_tools_write.py::test_post_notification_invokes_osascript -v
```

Expected: FAIL.

- [ ] **Step 3: Add the implementation**

Append to `src/mcp_server_iterm2/tools/write.py`:

```python
import shlex
import subprocess


async def post_notification_impl(*, title: str, body: str) -> dict[str, Any]:
    # AppleScript string-literal escape: backslash + double-quote.
    def _escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    script = (
        f'display notification "{_escape(body)}" '
        f'with title "{_escape(title)}"'
    )
    result = subprocess.run(  # noqa: S603 - argv fixed; body is user-supplied but escaped
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip() or 'unknown error'}")
    _ = shlex  # kept for readers; not used at runtime — remove if linter complains
    return {"ok": True}
```

(Drop the `_ = shlex` placeholder and the `import shlex` line if `ruff` flags unused; they are there only as a hint that AppleScript escaping is intentionally distinct from shell escaping. If ruff complains, just remove both.)

Register in `server.py`:

```python
    @mcp.tool()
    async def post_notification(title: str, body: str) -> dict[str, Any]:
        """Post a macOS notification (banner) with the given title and body."""
        try:
            return await write_tools.post_notification_impl(title=title, body=body)
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py src/mcp_server_iterm2/server.py \
        tests/unit/test_tools_write.py
git commit -m "feat: post_notification tool via osascript"
```

---

## Task 20: README + CHANGELOG polish

**Files:**

- Modify: `README.md`, `CHANGELOG.md`

The README from Task 1 was a placeholder stub. Now that all tools exist, write the real one.

- [ ] **Step 1: Replace `README.md` with full content**

````markdown
# mcp-server-iterm2

A Model Context Protocol (MCP) server that exposes iTerm2 to agents for **observation** and **non-destructive annotation**. Agents can inspect sessions and decorate them (badge, title, tab color, user variables, notifications) but cannot inject keystrokes, close or spawn sessions, or otherwise alter the user's working environment.

## Install

Configure your MCP client (e.g. Claude Desktop, Claude Code):

```json
{
  "mcpServers": {
    "iterm2": {
      "command": "uvx",
      "args": ["mcp-server-iterm2"]
    }
  }
}
```

Requires macOS, iTerm2, and [`uv`](https://docs.astral.sh/uv/) installed.

## First run

On first invocation, iTerm2 prompts you to authorize API access for the script. Approve it. Subsequent runs are silent.

If you previously denied access: iTerm2 → Preferences → General → Magic → enable "Python API" and remove `mcp-server-iterm2` from the denial list.

## Tools

### Read

| Tool                  | Description                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `list_sessions`       | Hierarchy of windows → tabs → sessions                                      |
| `get_session_info`    | Title, working dir, profile, badge, dimensions, TTY                         |
| `get_screen_contents` | Visible buffer + cursor position                                            |
| `get_scrollback`      | Last N lines (default 200, max 5000)                                        |
| `get_recent_output`   | Output since a cursor marker (cursor-based pagination)                      |
| `get_selection`       | Currently-selected text                                                     |
| `get_variable`        | Read a variable by fully-qualified name (e.g. `session.path`, `user.badge`) |
| `list_profiles`       | Available profiles by name and GUID                                         |

### Write (non-destructive)

| Tool                | Description                      |
| ------------------- | -------------------------------- |
| `set_badge`         | Set session badge text           |
| `set_title`         | Override session title           |
| `set_tab_color`     | Tint the tab (RGB 0-255)         |
| `set_user_variable` | Set a `user.*` session variable  |
| `post_notification` | Post a macOS notification banner |

Every session-targeted tool accepts an optional `session_id`. If omitted, the server uses `$ITERM_SESSION_ID` from its environment — which works automatically when the agent runs inside iTerm2.

## Notes on rendering

- **Badge:** for `set_badge` to display anything, your iTerm2 profile's badge format must include `\(user.badge)`. Configure in iTerm2 → Profiles → General → Badge.
- **Title:** whether a `set_title` override sticks depends on the profile's "Allow terminal apps to change title" and "Title Components" settings. The server always sets the override; iTerm2 controls the rendering.
- **Notifications:** routed through macOS via `osascript`. Make sure Terminal/iTerm2 notifications are allowed in System Settings if banners don't appear.

## Excluded by design

For safety, these are not exposed: `send_text`/keystroke injection, closing or spawning sessions/tabs/windows, splitting panes, focus changes, broadcasting input.

## License

MIT.

````

- [ ] **Step 2: Update `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-16

### Added
- Initial release.
- Persistent iTerm2 connection with exponential-backoff reconnect.
- 8 read tools: `list_sessions`, `get_session_info`, `get_screen_contents`,
  `get_scrollback`, `get_recent_output`, `get_selection`, `get_variable`,
  `list_profiles`.
- 5 non-destructive write tools: `set_badge`, `set_title`, `set_tab_color`,
  `set_user_variable`, `post_notification`.
- Cursor-based pagination for `get_recent_output` with stale-cursor detection.
- Default session resolution from `$ITERM_SESSION_ID` with explicit
  `session_id` override.
````

- [ ] **Step 3: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: full README and CHANGELOG for 0.1.0"
```

---

## Task 21: Smoke script

**Files:**

- Create: `scripts/smoke.py`

Runs every public tool once against the user's current iTerm2 session and prints a pass/fail summary. Requires iTerm2 running and an `ITERM_SESSION_ID` (set automatically when run inside iTerm2).

- [ ] **Step 1: Create `scripts/smoke.py`**

```python
"""Manual smoke test: exercises every tool against the current iTerm2 session.

Run from inside an iTerm2 session:

    uv run python scripts/smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp_server_iterm2.connection import ITermClient
from mcp_server_iterm2.tools import read, write


async def main() -> int:
    sid = os.environ.get("ITERM_SESSION_ID")
    if not sid:
        print("ERROR: ITERM_SESSION_ID is not set. Run this from inside an iTerm2 session.")
        return 1

    client = ITermClient()
    await client._connect_once()
    passes = 0
    failures: list[tuple[str, str]] = []

    async def _run(label: str, coro_factory):
        nonlocal passes
        try:
            value = await coro_factory()
        except Exception as e:
            failures.append((label, repr(e)))
            print(f"FAIL  {label:<24} {e!r}")
            return
        passes += 1
        preview = repr(value)
        if len(preview) > 80:
            preview = preview[:77] + "..."
        print(f"PASS  {label:<24} {preview}")

    await _run("list_sessions", lambda: asyncio.coroutine(read.list_sessions_impl)(client))
    await _run("get_session_info", lambda: read.get_session_info_impl(
        client, session_id_arg=sid, env_session_id=None
    ))
    await _run("get_screen_contents", lambda: read.get_screen_contents_impl(
        client, session_id_arg=sid, env_session_id=None
    ))
    await _run("get_scrollback", lambda: read.get_scrollback_impl(
        client, session_id_arg=sid, env_session_id=None
    ))
    await _run("get_recent_output", lambda: read.get_recent_output_impl(
        client, session_id_arg=sid, env_session_id=None, cursor=None
    ))
    await _run("get_selection", lambda: read.get_selection_impl(
        client, session_id_arg=sid, env_session_id=None
    ))
    await _run("get_variable", lambda: read.get_variable_impl(
        client, session_id_arg=sid, env_session_id=None, name="session.path"
    ))
    await _run("list_profiles", lambda: read.list_profiles_impl(client))

    await _run("set_badge", lambda: write.set_badge_impl(
        client, session_id_arg=sid, env_session_id=None, text="smoke"
    ))
    await _run("set_title", lambda: write.set_title_impl(
        client, session_id_arg=sid, env_session_id=None, title="smoke test"
    ))
    await _run("set_tab_color", lambda: write.set_tab_color_impl(
        client, session_id_arg=sid, env_session_id=None, r=80, g=160, b=240
    ))
    await _run("set_user_variable", lambda: write.set_user_variable_impl(
        client, session_id_arg=sid, env_session_id=None,
        name="user.smoke", value="ok",
    ))
    await _run("post_notification", lambda: write.post_notification_impl(
        title="smoke", body="all tools exercised"
    ))

    total = passes + len(failures)
    print(f"\n{passes}/{total} passed; {len(failures)} failed.")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

Note: the `asyncio.coroutine(...)` wrapper for `list_sessions_impl` is needed because it's a sync function; the `_run` helper awaits its caller. Replace it with the simpler form:

```python
    async def _run_sync(label: str, fn):
        try:
            value = fn()
        except Exception as e:
            failures.append((label, repr(e)))
            print(f"FAIL  {label:<24} {e!r}")
            return
        passes += 1
        preview = repr(value)
        if len(preview) > 80:
            preview = preview[:77] + "..."
        print(f"PASS  {label:<24} {preview}")

    _run_sync("list_sessions", lambda: read.list_sessions_impl(client))
```

Use `_run` for async impls and `_run_sync` for the one sync impl (`list_sessions_impl`).

- [ ] **Step 2: Verify it runs (optional but recommended)**

If iTerm2 is running and you're invoking from inside an iTerm2 session:

```bash
uv run python scripts/smoke.py
```

Expected: `13/13 passed.` and you'll see the session's badge change to "smoke", title to "smoke test", tab color shift, and a macOS notification appear. Restore manually as desired.

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke.py
git commit -m "feat: manual smoke script exercising every tool"
```

---

## Task 22: Integration tests

**Files:**

- Create: `tests/integration/conftest.py`, `tests/integration/test_integration.py`

Opt-in via `pytest -m integration`. CI does not run these; developers run them locally before tagging a release. Each test cleans up after itself.

- [ ] **Step 1: Create `tests/integration/conftest.py`**

```python
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
    await c._connect_once()
    return c
```

- [ ] **Step 2: Create `tests/integration/test_integration.py`**

```python
"""Integration tests against a live iTerm2.

Run with:

    uv run pytest -m integration -v

Requires iTerm2 running and the test process running inside an iTerm2 session.
"""

import asyncio

import pytest

from mcp_server_iterm2.tools import read, write

pytestmark = pytest.mark.integration


async def test_list_sessions_returns_real_hierarchy(client):
    result = read.list_sessions_impl(client)
    assert "windows" in result
    assert len(result["windows"]) >= 1


async def test_get_session_info(client, iterm_session_id):
    info = await read.get_session_info_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert info["session_id"] == iterm_session_id
    assert isinstance(info["dimensions"]["cols"], int)
    assert isinstance(info["dimensions"]["rows"], int)


async def test_set_and_read_badge(client, iterm_session_id):
    await write.set_badge_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, text="INTEGRATION"
    )
    info = await read.get_session_info_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert info["badge"] == "INTEGRATION"
    # cleanup
    await write.set_badge_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, text=""
    )


async def test_set_and_read_title(client, iterm_session_id):
    await write.set_title_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, title="integration-title"
    )
    info = await read.get_session_info_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert info["name"] == "integration-title"


async def test_set_tab_color_roundtrip(client, iterm_session_id):
    result = await write.set_tab_color_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, r=12, g=34, b=56
    )
    assert result["ok"] is True


async def test_set_user_variable_roundtrip(client, iterm_session_id):
    await write.set_user_variable_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None,
        name="user.itest", value="hello"
    )
    got = await read.get_variable_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, name="user.itest"
    )
    assert got["value"] == "hello"


async def test_get_screen_contents(client, iterm_session_id):
    result = await read.get_screen_contents_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert "text" in result
    assert "cursor" in result


async def test_get_scrollback(client, iterm_session_id):
    result = await read.get_scrollback_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, n_lines=50
    )
    assert "text" in result


async def test_get_recent_output_advances_cursor(client, iterm_session_id):
    first = await read.get_recent_output_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None, cursor=None
    )
    second = await read.get_recent_output_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None,
        cursor=first["cursor"],
    )
    # Same cursor or advanced; should not error and should be empty unless new output appeared.
    assert "text" in second


async def test_get_selection_returns_string(client, iterm_session_id):
    result = await read.get_selection_impl(
        client, session_id_arg=iterm_session_id, env_session_id=None
    )
    assert isinstance(result["text"], str)


async def test_list_profiles(client):
    result = await read.list_profiles_impl(client)
    assert "profiles" in result
    assert isinstance(result["profiles"], list)


async def test_post_notification(client):
    result = await write.post_notification_impl(
        title="integration", body="test"
    )
    assert result == {"ok": True}
```

- [ ] **Step 3: Verify integration tests run (only if iTerm2 is available)**

```bash
uv run pytest -m integration -v
```

Expected: 12 tests pass (or skip cleanly if `ITERM_SESSION_ID` unset).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: integration tests for all tools against live iTerm2"
```

---

## Task 23: Pre-commit config

**Files:**

- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: ty
        name: ty type check
        entry: uv run ty check src
        language: system
        types: [python]
        pass_filenames: false

      - id: pytest-unit
        name: pytest unit tests
        entry: uv run pytest tests/unit
        language: system
        types: [python]
        pass_filenames: false
```

- [ ] **Step 2: Install and verify**

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Expected: all hooks pass. If ty surfaces issues with FastMCP decorators, narrow them in `[tool.ty]` in `pyproject.toml` rather than disabling the hook.

- [ ] **Step 3: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: pre-commit hooks (ruff, ty, pytest unit)"
```

---

## Task 24: CI workflow

**Files:**

- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    name: Lint, typecheck, test (Python ${{ matrix.python }})
    runs-on: macos-latest
    strategy:
      fail-fast: false
      matrix:
        python: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Set up Python
        run: uv python install ${{ matrix.python }}

      - name: Sync deps
        run: uv sync --all-groups

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Ruff lint
        run: uv run ruff check .

      - name: Type check (ty)
        run: uv run ty check src

      - name: Unit tests
        run: uv run pytest tests/unit -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint + typecheck + unit tests on 3.12 and 3.13"
```

---

## Task 25: Publish workflow

**Files:**

- Create: `.github/workflows/publish.yml`

Trusted publishing via PyPI's OIDC — no API tokens stored in secrets. Requires configuring the `mcp-server-iterm2` project on PyPI to trust this repo's publish workflow (one-time manual step documented in CHANGELOG / release notes for future reference).

- [ ] **Step 1: Create `.github/workflows/publish.yml`**

```yaml
name: Publish to PyPI

on:
  push:
    tags: ["v*"]

permissions:
  contents: read
  id-token: write # Required for OIDC trusted publishing

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    environment: release
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Set up Python
        run: uv python install 3.12

      - name: Build
        run: uv build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: tag-triggered PyPI publish via OIDC trusted publishing"
```

- [ ] **Step 3: Final verification — full test suite green**

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check src
uv run pytest tests/unit -v
```

All four should pass. Integration tests run separately with `uv run pytest -m integration` and require iTerm2.

---

## Definition of Done

- [ ] All 25 tasks committed.
- [ ] `uv run pytest tests/unit` passes with zero failures.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.
- [ ] `uv run ty check src` passes (or has narrowly-scoped, documented ignores).
- [ ] `uv run pytest -m integration` passes against a real iTerm2.
- [ ] `uv run python scripts/smoke.py` reports `13/13 passed` from inside iTerm2.
- [ ] README documents install, first-run prompt, badge-format and title-rendering caveats.
- [ ] CI green on push to main on both 3.12 and 3.13.
- [ ] CHANGELOG entry for 0.1.0 lists every tool.

When all of the above are checked, tag `v0.1.0` and let the publish workflow ship it to PyPI.
