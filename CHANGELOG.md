# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-05-17

### Fixed

- Correct author email in package metadata. No functional changes; 0.1.0 is
  yanked.

## [0.1.0] - 2026-05-16

Initial release.

### Added

- Persistent iTerm2 connection with exponential-backoff reconnect (1s → 30s cap)
  and automatic disconnect detection.
- 8 read tools: `list_sessions`, `get_session_info`, `get_screen_contents`,
  `get_scrollback`, `get_recent_output`, `get_selection`, `get_variable`,
  `list_profiles`. `list_sessions` returns visible, minimized, and buried
  sessions; `buried_sessions` lives at the top level since they have no
  window/tab placement.
- 5 non-destructive write tools: `set_badge`, `set_title`, `set_tab_color`,
  `set_user_variable`, `post_notification`. `set_tab_color` writes the legacy
  tab color plus light- and dark-mode variants so the tint takes effect
  regardless of the profile's split-color preference.
- Cursor-based pagination for `get_recent_output` with stale-cursor detection
  (`cursor_expired: true` when the buffer has rolled past the prior cursor).
- Default session resolution from `$ITERM_SESSION_ID` (position prefix stripped)
  with explicit `session_id` override on every session-targeted tool.
- `iterm2.Transaction` wrapping for the `line_info`/`get_contents` RPC pair
  per SDK contract.
- `InvalidArgument` error class surfacing validation failures (length, range,
  prefix) to the agent with actionable detail; unknown exceptions collapse
  to a generic `Internal error: <ExceptionClass>` envelope to avoid leaking
  third-party library messages.
- Length bounds on every user-supplied string (badge, title, variable name
  and value, notification title and body, cursor) at the tool boundary,
  before any RPC or argv construction.

### Security

- Subprocess hygiene: absolute `/usr/bin/osascript` path, explicit timeouts
  (`SubprocessTimeout` error class), minimal `env=` that strips `ITERM2_COOKIE`
  from child processes, all calls run via `asyncio.to_thread` so they never
  block the event loop.
- AppleScript escaping for `post_notification` covered by adversarial-payload
  tests (injection attempts, mixed backslash/quote, Unicode bidi).
- All GitHub Actions in CI and publish workflows pinned to immutable commit
  SHAs; Dependabot auto-bumps them.
- PyPI publish workflow uses OIDC trusted publishing — no long-lived tokens.
- Ruff `S` (Bandit) rules enabled.
- Validation order in `set_user_variable` checks length before the `user.`
  prefix violation so oversize names cannot echo back through the error
  message.

### Documentation

- README, ARCHITECTURE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, CHANGELOG.
- GitHub issue templates (bug report, feature request) with security routing
  to private advisories.
- Pull request template with test plan, doc checklist, and security checklist.
