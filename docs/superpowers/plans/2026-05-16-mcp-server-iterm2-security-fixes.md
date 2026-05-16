# mcp-server-iterm2 Security Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the 9 actionable findings (S-1 through S-9) from the 0.1.0 paranoia audit: 3 block-shipping (event-loop blocking, PATH hijacking, missing subprocess timeouts) + 6 should-fix (length bounds, broaden exception handling, ruff S rules, SHA-pin actions, ci.yml permissions, adversarial escape tests).

**Architecture:** Surgical changes to `cookie.py`, `connection.py`, `tools/write.py`, `output_cursor.py`, `errors.py`, `server.py`, `pyproject.toml`, and both GitHub Actions workflows. No new modules. Tests-first throughout. Each task independent and committed separately.

**Tech Stack:** Same as 0.1.0 — Python 3.12+, `iterm2` SDK ≥ 2.7, `mcp` SDK ≥ 1.12, `pytest`, `ruff`, `ty`.

**Reference audit:** See conversation; S-1..S-9 mapped to specific lines in `cookie.py:8`, `cookie.py:22-27`, `connection.py:81`, `tools/write.py:86-101`, `server.py:33-194`, `pyproject.toml:50`, `.github/workflows/{ci,publish}.yml`.

---

## File Structure

| File                                       | Responsibility (this plan)                                                                  |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `src/mcp_server_iterm2/cookie.py`          | Absolute path to osascript, timeout, asyncio-safe wrapper (Tasks 1, 2, 3)                   |
| `src/mcp_server_iterm2/errors.py`          | Add `SubprocessTimeout` class (Task 2)                                                      |
| `src/mcp_server_iterm2/connection.py`      | `await asyncio.to_thread(request_cookie)` (Task 3)                                          |
| `src/mcp_server_iterm2/tools/write.py`     | Absolute path, timeout, async subprocess, length bounds, top-level `_escape` (Tasks 1, 2, 3, 4, 6) |
| `src/mcp_server_iterm2/tools/read.py`      | Length bound on cursor + variable name (Task 4)                                             |
| `src/mcp_server_iterm2/output_cursor.py`   | Length-bounded `decode_cursor` (Task 4)                                                     |
| `src/mcp_server_iterm2/server.py`          | Broaden each tool wrapper to catch all Exception, generic internal-error message (Task 5)   |
| `pyproject.toml`                           | Enable ruff `S` (Bandit) rules with narrow exemptions (Task 7)                              |
| `.github/workflows/ci.yml`                 | SHA-pin actions, add `permissions: contents: read` (Tasks 8, 9)                             |
| `.github/workflows/publish.yml`            | SHA-pin actions (Task 8)                                                                    |
| `tests/unit/test_cookie.py`                | Cover timeout error path, absolute-path argv (Tasks 1, 2)                                   |
| `tests/unit/test_tools_write.py`           | Cover timeout, length bounds, adversarial escape payloads (Tasks 2, 4, 6)                   |
| `tests/unit/test_errors.py`                | Cover new error class (Task 2)                                                              |
| `tests/unit/test_server.py`                | Cover broadened exception envelope (Task 5)                                                 |
| `tests/unit/test_output_cursor.py`         | Cover cursor length bound (Task 4)                                                          |

---

## Task 1: Use absolute `/usr/bin/osascript` (S-2)

**Bug:** `cookie.py:8` and `tools/write.py:97` invoke `subprocess.run(["osascript", "-e", ...])`. The bare name resolves via `$PATH` — a malicious binary earlier in PATH intercepts the call. iTerm2's own SDK uses `/usr/bin/osascript` (`iterm2/auth.py:45`).

**Files:**

- Modify: `src/mcp_server_iterm2/cookie.py`
- Modify: `src/mcp_server_iterm2/tools/write.py`
- Modify: `tests/unit/test_cookie.py`
- Modify: `tests/unit/test_tools_write.py`

- [ ] **Step 1: Write the failing test in `test_cookie.py`**

Add to `tests/unit/test_cookie.py`:

```python
@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_uses_absolute_osascript_path(mock_run):
    mock_run.return_value = _fake_completed(stdout="abc123\n")
    request_cookie()
    args = mock_run.call_args[0][0]
    assert args[0] == "/usr/bin/osascript", "must use absolute path, not PATH lookup"
```

- [ ] **Step 2: Write the failing test in `test_tools_write.py`**

Add to `tests/unit/test_tools_write.py`:

```python
@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_uses_absolute_osascript_path(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["/usr/bin/osascript"], returncode=0, stdout="", stderr=""
    )
    await post_notification_impl(title="t", body="b")
    args = mock_run.call_args[0][0]
    assert args[0] == "/usr/bin/osascript"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_cookie.py::test_uses_absolute_osascript_path tests/unit/test_tools_write.py::test_post_notification_uses_absolute_osascript_path -v`
Expected: FAIL — both currently use bare `"osascript"`.

- [ ] **Step 4: Update `cookie.py`**

In `src/mcp_server_iterm2/cookie.py`:

```python
_OSASCRIPT_COMMAND = [
    "/usr/bin/osascript",
    "-e",
    'tell application "iTerm2" to request cookie',
]
```

- [ ] **Step 5: Update `tools/write.py`**

In `src/mcp_server_iterm2/tools/write.py`, replace the subprocess args:

```python
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit -v`
Expected: all green (existing + 2 new).

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server_iterm2/cookie.py src/mcp_server_iterm2/tools/write.py tests/unit/test_cookie.py tests/unit/test_tools_write.py
git commit -m "fix(security): use absolute /usr/bin/osascript path to prevent PATH hijacking"
```

---

## Task 2: Add subprocess timeouts (S-3)

**Bug:** `cookie.py:22-27` and `tools/write.py:96-101` call `subprocess.run` without `timeout=`. If `osascript` hangs (user permission dialog with no operator present, broken TCC daemon), the call never returns. Combined with the async-blocking bug (Task 3), this freezes the entire server.

**Files:**

- Modify: `src/mcp_server_iterm2/errors.py`
- Modify: `src/mcp_server_iterm2/cookie.py`
- Modify: `src/mcp_server_iterm2/tools/write.py`
- Modify: `tests/unit/test_errors.py`
- Modify: `tests/unit/test_cookie.py`
- Modify: `tests/unit/test_tools_write.py`

- [ ] **Step 1: Add `SubprocessTimeout` error class**

In `src/mcp_server_iterm2/errors.py`, after `Disconnected`:

```python
class SubprocessTimeout(MCPIterm2Error):
    """A child osascript invocation exceeded its time budget."""

    def __init__(self, what: str, seconds: float) -> None:
        super().__init__(what)
        self.what = what
        self.seconds = seconds
```

And add to `to_error_text`:

```python
        case SubprocessTimeout() as e:
            return f"osascript timed out after {e.seconds:.0f}s while {e.what}."
```

- [ ] **Step 2: Add the error-rendering test**

In `tests/unit/test_errors.py`:

```python
def test_subprocess_timeout_message():
    err = SubprocessTimeout(what="requesting iTerm2 cookie", seconds=30.0)
    assert to_error_text(err) == (
        "osascript timed out after 30s while requesting iTerm2 cookie."
    )
```

Don't forget to import `SubprocessTimeout` at the top of `test_errors.py`.

- [ ] **Step 3: Write the failing tests for the cookie path**

In `tests/unit/test_cookie.py`:

```python
@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_request_cookie_raises_subprocess_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="osascript", timeout=30.0)
    with pytest.raises(SubprocessTimeout) as exc:
        request_cookie()
    assert exc.value.seconds == 30.0


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_request_cookie_passes_timeout(mock_run):
    mock_run.return_value = _fake_completed(stdout="abc\n")
    request_cookie()
    assert mock_run.call_args.kwargs.get("timeout") == 30.0
```

Import `SubprocessTimeout` at the top.

- [ ] **Step 4: Write the failing tests for the notification path**

In `tests/unit/test_tools_write.py`:

```python
@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_raises_subprocess_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="osascript", timeout=5.0)
    with pytest.raises(SubprocessTimeout) as exc:
        await post_notification_impl(title="t", body="b")
    assert exc.value.seconds == 5.0


@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_passes_timeout(mock_run):
    mock_run.return_value = subprocess.CompletedProcess(
        args=["/usr/bin/osascript"], returncode=0, stdout="", stderr=""
    )
    await post_notification_impl(title="t", body="b")
    assert mock_run.call_args.kwargs.get("timeout") == 5.0
```

Import `SubprocessTimeout` at the top.

- [ ] **Step 5: Run the new tests to verify they fail**

Run: `uv run pytest tests/unit -k "timeout" -v`
Expected: FAIL — no timeout currently passed, TimeoutExpired uncaught.

- [ ] **Step 6: Add timeout to `cookie.py`**

```python
"""Request an iTerm2 API cookie via AppleScript."""

import subprocess

from mcp_server_iterm2.errors import APINotEnabled, AuthDenied, ITermNotRunning, SubprocessTimeout

_OSASCRIPT_COMMAND = [
    "/usr/bin/osascript",
    "-e",
    'tell application "iTerm2" to request cookie',
]
_COOKIE_TIMEOUT_S = 30.0


def request_cookie() -> str:
    """Run osascript to request a one-time cookie.

    Returns the cookie string. Raises:
      - ITermNotRunning if iTerm2 isn't running.
      - APINotEnabled if the Python API toggle is off in iTerm2 prefs.
      - AuthDenied if the user denied this script.
      - SubprocessTimeout if osascript doesn't return within _COOKIE_TIMEOUT_S.
    """
    try:
        result = subprocess.run(
            _OSASCRIPT_COMMAND,
            capture_output=True,
            text=True,
            check=False,
            timeout=_COOKIE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessTimeout(
            what="requesting iTerm2 cookie", seconds=_COOKIE_TIMEOUT_S
        ) from exc

    if result.returncode == 0:
        return result.stdout.strip()

    stderr_lower = result.stderr.lower()
    if "isn’t running" in result.stderr or "application isn't running" in stderr_lower:
        raise ITermNotRunning()
    if "python api is not enabled" in stderr_lower:
        raise APINotEnabled()
    raise AuthDenied()
```

- [ ] **Step 7: Add timeout to `tools/write.py`**

In `post_notification_impl`:

```python
_NOTIFICATION_TIMEOUT_S = 5.0


async def post_notification_impl(*, title: str, body: str) -> dict[str, Any]:
    """Post a macOS notification via osascript."""

    # ... (keep _escape definition as-is for now; Task 6 hoists it)
    script = f'display notification "{_escape(body)}" with title "{_escape(title)}"'
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=_NOTIFICATION_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessTimeout(
            what="posting notification", seconds=_NOTIFICATION_TIMEOUT_S
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip() or 'unknown error'}")
    return {"ok": True}
```

Add `from mcp_server_iterm2.errors import SubprocessTimeout` at the top of `tools/write.py`.

- [ ] **Step 8: Run tests to verify everything passes**

Run: `uv run pytest tests/unit -v`
Expected: all green (existing + 5 new).

- [ ] **Step 9: Commit**

```bash
git add src/mcp_server_iterm2/errors.py src/mcp_server_iterm2/cookie.py src/mcp_server_iterm2/tools/write.py tests/unit/test_errors.py tests/unit/test_cookie.py tests/unit/test_tools_write.py
git commit -m "fix(security): add timeouts to osascript subprocess calls; new SubprocessTimeout error"
```

---

## Task 3: Run subprocess calls off the event loop (S-1)

**Bug:** `connection.py:81` (`connect_once` is async) calls sync `request_cookie()`. `tools/write.py` (`post_notification_impl` is async) calls sync `subprocess.run`. Either call blocks the entire asyncio loop — while blocked, no MCP tool can be served. Combined with the now-existing 30s/5s timeouts (Task 2), the worst-case stall is bounded but still unacceptable.

**Files:**

- Modify: `src/mcp_server_iterm2/connection.py`
- Modify: `src/mcp_server_iterm2/tools/write.py`
- Modify: `tests/unit/test_connection.py`
- Modify: `tests/unit/test_tools_write.py`

- [ ] **Step 1: Write the failing test that proves the cookie call doesn't block**

In `tests/unit/test_connection.py`:

```python
@pytest.mark.asyncio
@patch("mcp_server_iterm2.connection.iterm2")
async def test_connect_once_does_not_block_event_loop(mock_iterm2, monkeypatch):
    """request_cookie is a synchronous subprocess call; it must run off the loop."""
    import threading

    called_off_main = {"flag": False}

    def blocking_request_cookie():
        called_off_main["flag"] = threading.current_thread() is not threading.main_thread()
        return "cookie-xyz"

    monkeypatch.setattr(
        "mcp_server_iterm2.connection.request_cookie", blocking_request_cookie
    )
    mock_iterm2.Connection.async_create = AsyncMock(return_value=MagicMock())
    mock_iterm2.async_get_app = AsyncMock(return_value=MagicMock())

    client = ITermClient()
    await client.connect_once()

    assert called_off_main["flag"], "request_cookie must run in a thread, not on the loop"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_connection.py::test_connect_once_does_not_block_event_loop -v`
Expected: FAIL — `request_cookie` runs on the main (event loop) thread.

- [ ] **Step 3: Wrap `request_cookie` in `asyncio.to_thread` in `connection.py`**

In `connection.py`, modify `connect_once`:

```python
    async def connect_once(self) -> None:
        """Establish a single connection attempt. Raises on failure."""
        cookie = await asyncio.to_thread(request_cookie)
        os.environ["ITERM2_COOKIE"] = cookie
        self._connection = await iterm2.Connection.async_create()
        self._app = await iterm2.async_get_app(self._connection)
        log.info("connected to iTerm2")
```

(`asyncio` is already imported.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_connection.py -v`
Expected: all green (including the new off-thread test).

- [ ] **Step 5: Write the failing test for the notification path**

In `tests/unit/test_tools_write.py`:

```python
@patch("mcp_server_iterm2.tools.write.subprocess.run")
async def test_post_notification_runs_subprocess_off_event_loop(mock_run):
    import threading
    called_threads = []

    def _capture_thread(*args, **kwargs):
        called_threads.append(threading.current_thread())
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="", stderr=""
        )

    mock_run.side_effect = _capture_thread

    await post_notification_impl(title="t", body="b")
    assert len(called_threads) == 1
    assert called_threads[0] is not threading.main_thread(), (
        "subprocess.run must run off the event loop thread"
    )
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_tools_write.py::test_post_notification_runs_subprocess_off_event_loop -v`
Expected: FAIL.

- [ ] **Step 7: Wrap `subprocess.run` in `asyncio.to_thread` in `tools/write.py`**

In `post_notification_impl`:

```python
async def post_notification_impl(*, title: str, body: str) -> dict[str, Any]:
    """Post a macOS notification via osascript."""

    # ... (keep _escape definition as-is for now; Task 6 hoists it)
    script = f'display notification "{_escape(body)}" with title "{_escape(title)}"'
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=_NOTIFICATION_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessTimeout(
            what="posting notification", seconds=_NOTIFICATION_TIMEOUT_S
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip() or 'unknown error'}")
    return {"ok": True}
```

Add `import asyncio` at the top of `tools/write.py`.

- [ ] **Step 8: Run tests to verify they all pass**

Run: `uv run pytest tests/unit -v`
Expected: all green.

- [ ] **Step 9: Commit**

```bash
git add src/mcp_server_iterm2/connection.py src/mcp_server_iterm2/tools/write.py tests/unit/test_connection.py tests/unit/test_tools_write.py
git commit -m "fix(security): run osascript via asyncio.to_thread to avoid blocking the event loop"
```

---

## Task 4: Length bounds on user-supplied strings (S-4)

**Bug:** No bounds on `text` (set_badge), `title` (set_title, post_notification), `body` (post_notification), `name` / `value` (set_user_variable, get_variable), or `cursor` (get_recent_output). A 1 GB base64 cursor is decoded fully in memory before any validation; an argv near `ARG_MAX` (~256 KB on macOS) crashes with `OSError`.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`
- Modify: `src/mcp_server_iterm2/tools/read.py`
- Modify: `src/mcp_server_iterm2/output_cursor.py`
- Modify: `tests/unit/test_tools_write.py`
- Modify: `tests/unit/test_tools_read.py`
- Modify: `tests/unit/test_output_cursor.py`

- [ ] **Step 1: Write the failing tests for write tools**

In `tests/unit/test_tools_write.py`:

```python
async def test_set_badge_rejects_text_over_limit(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await set_badge_impl(
            client, session_id_arg="sess-1", env_session_id=None, text="x" * 257
        )


async def test_set_title_rejects_title_over_limit(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await set_title_impl(
            client, session_id_arg="sess-1", env_session_id=None, title="x" * 257
        )


async def test_set_user_variable_rejects_value_over_limit(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await set_user_variable_impl(
            client,
            session_id_arg="sess-1",
            env_session_id=None,
            name="user.big",
            value="x" * 4097,
        )


async def test_set_user_variable_rejects_name_over_limit(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await set_user_variable_impl(
            client,
            session_id_arg="sess-1",
            env_session_id=None,
            name="user." + ("x" * 252),
            value="ok",
        )


async def test_post_notification_rejects_long_title():
    with pytest.raises(ValueError):
        await post_notification_impl(title="x" * 129, body="ok")


async def test_post_notification_rejects_long_body():
    with pytest.raises(ValueError):
        await post_notification_impl(title="ok", body="x" * 1025)
```

- [ ] **Step 2: Write the failing test for `get_variable` name bound**

In `tests/unit/test_tools_read.py`:

```python
async def test_get_variable_rejects_long_name(simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    with pytest.raises(ValueError):
        await get_variable_impl(
            client,
            session_id_arg="sess-1",
            env_session_id=None,
            name="session." + ("x" * 250),
        )
```

- [ ] **Step 3: Write the failing test for cursor length bound**

In `tests/unit/test_output_cursor.py`:

```python
def test_decode_cursor_rejects_oversize_input():
    big = "A" * 16385  # 16 KB + 1
    with pytest.raises(CursorInvalid):
        decode_cursor(big)
```

- [ ] **Step 4: Run failing tests to confirm they fail**

Run: `uv run pytest tests/unit -k "over_limit or long_name or long_title or long_body or oversize" -v`
Expected: all FAIL.

- [ ] **Step 5: Add bounds constants and validation in `tools/write.py`**

At the top of `src/mcp_server_iterm2/tools/write.py`, after imports:

```python
_MAX_BADGE = 256
_MAX_TITLE = 256
_MAX_VAR_NAME = 256
_MAX_VAR_VALUE = 4096
_MAX_NOTIFICATION_TITLE = 128
_MAX_NOTIFICATION_BODY = 1024


def _check_length(field: str, value: str, limit: int) -> None:
    if len(value) > limit:
        raise ValueError(f"{field} length {len(value)} exceeds limit {limit}")
```

Then in each impl, validate before any session resolution or subprocess call:

```python
async def set_badge_impl(client, *, session_id_arg, env_session_id, text):
    _check_length("badge text", text, _MAX_BADGE)
    app = client.require_app()
    ...


async def set_title_impl(client, *, session_id_arg, env_session_id, title):
    _check_length("title", title, _MAX_TITLE)
    app = client.require_app()
    ...


async def set_user_variable_impl(client, *, session_id_arg, env_session_id, name, value):
    if not name.startswith("user."):
        raise ValueError(f"variable name must start with 'user.' (got {name!r})")
    _check_length("variable name", name, _MAX_VAR_NAME)
    _check_length("variable value", value, _MAX_VAR_VALUE)
    app = client.require_app()
    ...


async def post_notification_impl(*, title, body):
    _check_length("notification title", title, _MAX_NOTIFICATION_TITLE)
    _check_length("notification body", body, _MAX_NOTIFICATION_BODY)
    ...
```

- [ ] **Step 6: Add bound for `get_variable` in `tools/read.py`**

At the top of `src/mcp_server_iterm2/tools/read.py`:

```python
_MAX_VAR_NAME = 256
```

In `get_variable_impl`:

```python
async def get_variable_impl(client, *, session_id_arg, env_session_id, name):
    if len(name) > _MAX_VAR_NAME:
        raise ValueError(f"variable name length {len(name)} exceeds limit {_MAX_VAR_NAME}")
    app = client.require_app()
    ...
```

- [ ] **Step 7: Add length bound in `decode_cursor`**

In `src/mcp_server_iterm2/output_cursor.py`:

```python
_MAX_CURSOR_LEN = 16384


def decode_cursor(cursor: str, *, expected_session_id: str | None = None) -> tuple[str, int]:
    if len(cursor) > _MAX_CURSOR_LEN:
        raise CursorInvalid(f"cursor length {len(cursor)} exceeds limit {_MAX_CURSOR_LEN}")
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        sid = data["sid"]
        line = int(data["line"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CursorInvalid(str(exc)) from exc
    if not isinstance(sid, str):
        raise CursorInvalid("cursor sid is not a string")
    if expected_session_id is not None and sid != expected_session_id:
        raise CursorInvalid("cursor session_id mismatch")
    return sid, line
```

Note: the `isinstance(sid, str)` check keeps `decode_cursor` self-defending even when callers omit `expected_session_id`.

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/unit -v`
Expected: all green (existing + 8 new).

- [ ] **Step 9: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py src/mcp_server_iterm2/tools/read.py src/mcp_server_iterm2/output_cursor.py tests/unit/test_tools_write.py tests/unit/test_tools_read.py tests/unit/test_output_cursor.py
git commit -m "fix(security): bound length of user-supplied strings (badge, title, var, cursor)"
```

---

## Task 5: Broaden tool exception handling (S-5)

**Bug:** Each tool wrapper in `server.py:33-194` does `except MCPIterm2Error as e: raise RuntimeError(to_error_text(e))`. Every other exception — `iterm2.rpc.RPCException`, `websockets` errors, `ValueError`, `OSError`, the new `SubprocessTimeout` — propagates raw. FastMCP wraps it as `"Error executing tool X: <str(e)>"` exposing inner-library messages to agents.

**Files:**

- Modify: `src/mcp_server_iterm2/server.py`
- Modify: `tests/unit/test_server.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_server.py`:

```python
def test_create_server_wraps_unknown_exceptions_as_generic_internal_error():
    """Unknown exceptions must not leak third-party error messages to the agent."""
    client = MagicMock()
    client.require_app.side_effect = RuntimeError("internal: connection pool exhausted at 0xdeadbeef")
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_server.py::test_create_server_wraps_unknown_exceptions_as_generic_internal_error -v`
Expected: FAIL — current code only catches `MCPIterm2Error`, so the raw `RuntimeError` propagates.

- [ ] **Step 3: Add a generic-internal-error helper to `server.py`**

At the top of `src/mcp_server_iterm2/server.py`, after the existing imports:

```python
import logging

log = logging.getLogger(__name__)


def _to_tool_error(exc: BaseException) -> RuntimeError:
    """Convert any tool-impl exception into a safe RuntimeError for FastMCP.

    Known errors (MCPIterm2Error) are surfaced verbatim via to_error_text.
    Everything else collapses to a generic "Internal error: <ExceptionClass>"
    so we never leak third-party library messages, stack frames, or addresses.
    """
    if isinstance(exc, MCPIterm2Error):
        return RuntimeError(to_error_text(exc))
    log.exception("unexpected error in tool", exc_info=exc)
    return RuntimeError(f"Internal error: {type(exc).__name__}")
```

- [ ] **Step 4: Replace every `except MCPIterm2Error` block in `server.py`**

Replace the 13 tool wrappers' exception handlers. Pattern:

```python
        except MCPIterm2Error as e:
            raise RuntimeError(to_error_text(e)) from e
```

becomes:

```python
        except Exception as e:  # noqa: BLE001 — intentional broad catch at tool boundary
            raise _to_tool_error(e) from e
```

Apply to all 13 tool functions in `create_server`. Don't forget the `list_sessions` (sync) wrapper as well — same pattern applies.

- [ ] **Step 5: Run tests to verify everything passes**

Run: `uv run pytest tests/unit -v`
Expected: all green. Specifically, `test_create_server_translates_mcpiterm2error_to_runtime_error` still passes (MCPIterm2Error is still surfaced via to_error_text), and the new generic test passes.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server_iterm2/server.py tests/unit/test_server.py
git commit -m "fix(security): collapse unknown tool exceptions to generic 'Internal error: <Type>'"
```

---

## Task 6: Adversarial AppleScript escape tests + hoist `_escape` (S-9)

**Bug:** `_escape` is correct by reasoning but tested only via two example payloads. A future refactor could silently regress. Also `_escape` is a nested function inside `post_notification_impl`, awkward to test directly.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`
- Modify: `tests/unit/test_tools_write.py`

- [ ] **Step 1: Hoist `_escape` to module level**

In `src/mcp_server_iterm2/tools/write.py`, move the `_escape` function out of `post_notification_impl` so it's importable:

```python
def _escape_applescript_string(s: str) -> str:
    """Escape a Python string for safe embedding inside an AppleScript "..." literal.

    Order matters: backslash MUST be doubled FIRST so subsequent escapes don't
    get re-escaped. Then escape the closing-quote character and the three
    AppleScript-recognised C-style control escapes.
    """
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
```

In `post_notification_impl`, replace the nested `_escape` call:

```python
    script = (
        f'display notification "{_escape_applescript_string(body)}" '
        f'with title "{_escape_applescript_string(title)}"'
    )
```

- [ ] **Step 2: Add adversarial parametrized tests**

In `tests/unit/test_tools_write.py`, add (with appropriate imports):

```python
from mcp_server_iterm2.tools.write import _escape_applescript_string


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Plain text — unchanged.
        ("hello", "hello"),
        # Double quote — escaped.
        ('say "hi"', r'say \"hi\"'),
        # Backslash — doubled.
        ("a\\b", r"a\\b"),
        # Backslash THEN quote — must escape both, in order.
        ('\\"', r'\\\"'),
        # Newline — converted to AppleScript escape sequence.
        ("line1\nline2", r"line1\nline2"),
        # Carriage return + tab.
        ("a\rb\tc", r"a\rb\tc"),
        # AppleScript-injection attempt: closes string, injects code, opens comment.
        ('"; do shell script "rm -rf ~"; --', r'\"; do shell script \"rm -rf ~\"; --'),
        # Mixed backslash-quote sequences.
        ('\\\\"\\\\', r'\\\\\"\\\\'),
        # Empty string.
        ("", ""),
    ],
    ids=[
        "plain",
        "double-quote",
        "backslash",
        "backslash-quote",
        "newline",
        "cr-tab",
        "injection-attempt",
        "mixed-backslash-quote",
        "empty",
    ],
)
def test_applescript_escape_handles_adversarial_payloads(raw, expected):
    assert _escape_applescript_string(raw) == expected


def test_applescript_escape_does_not_leave_unescaped_double_quote():
    """No matter what input we throw at it, no naked " survives the escape."""
    for ch in ('"', '""', '\\"', '"\\', '\n"', '\t"\n'):
        escaped = _escape_applescript_string(ch)
        # Every " in `escaped` must have a \ immediately before it.
        for i, c in enumerate(escaped):
            if c == '"':
                assert i > 0 and escaped[i - 1] == "\\", (
                    f"unescaped quote at index {i} in {escaped!r} (from raw {ch!r})"
                )


def test_applescript_escape_preserves_length_relationship_for_safe_chars():
    """ASCII printable chars (except \\, ") pass through unchanged."""
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !#$%&'()*+,-./"
    assert _escape_applescript_string(safe) == safe


def test_applescript_escape_handles_unicode_bidi_and_smart_quotes():
    """Unicode chars that *look* like quotes/backslashes but aren't (U+201C, U+2014, etc.)
    must pass through unchanged — they cannot close the AppleScript string."""
    raw = "Hello “world” ‮secret‬ ¬¬"
    escaped = _escape_applescript_string(raw)
    assert escaped == raw, "smart/bidi/special unicode must not be modified"
```

- [ ] **Step 3: Run new tests and verify they pass**

Run: `uv run pytest tests/unit/test_tools_write.py -k "applescript_escape" -v`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py tests/unit/test_tools_write.py
git commit -m "test(security): hoist _escape and add adversarial AppleScript payload tests"
```

---

## Task 7: Enable ruff `S` (Bandit) rules (S-6)

**Bug:** `pyproject.toml:50` selects `["E","F","W","I","N","UP","B","SIM","RUF"]` — Bandit rules disabled. Enabling them catches partial-path subprocess (S607), broad `try/except`, hardcoded passwords, and other security smells mechanically. Free defense in depth.

**Files:**

- Modify: `pyproject.toml`

- [ ] **Step 1: Add `S` to the lint select**

In `pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "RUF", "S"]
# N818: error-class naming is intentional (see design spec).
# RUF001: cookie.py literally matches iTerm2's right-single-quotation-mark error text.
# S101: pytest tests use `assert` by design.
# S603: subprocess calls use list argv with shell=False — false positive for our usage.
ignore = ["N818", "RUF001", "S101", "S603"]

[tool.ruff.lint.per-file-ignores]
# Tests construct fakes with strings that look like credentials; not a security concern.
"tests/**/*.py" = ["S106", "S105"]
```

`S101` (use of `assert`) is ignored globally because pytest uses `assert`. `S603` (subprocess-without-shell-equals-true) is a false positive when shell=False (default); we ignore it globally. Adjust other `S###` rules as needed based on actual output.

- [ ] **Step 2: Run ruff to surface any new issues**

Run: `uv run ruff check . --no-fix`
Expected: a small number of warnings, all of which should be either (a) genuine issues already fixed in earlier tasks (S607 — bare osascript → now `/usr/bin/osascript`), or (b) noqa-able with documented reason.

- [ ] **Step 3: Address remaining warnings**

For each remaining `S###` warning, either fix the underlying issue or add a narrowly-scoped `# noqa: S### — <reason>` annotation. Do NOT add blanket `# noqa: S` comments.

Common cases you may encounter:
- `S104` (hardcoded bind): n/a, we don't bind ports.
- `S311` (random): n/a unless you've added crypto.
- `S404` (subprocess import): sibling of S603; add to `ignore` if it appears.

- [ ] **Step 4: Run the full test + lint + typecheck suite**

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check src
uv run pytest tests/unit
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
# Include any source files you needed to noqa
git commit -m "chore(security): enable ruff S (Bandit) rules with narrow exemptions"
```

---

## Task 8: SHA-pin GitHub Actions (S-7)

**Bug:** `ci.yml` and `publish.yml` reference actions by mutable tag/branch (`actions/checkout@v4`, `astral-sh/setup-uv@v3`, `pypa/gh-action-pypi-publish@release/v1`). Compromised upstream re-points the ref → malicious code runs in CI/publish context.

**Files:**

- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/publish.yml`

- [ ] **Step 1: Look up the current SHA for each action**

Run:

```bash
gh api repos/actions/checkout/commits/v4 --jq '.sha'
gh api repos/astral-sh/setup-uv/commits/v3 --jq '.sha'
gh api repos/pypa/gh-action-pypi-publish/commits/release/v1 --jq '.sha'
```

Record the three SHAs (each is 40 hex chars).

- [ ] **Step 2: Update `ci.yml`**

Replace each `uses:` line. Use the SHAs from Step 1; comment with the tag for human readability:

```yaml
      - uses: actions/checkout@<SHA-FROM-STEP-1>  # v4
      - name: Install uv
        uses: astral-sh/setup-uv@<SHA-FROM-STEP-1>  # v3
```

- [ ] **Step 3: Update `publish.yml`**

```yaml
      - uses: actions/checkout@<SHA-FROM-STEP-1>  # v4
      - name: Install uv
        uses: astral-sh/setup-uv@<SHA-FROM-STEP-1>  # v3
      ...
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@<SHA-FROM-STEP-1>  # release/v1
```

- [ ] **Step 4: Verify the workflows still parse**

```bash
gh workflow list
```

Expected: both workflows listed without errors. (Actual CI run happens on next push; this is a static-check stage.)

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/publish.yml
git commit -m "chore(security): pin GitHub Actions to immutable commit SHAs"
```

---

## Task 9: Explicit minimal permissions in `ci.yml` (S-8)

**Bug:** `ci.yml` lacks a `permissions:` block. The workflow inherits the repo-default `GITHUB_TOKEN` scope, which on older repos can be `contents: write`. CI must be read-only.

**Files:**

- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add `permissions: contents: read` at the workflow level**

In `.github/workflows/ci.yml`, immediately after the `on:` block and before `jobs:`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  test:
    name: Lint, typecheck, test (Python ${{ matrix.python }})
    runs-on: macos-latest
    ...
```

- [ ] **Step 2: Verify the workflow is well-formed**

```bash
gh workflow list
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore(security): set explicit minimal permissions in CI workflow"
```

---

## Definition of Done

- [ ] Tasks 1–9 all committed.
- [ ] `uv run pytest tests/unit` passes (≥ 95 tests, depending on parametrize expansion).
- [ ] `uv run ruff check .` passes with the new `S` rules enabled.
- [ ] `uv run ruff format --check .` passes.
- [ ] `uv run ty check src` passes.
- [ ] No `subprocess.run` call in the codebase lacks a `timeout=` argument or an absolute executable path.
- [ ] No `subprocess.run` call inside an `async def` runs synchronously (all wrapped in `asyncio.to_thread`).
- [ ] Every `@mcp.tool()` body in `server.py` uses the broad-catch + `_to_tool_error` pattern.
- [ ] All `uses:` in `.github/workflows/*.yml` reference a 40-char commit SHA.
- [ ] Both workflows declare `permissions:` explicitly.

When all checked, the audit's block-shipping and should-fix-this-version tiers are closed. The remaining document-and-defer items (S-10 through S-13) are tracked separately and not part of this plan.

---

## Out of scope (document-and-defer items from audit)

These are deliberately NOT addressed by this plan; they are documentation / threat-model / hardening-by-policy concerns that should be handled separately:

- **S-10**: README/spec should clarify the macOS Automation permission is binary-pair, not server-specific.
- **S-11**: README should add a "Security model" section listing deception capabilities (set_title, post_notification, screen reads).
- **S-12**: Token-bucket rate limit on `post_notification` (server-side spam protection).
- **S-13**: Pass minimal `env=` to subprocess children (defense-in-depth env-stripping).

Track these in a follow-up plan or as GitHub issues.
