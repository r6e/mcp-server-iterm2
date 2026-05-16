# mcp-server-iterm2 SDK-Grounded Fixes Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve seven correctness items identified by SDK-grounded audit of the 0.1.0 implementation: three real bugs and four quality gaps, all verifiable against `iterm2/*.py` SDK source and the iTerm2 GitHub repository.

**Architecture:** Surgical fixes to `tools/read.py`, `tools/write.py`, and `output_cursor.py`. No new modules; no architectural change. Each fix is independent and committed separately. Tests-first throughout.

**Tech Stack:** Same as 0.1.0 — Python 3.12+, `iterm2` SDK ≥ 2.7, `mcp` SDK ≥ 1.12, `pytest`, `ruff`, `ty`.

**Reference audit:** Findings traced to: `iterm2/session.py:246` (buried `__grid_size = None`), `iterm2/session.py:367-369` (Transaction requirement), `output_cursor.diff_since` last_seen<0 branch, `iterm2/app.py:448,462` (deprecated property names), `iterm2/tab.py:115` (`.sessions` excludes minimized), `iterm2/profile.py:1063` (`set_tab_color` no-op when light/dark split).

---

## File Structure

| File                                         | Responsibility (this plan)                                            |
| -------------------------------------------- | --------------------------------------------------------------------- |
| `src/mcp_server_iterm2/output_cursor.py`     | Modify: treat `last_seen < 0` as fresh, not expired (Task 3)          |
| `src/mcp_server_iterm2/tools/read.py`        | Modify: buried-safe info, transactions, deprecated APIs, all_sessions, buried list (Tasks 1, 2, 4, 5, 6) |
| `src/mcp_server_iterm2/tools/write.py`       | Modify: set light + dark tab colors too (Task 7)                      |
| `tests/unit/conftest.py`                     | Create: autouse stub for `iterm2.Transaction` so existing tests don't need to mock it |
| `tests/fixtures.py`                          | Modify: add `windows`/`current_window`, `all_sessions`, `buried_sessions` |
| `tests/unit/test_tools_read.py`              | Modify: cover buried info, transaction usage, all_sessions, buried list (Tasks 1, 2, 4, 5, 6) |
| `tests/unit/test_tools_write.py`             | Modify: cover light/dark tab color calls (Task 7)                     |
| `tests/unit/test_output_cursor.py`           | Modify: cover fresh-cursor case (Task 3)                              |
| `README.md`, `CHANGELOG.md`                  | Modify: document `list_sessions` schema change for buried sessions (Task 6) |

---

## Task 1: Buried-session-safe `get_session_info`

**Bug:** `iterm2/session.py:226-247` shows that buried sessions have `self.__grid_size = None`. Our `get_session_info_impl` reads `session.grid_size.width`/`.height` unconditionally → `AttributeError`. We must guard, since buried sessions are valid lookup targets via `app.get_session_by_id(..., include_buried=True)` (the SDK default).

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`
- Modify: `tests/fixtures.py`
- Modify: `tests/unit/test_tools_read.py`

- [ ] **Step 1: Extend fixture factory to support buried sessions**

In `tests/fixtures.py`, update `make_session` to accept `buried: bool` and to default `grid_size` appropriately:

```python
def make_session(
    *,
    session_id: str,
    name: str = "session",
    buried: bool = False,
) -> MagicMock:
    s = MagicMock(name=f"session-{session_id}")
    s.session_id = session_id
    s.name = name
    s.buried = buried
    if buried:
        s.grid_size = None
    return s
```

- [ ] **Step 2: Write the failing test**

In `tests/unit/test_tools_read.py`, add:

```python
async def test_get_session_info_buried_session_returns_null_dimensions(simple_app):
    """Buried sessions have grid_size=None; we must not crash on dimensions access."""
    client = MagicMock()
    client.require_app.return_value = simple_app
    # Replace the fixture session with a buried one.
    from tests.fixtures import make_session
    buried = make_session(session_id="sess-buried", name="zsh", buried=True)
    simple_app.get_session_by_id = lambda sid: buried if sid == "sess-buried" else None
    buried.async_get_variable = AsyncMock(
        side_effect=lambda key: {
            "session.path": "/Users/rob",
            "user.badge": "",
            "session.tty": "",
        }.get(key)
    )
    profile = MagicMock()
    profile.name = "Default"
    buried.async_get_profile = AsyncMock(return_value=profile)

    result = await get_session_info_impl(client, session_id_arg="sess-buried", env_session_id=None)
    assert result["dimensions"] is None
    assert result["session_id"] == "sess-buried"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_tools_read.py::test_get_session_info_buried_session_returns_null_dimensions -v`
Expected: FAIL — `AttributeError: 'NoneType' object has no attribute 'width'`.

- [ ] **Step 4: Update `get_session_info_impl` to guard `grid_size`**

In `src/mcp_server_iterm2/tools/read.py`, replace the body of `get_session_info_impl`:

```python
async def get_session_info_impl(
    client: Any, *, session_id_arg: str | None, env_session_id: str | None
) -> dict[str, Any]:
    """Return session metadata: title, working dir, profile, badge, dimensions, TTY.

    Buried sessions have no grid; `dimensions` is None in that case.
    """
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    grid = session.grid_size
    profile, working_directory, badge, tty = await asyncio.gather(
        session.async_get_profile(),
        session.async_get_variable("session.path"),
        session.async_get_variable("user.badge"),
        session.async_get_variable("session.tty"),
    )
    dimensions = {"cols": grid.width, "rows": grid.height} if grid is not None else None
    return {
        "session_id": session.session_id,
        "name": session.name,
        "working_directory": working_directory,
        "profile_name": profile.name,
        "badge": badge,
        "tty": tty,
        "dimensions": dimensions,
    }
```

- [ ] **Step 5: Run test to verify it passes (and existing tests still pass)**

Run: `uv run pytest tests/unit/test_tools_read.py -v`
Expected: all green, including the new buried-session test.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py tests/fixtures.py tests/unit/test_tools_read.py
git commit -m "fix: handle buried sessions (grid_size=None) in get_session_info"
```

---

## Task 2: Wrap `line_info` + `get_contents` in `iterm2.Transaction`

**Bug:** `iterm2/session.py:367-369` (`async_get_contents` docstring): "To use this reliably, you **must** call `async_get_line_info()` and this method in a `Transaction` to ensure the session doesn't change between calls." Our `get_scrollback_impl` and `get_recent_output_impl` make the two RPCs back-to-back without a transaction. Concrete consequence: if `overflow` advances between the two calls, the SDK silently returns a subset — agent sees fewer lines than were emitted, with `cursor_expired=False`.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`
- Create: `tests/unit/conftest.py` (autouse stub so existing tests stay clean)
- Modify: `tests/unit/test_tools_read.py` (add explicit transaction-usage test)

- [ ] **Step 1: Create `tests/unit/conftest.py` to stub Transaction for existing tests**

```python
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

    # Replace the class lookup so `async with iterm2.Transaction(conn):` works.
    monkeypatch.setattr(
        "mcp_server_iterm2.tools.read.iterm2.Transaction",
        MagicMock(side_effect=lambda conn: _noop(conn)),
    )
```

- [ ] **Step 2: Run the existing test suite to confirm the autouse stub is benign**

Run: `uv run pytest tests/unit -v`
Expected: all currently-passing tests still pass; no new failures from the autouse fixture.

- [ ] **Step 3: Write the failing test that asserts Transaction wrapping**

In `tests/unit/test_tools_read.py`, add:

```python
async def test_get_scrollback_wraps_line_info_and_contents_in_transaction(simple_app, monkeypatch):
    """The SDK requires line_info + get_contents to run inside a Transaction."""
    client = MagicMock()
    client.require_app.return_value = simple_app
    client.require_connection.return_value = "<conn>"
    session = simple_app.get_session_by_id("sess-1")

    enter_calls = []
    exit_calls = []

    class _TrackedTransaction:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            enter_calls.append(self.conn)
            return self

        async def __aexit__(self, *exc):
            exit_calls.append(self.conn)
            return False

    monkeypatch.setattr("mcp_server_iterm2.tools.read.iterm2.Transaction", _TrackedTransaction)

    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=10))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(10)]
    )

    await get_scrollback_impl(client, session_id_arg="sess-1", env_session_id=None, n_lines=10)

    assert enter_calls == ["<conn>"], "Transaction must be entered with the iTerm2 connection"
    assert exit_calls == ["<conn>"], "Transaction must be exited (clean) after both RPCs"


async def test_get_recent_output_wraps_line_info_and_contents_in_transaction(simple_app, monkeypatch):
    client = MagicMock()
    client.require_app.return_value = simple_app
    client.require_connection.return_value = "<conn>"
    session = simple_app.get_session_by_id("sess-1")

    entered = []

    class _TrackedTransaction:
        def __init__(self, conn):
            entered.append(conn)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr("mcp_server_iterm2.tools.read.iterm2.Transaction", _TrackedTransaction)

    session.async_get_line_info = AsyncMock(return_value=_line_info(overflow=0, total=5))
    session.async_get_contents = AsyncMock(
        return_value=[MagicMock(string=f"L{i}") for i in range(5)]
    )

    await get_recent_output_impl(
        client, session_id_arg="sess-1", env_session_id=None, cursor=None
    )
    assert entered == ["<conn>"]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_tools_read.py -k "wraps_line_info_and_contents_in_transaction" -v`
Expected: FAIL — `assert enter_calls == ["<conn>"]` because the impl never calls `iterm2.Transaction`.

- [ ] **Step 5: Wrap the RPCs in `get_scrollback_impl` and `get_recent_output_impl`**

In `src/mcp_server_iterm2/tools/read.py`:

```python
async def get_scrollback_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    n_lines: int = 200,
) -> dict[str, Any]:
    """Return the last N lines of scrollback (capped at SCROLLBACK_MAX)."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    conn = client.require_connection()
    async with iterm2.Transaction(conn):
        info = await session.async_get_line_info()
        total = info.scrollback_buffer_height + info.mutable_area_height
        take = min(max(n_lines, 0), SCROLLBACK_MAX, total)
        if take == 0:
            return {"text": ""}
        start = info.overflow + total - take
        line_contents = await session.async_get_contents(start, take)
    return {"text": "\n".join(lc.string for lc in line_contents)}


async def get_recent_output_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    cursor: str | None,
) -> dict[str, Any]:
    """Return output since the given cursor, or the visible screen if no cursor supplied."""
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    sid = session.session_id
    conn = client.require_connection()

    async with iterm2.Transaction(conn):
        info = await session.async_get_line_info()
        total = info.scrollback_buffer_height + info.mutable_area_height

        last_seen: int | None
        if cursor is None:
            if info.scrollback_buffer_height > 0:
                visible_start = info.overflow + info.scrollback_buffer_height
                last_seen = visible_start - 1
            else:
                last_seen = None
        else:
            _, last_seen = decode_cursor(cursor, expected_session_id=sid)

        diff = diff_since(overflow=info.overflow, line_count=total, last_seen=last_seen)

        if diff.first_line is None:
            return {
                "text": "",
                "cursor": encode_cursor(session_id=sid, line_number=diff.new_last_seen),
                "cursor_expired": diff.cursor_expired,
            }

        assert diff.last_line is not None
        count = diff.last_line - diff.first_line + 1
        line_contents = await session.async_get_contents(diff.first_line, count)

    return {
        "text": "\n".join(lc.string for lc in line_contents),
        "cursor": encode_cursor(session_id=sid, line_number=diff.new_last_seen),
        "cursor_expired": diff.cursor_expired,
    }
```

Note: `decode_cursor` may raise `CursorInvalid`; keep it inside the Transaction so it short-circuits cleanly (no in-flight RPCs to clean up).

- [ ] **Step 6: Run tests to verify everything passes**

Run: `uv run pytest tests/unit -v`
Expected: 79+ passed (including two new transaction tests).

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py tests/unit/conftest.py tests/unit/test_tools_read.py
git commit -m "fix: wrap line_info+get_contents in iterm2.Transaction per SDK contract"
```

---

## Task 3: Treat fresh-session cursor (`line_number < 0`) as not expired

**Bug:** `output_cursor.diff_since(line_count=0, last_seen=None)` returns `new_last_seen=-1`. The agent's continuation cursor encodes `line_number=-1`. On the next call, `diff_since` takes the `last_seen < lowest` branch and sets `cursor_expired=True` — falsely signaling lost lines when the agent simply started from an empty session.

**Files:**

- Modify: `src/mcp_server_iterm2/output_cursor.py`
- Modify: `tests/unit/test_output_cursor.py`

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_output_cursor.py`, add:

```python
def test_diff_since_negative_last_seen_is_treated_as_fresh_not_expired():
    """Cursor from a previously-empty session encodes line_number=-1.
    A later call with that cursor must report cursor_expired=False."""
    result = diff_since(overflow=0, line_count=10, last_seen=-1)
    assert result.first_line == 0
    assert result.last_line == 9
    assert result.cursor_expired is False
    assert result.new_last_seen == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_output_cursor.py::test_diff_since_negative_last_seen_is_treated_as_fresh_not_expired -v`
Expected: FAIL — `assert result.cursor_expired is False` fails because the code currently returns `cursor_expired=True`.

- [ ] **Step 3: Update `diff_since` to treat `last_seen < 0` as fresh**

In `src/mcp_server_iterm2/output_cursor.py`, modify `diff_since`:

```python
def diff_since(*, overflow: int, line_count: int, last_seen: int | None) -> DiffResult:
    """Compute the range of new lines since last_seen.

    iTerm2 line numbering is monotonically increasing. The currently
    addressable range is [overflow, overflow + line_count - 1].

    A `last_seen` value below zero is treated as "no prior cursor" rather
    than "cursor expired". This handles the case where the caller's prior
    fetch happened on an empty session (encoded as line_number=-1).
    """
    if line_count == 0:
        return DiffResult(None, None, -1, False)

    highest = overflow + line_count - 1
    lowest = overflow

    if last_seen is None or last_seen < 0:
        return DiffResult(lowest, highest, highest, False)

    if last_seen < lowest:
        return DiffResult(lowest, highest, highest, True)

    if last_seen >= highest:
        return DiffResult(None, None, last_seen, False)

    return DiffResult(last_seen + 1, highest, highest, False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_output_cursor.py -v`
Expected: all green (existing 8 + new 1).

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/output_cursor.py tests/unit/test_output_cursor.py
git commit -m "fix: treat negative cursor line as fresh, not expired, in diff_since"
```

---

## Task 4: Replace deprecated SDK property names

**Gap:** `iterm2/app.py:448-464` documents `current_terminal_window` and `terminal_windows` as deprecated in favor of `current_window` and `windows`. Our `list_sessions_impl` uses the deprecated names. Functional today; could break on a future SDK major.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`
- Modify: `tests/fixtures.py`

- [ ] **Step 1: Update fixture to expose modern property names**

In `tests/fixtures.py`, update `make_app`:

```python
def make_app(
    *,
    windows: list[MagicMock],
    current_window: MagicMock | None = None,
) -> MagicMock:
    app = MagicMock(name="app")
    chosen_current = current_window or (windows[0] if windows else None)
    app.windows = windows
    app.current_window = chosen_current
    # Back-compat aliases so any caller still using the deprecated names sees the same data.
    app.terminal_windows = windows
    app.current_terminal_window = chosen_current

    sessions_by_id = {s.session_id: s for w in windows for t in w.tabs for s in t.sessions}
    app.get_session_by_id = lambda sid: sessions_by_id.get(sid)

    tabs_by_id = {t.tab_id: t for w in windows for t in w.tabs}
    windows_by_tab_id = {t.tab_id: w for w in windows for t in w.tabs}
    app.get_tab_by_id = lambda tid: tabs_by_id.get(tid)
    app.get_window_for_tab = lambda tid: windows_by_tab_id.get(tid)
    return app
```

- [ ] **Step 2: Run tests to confirm fixture change is benign**

Run: `uv run pytest tests/unit -v`
Expected: all green (unchanged); fixture still exposes the old names for any caller.

- [ ] **Step 3: Update `list_sessions_impl` to use the modern names**

In `src/mcp_server_iterm2/tools/read.py`, replace the first three lines of `list_sessions_impl`:

```python
def list_sessions_impl(client: Any) -> dict[str, Any]:
    """Return the windows → tabs → sessions hierarchy."""
    app = client.require_app()
    current_window = app.current_window
    current_window_id = getattr(current_window, "window_id", None)

    out_windows = []
    for window in app.windows:
        # ... rest unchanged
```

- [ ] **Step 4: Run tests to verify they still pass**

Run: `uv run pytest tests/unit/test_tools_read.py -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py tests/fixtures.py
git commit -m "chore: use modern App.windows / current_window (SDK deprecated old names)"
```

---

## Task 5: Include minimized sessions via `tab.all_sessions`

**Gap:** `iterm2/tab.py:115-118` — `Tab.sessions` excludes minimized panes (which appear when another pane is maximized). `Tab.all_sessions` returns both visible and minimized. For a tool that exposes terminal state to agents, hiding minimized sessions is a completeness gap.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`
- Modify: `tests/fixtures.py`
- Modify: `tests/unit/test_tools_read.py`

- [ ] **Step 1: Update fixture factory to support minimized sessions**

In `tests/fixtures.py`, update `make_tab`:

```python
def make_tab(
    *,
    tab_id: int,
    sessions: list[MagicMock],
    minimized: list[MagicMock] | None = None,
    current: MagicMock | None = None,
) -> MagicMock:
    minimized_list = minimized or []
    t = MagicMock(name=f"tab-{tab_id}")
    t.tab_id = tab_id
    t.sessions = sessions
    t.minimized_sessions = minimized_list
    t.all_sessions = sessions + minimized_list
    t.current_session = current or (sessions[0] if sessions else None)
    for s in sessions + minimized_list:
        s.tab = t
    return t
```

Also update `make_app` so `get_session_by_id` discovers minimized sessions:

```python
def make_app(
    *,
    windows: list[MagicMock],
    current_window: MagicMock | None = None,
) -> MagicMock:
    app = MagicMock(name="app")
    chosen_current = current_window or (windows[0] if windows else None)
    app.windows = windows
    app.current_window = chosen_current
    app.terminal_windows = windows
    app.current_terminal_window = chosen_current

    sessions_by_id = {
        s.session_id: s
        for w in windows for t in w.tabs for s in t.all_sessions
    }
    app.get_session_by_id = lambda sid: sessions_by_id.get(sid)
    tabs_by_id = {t.tab_id: t for w in windows for t in w.tabs}
    windows_by_tab_id = {t.tab_id: w for w in windows for t in w.tabs}
    app.get_tab_by_id = lambda tid: tabs_by_id.get(tid)
    app.get_window_for_tab = lambda tid: windows_by_tab_id.get(tid)
    return app
```

- [ ] **Step 2: Write the failing test**

In `tests/unit/test_tools_read.py`, add:

```python
def test_list_sessions_includes_minimized_sessions():
    """When a pane is maximized, the other panes are minimized; list_sessions must include them."""
    from tests.fixtures import make_app, make_session, make_tab, make_window
    visible = make_session(session_id="sess-visible", name="zsh")
    minimized = make_session(session_id="sess-minimized", name="bash")
    tab = make_tab(tab_id=1, sessions=[visible], minimized=[minimized])
    window = make_window(window_id="win-1", tabs=[tab])
    app = make_app(windows=[window])

    client = MagicMock()
    client.require_app.return_value = app
    result = list_sessions_impl(client)
    sids = {s["session_id"] for s in result["windows"][0]["tabs"][0]["sessions"]}
    assert sids == {"sess-visible", "sess-minimized"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_tools_read.py::test_list_sessions_includes_minimized_sessions -v`
Expected: FAIL — only `sess-visible` is in the result because the impl iterates `tab.sessions`.

- [ ] **Step 4: Switch iteration to `tab.all_sessions` in `list_sessions_impl`**

In `src/mcp_server_iterm2/tools/read.py`, replace the session loop:

```python
            out_sessions = [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "active": s.session_id == current_session_id
                    and tab.tab_id == current_tab_id
                    and window.window_id == current_window_id,
                }
                for s in tab.all_sessions
            ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_tools_read.py -v`
Expected: all green (existing + minimized test).

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py tests/fixtures.py tests/unit/test_tools_read.py
git commit -m "fix: include minimized panes in list_sessions via tab.all_sessions"
```

---

## Task 6: Surface buried sessions in `list_sessions`

**Gap:** `App.buried_sessions` (`iterm2/app.py:466-472`) lists sessions that are buried — they have no window/tab placement in the visible hierarchy. Our `list_sessions` ignores them entirely, leaving agents blind to buried sessions even though they remain addressable via `get_session_by_id`. Schema change: add a top-level `"buried_sessions"` array to the response.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/read.py`
- Modify: `tests/fixtures.py`
- Modify: `tests/unit/test_tools_read.py`
- Modify: `README.md`, `CHANGELOG.md`

- [ ] **Step 1: Add `buried_sessions` field to the fixture**

In `tests/fixtures.py`, update `make_app`:

```python
def make_app(
    *,
    windows: list[MagicMock],
    current_window: MagicMock | None = None,
    buried_sessions: list[MagicMock] | None = None,
) -> MagicMock:
    app = MagicMock(name="app")
    chosen_current = current_window or (windows[0] if windows else None)
    buried = buried_sessions or []
    app.windows = windows
    app.current_window = chosen_current
    app.terminal_windows = windows
    app.current_terminal_window = chosen_current
    app.buried_sessions = buried

    sessions_by_id = {
        s.session_id: s
        for w in windows for t in w.tabs for s in t.all_sessions
    }
    for s in buried:
        sessions_by_id[s.session_id] = s
    app.get_session_by_id = lambda sid: sessions_by_id.get(sid)
    tabs_by_id = {t.tab_id: t for w in windows for t in w.tabs}
    windows_by_tab_id = {t.tab_id: w for w in windows for t in w.tabs}
    app.get_tab_by_id = lambda tid: tabs_by_id.get(tid)
    app.get_window_for_tab = lambda tid: windows_by_tab_id.get(tid)
    return app
```

Also update `tests/conftest.py`'s `simple_app` fixture to set `buried_sessions=[]`:

```python
@pytest.fixture
def simple_app() -> MagicMock:
    """One window, one tab, one session with id 'sess-1'; no buried sessions."""
    s1 = make_session(session_id="sess-1", name="bash")
    t1 = make_tab(tab_id=1, sessions=[s1])
    w1 = make_window(window_id="win-1", tabs=[t1])
    return make_app(windows=[w1], buried_sessions=[])
```

- [ ] **Step 2: Write the failing test**

In `tests/unit/test_tools_read.py`, add:

```python
def test_list_sessions_surfaces_buried_sessions():
    """Buried sessions live outside the window→tab tree; expose them as a top-level list."""
    from tests.fixtures import make_app, make_session, make_tab, make_window
    visible = make_session(session_id="sess-visible", name="zsh")
    buried = make_session(session_id="sess-buried", name="vim", buried=True)
    tab = make_tab(tab_id=1, sessions=[visible])
    window = make_window(window_id="win-1", tabs=[tab])
    app = make_app(windows=[window], buried_sessions=[buried])

    client = MagicMock()
    client.require_app.return_value = app
    result = list_sessions_impl(client)
    assert result["buried_sessions"] == [
        {"session_id": "sess-buried", "name": "vim"},
    ]
```

Also update `test_list_sessions_returns_hierarchy` (existing) to assert `"buried_sessions": []` in the result.

- [ ] **Step 3: Run tests to verify failure**

Run: `uv run pytest tests/unit/test_tools_read.py -k "list_sessions" -v`
Expected: FAIL — `KeyError: 'buried_sessions'` and the updated hierarchy test fails.

- [ ] **Step 4: Update `list_sessions_impl` to include buried sessions**

In `src/mcp_server_iterm2/tools/read.py`, at the end of `list_sessions_impl`:

```python
    buried = getattr(app, "buried_sessions", []) or []
    out_buried = [{"session_id": s.session_id, "name": s.name} for s in buried]
    return {"windows": out_windows, "buried_sessions": out_buried}
```

(`getattr` keeps backward-compat with a hypothetical older mock that doesn't set the attribute; real `iterm2.App` always sets it.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_tools_read.py -v`
Expected: all green.

- [ ] **Step 6: Document the schema change**

In `README.md`, update the `list_sessions` description row to:

```
| `list_sessions`       | Tree of windows → tabs → sessions, plus a top-level `buried_sessions` list. |
```

In `CHANGELOG.md`, under `[Unreleased]`:

```markdown
## [Unreleased]

### Changed
- `list_sessions` now also returns a top-level `buried_sessions` array. Buried
  sessions (created via the user's "Bury Session" command) are addressable via
  `get_session_by_id` but were previously invisible to `list_sessions`.
```

- [ ] **Step 7: Commit**

```bash
git add src/mcp_server_iterm2/tools/read.py tests/fixtures.py tests/conftest.py tests/unit/test_tools_read.py README.md CHANGELOG.md
git commit -m "feat: surface buried sessions in list_sessions response"
```

---

## Task 7: `set_tab_color` writes both light and dark variants

**Gap:** `iterm2/profile.py:1063` — `set_tab_color` "is used only when separate light/dark mode colors are not enabled." If the user's profile has split light/dark colors, our write silently does nothing. Fix: also call `set_tab_color_light` / `set_tab_color_dark` and the matching `set_use_tab_color_*` toggles so the color takes effect regardless of the split preference.

**Files:**

- Modify: `src/mcp_server_iterm2/tools/write.py`
- Modify: `tests/unit/test_tools_write.py`

- [ ] **Step 1: Write the failing test**

Replace `test_set_tab_color_writes_profile_properties` in `tests/unit/test_tools_write.py`:

```python
@patch("mcp_server_iterm2.tools.write.iterm2")
async def test_set_tab_color_writes_legacy_and_light_dark_variants(mock_iterm2, simple_app):
    client = MagicMock()
    client.require_app.return_value = simple_app
    session = simple_app.get_session_by_id("sess-1")
    session.async_set_profile_properties = AsyncMock()

    fake_profile = MagicMock()
    mock_iterm2.LocalWriteOnlyProfile.return_value = fake_profile
    color_instances = []
    def _make_color(r, g, b):
        c = MagicMock(name=f"color({r},{g},{b})")
        color_instances.append(c)
        return c
    mock_iterm2.Color.side_effect = _make_color

    result = await set_tab_color_impl(
        client, session_id_arg="sess-1", env_session_id=None, r=255, g=128, b=64
    )
    assert result == {"ok": True, "rgb": [255, 128, 64]}
    # Three Color(255,128,64) instances: one per variant.
    assert mock_iterm2.Color.call_args_list == [
        ((255, 128, 64),),
        ((255, 128, 64),),
        ((255, 128, 64),),
    ]
    # All three color setters called.
    assert fake_profile.set_tab_color.call_count == 1
    assert fake_profile.set_tab_color_light.call_count == 1
    assert fake_profile.set_tab_color_dark.call_count == 1
    # All three "use tab color" toggles set to True.
    fake_profile.set_use_tab_color.assert_called_once_with(True)
    fake_profile.set_use_tab_color_light.assert_called_once_with(True)
    fake_profile.set_use_tab_color_dark.assert_called_once_with(True)
    session.async_set_profile_properties.assert_awaited_once_with(fake_profile)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_tools_write.py::test_set_tab_color_writes_legacy_and_light_dark_variants -v`
Expected: FAIL — `set_tab_color_light` / `set_tab_color_dark` were never called.

- [ ] **Step 3: Update `set_tab_color_impl` to write all three variants**

In `src/mcp_server_iterm2/tools/write.py`:

```python
async def set_tab_color_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    r: int,
    g: int,
    b: int,
) -> dict[str, Any]:
    """Set the tab tint as RGB (each component 0-255).

    Writes the legacy `Tab Color` plus both `Tab Color (Light)` and
    `Tab Color (Dark)` so the change takes effect whether or not the
    user has split light/dark profile colors enabled.
    """
    for name, v in (("r", r), ("g", g), ("b", b)):
        if not (0 <= v <= 255):
            raise ValueError(f"{name}={v} out of range; expected 0-255")
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_tab_color(iterm2.Color(r, g, b))
    profile.set_tab_color_light(iterm2.Color(r, g, b))
    profile.set_tab_color_dark(iterm2.Color(r, g, b))
    profile.set_use_tab_color(True)
    profile.set_use_tab_color_light(True)
    profile.set_use_tab_color_dark(True)
    await session.async_set_profile_properties(profile)
    return {"ok": True, "rgb": [r, g, b]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_tools_write.py -v`
Expected: all green.

- [ ] **Step 5: Update README note for `set_tab_color`**

In `README.md`, update the rendering notes section:

```markdown
- **Tab color:** `set_tab_color` writes the legacy tab color plus both light- and dark-mode variants, so the tint takes effect regardless of the profile's split-color preference.
```

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server_iterm2/tools/write.py tests/unit/test_tools_write.py README.md
git commit -m "fix: set_tab_color writes light+dark variants so split-color profiles work"
```

---

## Definition of Done

- [ ] Tasks 1–7 all committed.
- [ ] `uv run pytest tests/unit` passes (≥ 84 tests).
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.
- [ ] `uv run ty check src` passes.
- [ ] `README.md` reflects the `list_sessions` schema change (Task 6) and the `set_tab_color` notes update (Task 7).
- [ ] `CHANGELOG.md` `[Unreleased]` section documents the `list_sessions` schema change.
- [ ] Optional follow-up (not in this plan): a smoke-script run from inside iTerm2 confirms `set_tab_color` works on a profile with split light/dark colors enabled.

---

## Out of scope (audit findings *not* fixed here)

These were flagged by the audit but are intentionally deferred:

- **Cookie request lacks `and key for app named "..."`.** Plan/spec authored the simpler form. Persistence is delegated to macOS Automation permission at the osascript-binary level. Acceptable.
- **`ITERM2_KEY` never set.** Functional cost is "no scripting-console entry tied to our script" — UX-only.
- **`session.async_get_variable("session.X")` form-vs-bare-name uncertainty.** Verified empirically by smoke/integration testing inside iTerm2; not provable from SDK source alone.
- **`session.name` refresh after `async_set_name`.** Plain attribute in SDK source; integration test relies on App's notification subscription to patch it. Not traced here.
