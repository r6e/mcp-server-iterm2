# Security Policy

## Reporting a vulnerability

**Do not open a public issue for security reports.** Use GitHub's private security advisory flow instead:

[Report a vulnerability](https://github.com/r6e/mcp-server-iterm2/security/advisories/new)

We will respond within 7 days. Coordinated disclosure is expected before details are made public.

## Supported versions

This project is pre-1.0. Only the latest tagged release on PyPI receives security fixes. Pin to a specific version in production and follow the changelog.

| Version | Supported |
|---|---|
| Latest tagged release | ✅ |
| Older releases | ❌ |

## Threat model

### What this server can do

The server exposes 13 tools to whatever MCP client invokes it. Read tools can:

- Enumerate every window, tab, and session iTerm2 has open (visible, minimized, and buried).
- Read the visible screen contents and scrollback of any session.
- Read any iTerm2 variable, including `session.path`, `session.username`, `session.hostname`, `session.tty`, and any `user.*` variable.

Write tools can:

- Set a session's badge, title, and tab color.
- Set `user.*` session variables (iTerm2 sandboxes these; non-`user` writes are rejected).
- Post a macOS notification banner via `osascript`.

### What this server intentionally cannot do

The tool surface is the security boundary. Keystroke injection, closing/spawning sessions or windows, splitting panes, focus changes, and writes to non-`user.*` variables or global preferences are not exposed. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full exclusion list.

### Trust gates

Three gates protect users:

1. **MCP client install.** The user explicitly added this server to their MCP client configuration. Anyone with that ability could have added something worse.
2. **macOS Automation permission.** On first run iTerm2 prompts to authorize the script. This permission is granted to the **`osascript` binary ↔ iTerm2** pair, not to `mcp-server-iterm2` itself. Any process the user can run as themselves can request the same cookie via the same `osascript` command — the permission is not server-scoped.
3. **iTerm2 cookie.** Each connection authenticates with a cookie issued by iTerm2 via AppleScript. The cookie lives only in process memory; it is not written to disk.

### Capabilities to be aware of

These behaviors are intentional, but operators should understand them before installing:

- **On-screen content capture.** `get_screen_contents` and `get_scrollback` return whatever the terminal shows. If a sudo prompt or password was visible — and most shells echo until you press Return — the agent sees it.
- **Title and badge spoofing.** `set_title` can replace a tab's title with text like `"sudo: password:"`. A user glancing at the title may type credentials thinking they're interacting with a system prompt.
- **macOS notification authority.** `post_notification` posts via `osascript`, so notifications display with whatever macOS labels osascript-launched notifications. Body and title are agent-controlled.
- **Other MCP clients on the same machine.** Once macOS grants `osascript ↔ iTerm2` automation, any process the user runs can shell out to `osascript -e 'tell application "iTerm2" to request cookie'` and obtain a valid cookie. The grant is not server-specific.

### Hardening already in place

The 0.1.0 codebase shipped with the following defenses (see commit history for details):

- All subprocess calls use absolute paths (`/usr/bin/osascript`), explicit timeouts, minimal `env=` dicts, and run via `asyncio.to_thread` to keep the event loop responsive.
- All user-supplied strings are length-bounded at the tool boundary before reaching the SDK or argv.
- Unknown exceptions are collapsed to `"Internal error: <ExceptionClass>"` so third-party error messages do not leak to agents; validated errors surface their actionable text via `InvalidArgument`.
- `iterm2.Transaction` wraps the `line_info` + `get_contents` RPC pair to prevent silent buffer-advance dropped lines.
- Cursor inputs are length-bounded and shape-validated (base64 → JSON → typed fields → range-bounded line number) before any work.
- AppleScript escaping for `post_notification` is property-tested against adversarial payloads (injection attempts, mixed backslash/quote, Unicode bidi).
- GitHub Actions in CI and publish workflows are pinned to immutable commit SHAs; Dependabot auto-bumps them.
- The PyPI publish workflow uses OIDC trusted publishing — no long-lived tokens.
- Ruff `S` (Bandit) rules are enabled in lint.

### Out of scope

These are not security issues we can address from this codebase:

- Compromise of iTerm2 itself. If iTerm2 is malicious, the trust model fails before we run.
- Compromise of macOS or the user account. Any process with the user's privileges can call `osascript` against iTerm2.
- Compromise of the MCP client (the agent). The client has full authority to call any tool we expose; the threat model assumes the client is trusted.
- Compromise of the user's PyPI install path or `uvx` cache.

## Disclosure

When a vulnerability is reported and fixed, we:

1. Land the fix in a tagged patch release.
2. Note the fix in [CHANGELOG.md](CHANGELOG.md) and the GitHub release notes.
3. Credit the reporter unless they request otherwise.
4. Publish a security advisory after users have had a reasonable window to upgrade.
