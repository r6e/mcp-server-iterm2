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
| `list_sessions`       | Tree of windows → tabs → sessions, plus a top-level `buried_sessions` list. |
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
- **Tab color:** `set_tab_color` writes the legacy tab color plus both light- and dark-mode variants, so the tint takes effect regardless of the profile's split-color preference.
- **Notifications:** routed through macOS via `osascript`. Make sure Terminal/iTerm2 notifications are allowed in System Settings if banners don't appear.

## Excluded by design

For safety, these are not exposed: `send_text`/keystroke injection, closing or spawning sessions/tabs/windows, splitting panes, focus changes, broadcasting input.

## Security model

Installing this server gives any MCP client that uses it broad read access to your iTerm2 sessions (screen contents, scrollback, working directories, variables) and limited write access (badge, title, tab color, `user.*` variables, macOS notifications). Read tools can capture passwords visible on screen; write tools can spoof titles and notifications. The full threat model and reporting flow live in [SECURITY.md](SECURITY.md).

## Development

```bash
uv sync
uv run pytest tests/unit       # 122 unit tests
uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run ty check src            # type check
```

Integration tests (`pytest -m integration`) and the smoke script (`scripts/smoke.py`) require running inside an iTerm2 session. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide and [ARCHITECTURE.md](ARCHITECTURE.md) for how the pieces fit together.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — module layout, lifecycle, data flow
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, quality gates, PR process
- [SECURITY.md](SECURITY.md) — threat model and how to report a vulnerability
- [CHANGELOG.md](CHANGELOG.md) — version history
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards

## License

MIT — see [LICENSE](LICENSE).
