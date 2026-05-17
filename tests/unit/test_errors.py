from mcp_server_iterm2.errors import (
    APINotEnabled,
    AuthDenied,
    Disconnected,
    ITermNotRunning,
    NoCurrentSession,
    SessionNotFound,
    SubprocessTimeout,
    to_error_text,
)


def test_iterm_not_running_message():
    assert to_error_text(ITermNotRunning()) == (
        "iTerm2 is not running. Start iTerm2 and try again."
    )


def test_auth_denied_message():
    assert to_error_text(AuthDenied()) == (
        "iTerm2 denied API authorization for this script. "
        "Re-approve in iTerm2 → Settings → General → Magic."
    )


def test_api_not_enabled_message():
    assert to_error_text(APINotEnabled()) == (
        "iTerm2's Python API is not enabled. "
        "Enable it in iTerm2 → Settings → General → Magic → 'Enable Python API'."
    )


def test_disconnected_message():
    assert to_error_text(Disconnected()) == "iTerm2 unavailable, reconnecting."


def test_no_current_session_message():
    assert to_error_text(NoCurrentSession()) == (
        "No current session — pass session_id or run the MCP server from inside an iTerm2 session."
    )


def test_session_not_found_message():
    err = SessionNotFound(session_id="abc-123")
    assert to_error_text(err) == "session_id abc-123 not found."


def test_subprocess_timeout_message():
    err = SubprocessTimeout(what="requesting iTerm2 cookie", seconds=30.0)
    assert to_error_text(err) == ("osascript timed out after 30s while requesting iTerm2 cookie.")


def test_unknown_exception_falls_through_as_internal_error():
    assert to_error_text(ValueError("oops")) == "Internal error: oops"
