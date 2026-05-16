# mcp-server-iterm2 — Design

**Status:** Approved, pending implementation plan
**Date:** 2026-05-16
**Owner:** rob (<me@r6e.dev>)

## Goal

A Model Context Protocol (MCP) server that exposes iTerm2 to agents for **observation** and **non-destructive annotation**. Agents can inspect sessions, read screen contents, and decorate sessions (badge, title, tab color, user variables, notifications). They cannot inject keystrokes, close or spawn sessions, focus tabs, or otherwise alter the user's working environment.

The primary use case is an agent running _inside_ iTerm2 that wants to read its own context and label its own session — for example, setting a badge that reflects which task it is working on, or reading scrollback to recover from a lost interactive prompt.

## Non-goals

- Keystroke injection or `send_text`-style writes
- Creating, closing, splitting, or focusing sessions/tabs/windows
- Broadcasting input across sessions
- Streaming session output as an MCP resource (a request/response cursor pattern is used instead)
- Per-session permission gating or allowlists (installation is the trust gate)
- Windows or Linux support (iTerm2 is macOS-only)

## Architecture

### Stack

- Python 3.12+
- Official `iterm2` SDK (WebSocket-based, async)
- `mcp` Python SDK (stdio transport)
- `uv` for project + dependency management
- `pytest` for tests, `ruff` for lint+format, `ty` (Astral) for type checking
- PyPI distribution: `mcp-server-iterm2`

### Process model

The MCP server runs as a stdio subprocess of the agent (the standard MCP transport). On startup it:

1. Requests an iTerm2 cookie via AppleScript:
   `osascript -e 'tell application "iTerm2" to request cookie'`
   This prompts the user once for authorization; subsequent runs are silent.
2. Sets `ITERM2_COOKIE` (and `ITERM2_KEY` if returned) in its own environment.
3. Calls `iterm2.Connection.async_create()` to establish a persistent WebSocket connection.
4. Captures `$ITERM_SESSION_ID` from its inherited environment as the default session for tool calls.
5. Registers MCP tools and begins serving over stdio.

The connection persists for the server's lifetime. On disconnect (iTerm2 quit/restart), a background task reconnects with exponential backoff (1s, 2s, 4s, capped at 30s). Tool calls during outage return a structured `iTerm2 unavailable, reconnecting` error rather than blocking indefinitely.

### Module layout

```plaintext
mcp-server-iterm2/
  src/mcp_server_iterm2/
    __init__.py
    server.py          # MCP server setup, tool registration
    connection.py      # iTerm2 connection lifecycle + reconnect
    session.py         # session resolution (caller's session vs explicit override)
    output_cursor.py   # marker-based scrollback diffing for get_recent_output
    tools/
      __init__.py
      read.py          # list_sessions, get_session_info, get_screen, etc.
      write.py         # set_badge, set_title, set_tab_color, etc.
  tests/
    unit/              # mocked iterm2 SDK; runs in plain `pytest`
    integration/       # opt-in via `pytest -m integration`; requires iTerm2
    fixtures.py        # factory functions for synthetic snapshots
  scripts/
    smoke.py           # manual smoke test exercising every tool
  docs/superpowers/specs/
    2026-05-16-mcp-server-iterm2-design.md
  pyproject.toml
  .python-version      # 3.12
  .gitignore
  README.md
  LICENSE              # MIT
  CHANGELOG.md
  .github/workflows/
    ci.yml             # ruff + ty + pytest on 3.12, 3.13
    publish.yml        # tag-triggered PyPI publish
```

Module responsibilities are deliberately narrow. `connection.py` knows iTerm2 but not MCP; `server.py` knows MCP but not iTerm2 internals; `tools/*.py` translate MCP arguments → connection calls → MCP responses, nothing more. Tests can isolate each layer.

## Tool surface

### Conventions

- Every tool that targets a session accepts an optional `session_id` argument. Omitted → resolves to `$ITERM_SESSION_ID`. If neither is present, the tool returns a clear "no current session — pass `session_id` or run the MCP server from inside an iTerm2 session" error.
- Tools return structured JSON. Errors are returned as tool-call errors with actionable messages ("iTerm2 not running", "session_id not found", "iTerm2 unavailable, reconnecting"), never as raw Python tracebacks.
- All tools are read-only or non-destructive. No tool writes to a session's TTY or alters the user's focus, tabs, or windows.

### Read tools

| Tool                  | Returns                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `list_sessions`       | Tree of windows → tabs → sessions with IDs, titles, active flags                                                      |
| `get_session_info`    | Title, working directory, profile name, badge, dimensions (cols × rows), TTY path                                     |
| `get_screen_contents` | Visible buffer text + cursor position (row, column)                                                                   |
| `get_scrollback`      | Last N lines of scrollback (default 200, capped at 5000)                                                              |
| `get_recent_output`   | Output since a cursor marker. Returns `{text, cursor}`. First call (no cursor) returns last screenful + a new cursor. |
| `get_selection`       | Currently selected text in the session                                                                                |
| `get_variable`        | Read a variable by fully-qualified name (e.g. `session.username`, `tab.title`, `user.foo`)                            |
| `list_profiles`       | Available iTerm2 profiles by name and GUID                                                                            |

`get_recent_output`'s cursor is an opaque string. Internally it encodes `(session_id, scrollback_offset)`. The agent treats it as a black box; it passes back whatever the server handed out. If the cursor has aged out of scrollback (offset older than the buffer holds), the server returns all currently-available output since the oldest reachable point and includes a `cursor_expired: true` flag in the response so the agent knows it may have missed lines.

### Write tools (non-destructive)

| Tool                | Effect                                                                                                                                    |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `set_badge`         | Set session badge text (the floating overlay)                                                                                             |
| `set_title`         | Override session title                                                                                                                    |
| `set_tab_color`     | Set tab tint as RGB (0–255 each)                                                                                                          |
| `set_user_variable` | Set a `user.foo` session variable (these are sandboxed to user-defined names by iTerm2)                                                   |
| `post_notification` | Post a macOS notification via iTerm2 — useful for "long task done" signaling. Edge case: user-visible, but does not alter terminal state. |

### Explicitly excluded

The following are intentionally **not** exposed:

- `send_text` / keystroke injection
- `close_session` / `close_tab` / `close_window`
- `split_pane` / `new_tab` / `new_window`
- `broadcast_input`
- `select_tab` / focus changes (the user may be working in another tab)
- Writes to non-user variables, profiles, or global preferences

## Authentication & connection lifecycle

### Cookie acquisition

iTerm2's Python API requires authentication. Two mechanisms exist:

1. Auto-launch scripts registered in iTerm2's Scripts menu — not viable for an MCP subprocess.
2. One-time cookie via AppleScript — this is what we use.

On startup, the server shells out to `osascript -e 'tell application "iTerm2" to request cookie'`. iTerm2 prompts the user to authorize _this script_ on first request; subsequent requests are silent (authorization is remembered per-script-name). The returned cookie is set as `ITERM2_COOKIE` in the server's env before `iterm2.Connection.async_create()` is called.

### Failure modes

| Condition                                              | Behavior                                                                                                                                  |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| iTerm2 not running at startup                          | Exit with `iTerm2 is not running. Start iTerm2 and try again.`                                                                            |
| User denies authorization                              | Exit with `iTerm2 denied API authorization. Re-enable in iTerm2 → Preferences → General → Magic.`                                         |
| Connection drops mid-session                           | Background reconnect with backoff 1s → 2s → 4s → ... → 30s cap. Tool calls during outage return `iTerm2 unavailable, reconnecting` error. |
| `$ITERM_SESSION_ID` unset and no `session_id` argument | Return `no current session — pass session_id or run the MCP server from inside an iTerm2 session` error.                                  |
| `session_id` does not match any current session        | Return `session_id X not found` error.                                                                                                    |

### Permission model

Installing the MCP server is the trust gate. There is no per-tool or per-session allowlist. The non-destructive guarantee comes from the **tool surface** itself: destructive operations simply aren't exposed. This is a deliberate simplification; revisit if/when a real need for scoping emerges.

## Distribution

### PyPI

Published as `mcp-server-iterm2` with a console-script entry point of the same name. MCP client configuration:

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

`uvx` handles isolated install and execution. For development/pre-release: `uvx --from git+https://github.com/<owner>/mcp-server-iterm2 mcp-server-iterm2`.

### Tooling

- `uv` for venv + dependency management (`uv sync`, `uv run`).
- `pyproject.toml` is the single source of truth for metadata, deps, ruff config, and ty config.
- `ruff` for lint + format. Strict-ish defaults with a narrowly curated set of disabled rules.
- `ty` (Astral) for type checking, configured under `[tool.ty]` in `pyproject.toml`. Run as `uv run ty check`. Note: ty is still pre-1.0/preview; expect occasional config churn.
- `pytest` for tests.
- Pre-commit hook: ruff format, ruff check, ty check, pytest (unit only).
- GitHub Actions CI: lint + typecheck + unit tests on Python 3.12 and 3.13. Integration tests are not run in CI (require a running iTerm2).

### Versioning

Semver, starting at `0.1.0`. Tagged releases (`v*`) trigger the publish workflow.

### License

MIT.

## Testing strategy

Per project conventions: TDD always. Tests written first, run red, then implementation makes them green. Coverage target ≥ 80%.

### Tier 1: Unit (default `pytest`, no iTerm2 needed)

Mock the `iterm2` SDK at the module boundary. Coverage targets:

- Session resolution: caller-default, explicit override, no-current error
- Cursor encoding/decoding for `get_recent_output`
- Tool argument validation and error message shape
- Reconnect backoff logic with a fake clock
- Connection failure → tool-call error translation (never a raw traceback)
- Tool response JSON shape against fixture snapshots

### Tier 2: Integration (`pytest -m integration`, requires iTerm2)

Opt-in. CI skips by default; runs locally and optionally on a self-hosted macOS runner with iTerm2 installed. Coverage targets:

- Cookie request via osascript end-to-end
- `list_sessions` returns a real hierarchy
- `set_badge` / `set_title` / `set_tab_color` round-trip via `get_session_info`
- `get_screen_contents` / `get_scrollback` against a controlled ephemeral session (test scaffolding creates a session via the underlying SDK, writes known text, reads back, cleans up — this is permissible inside the test harness even though the public tool surface forbids it)
- `get_recent_output` cursor advances correctly across writes
- Reconnect after a forced iTerm2 quit/restart

### Tier 3: Smoke (manual)

`uv run python scripts/smoke.py` runs every public tool once against the user's current iTerm2 session and prints a pass/fail summary. Used before tagging a release.

### Out of scope for testing

- The `iterm2` SDK itself (third-party, mocked at boundary)
- The MCP SDK wire protocol (third-party, mocked at boundary)

## Risks & open questions

- **`ty` maturity.** ty is pre-1.0. If config churn or false positives become disruptive, fall back to mypy temporarily. Decision deferred to implementation.
- **iTerm2 authorization UX.** First-run prompt is unavoidable. README needs a clear "first run" section so users aren't surprised.
- **Namespace collision.** `iterm2-mcp` on PyPI is taken by an unrelated full-control server. Using `mcp-server-iterm2` follows the MCP-org convention (e.g. `mcp-server-filesystem`) and avoids the collision.
- **`post_notification` borderline case.** User-visible but state-neutral. Included with the option to remove if it causes annoyance in practice.
- **Session ID stability.** iTerm2 session IDs are stable for a session's lifetime but vanish on close. Agents holding stale IDs get a clear error; no recovery logic needed.
- **`set_title` profile override.** Whether a title override sticks depends on the profile's "Allow terminal apps to change title" and "Title Components" settings. The tool sets the override successfully in all cases; whether it is rendered is iTerm2-controlled. README should document this so users aren't surprised.

## What success looks like

- `uvx mcp-server-iterm2` works on a fresh macOS install with iTerm2 present.
- An agent running in iTerm2 can call `set_badge` and `get_screen_contents` against itself with no extra configuration beyond MCP client setup.
- A user can drop the server config into their MCP client, approve once, and never think about it again.
- All 13 tools have unit tests; all 13 have integration tests; smoke script covers all 13.
- CI is green on 3.12 and 3.13.
