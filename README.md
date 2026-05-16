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
