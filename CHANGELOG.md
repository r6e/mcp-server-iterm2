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
