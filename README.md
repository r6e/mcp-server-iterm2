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
