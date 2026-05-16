"""Exception types and tool-error formatting."""


class MCPIterm2Error(Exception):
    """Base for all expected errors surfaced to MCP tool callers."""


class ITermNotRunning(MCPIterm2Error):
    """iTerm2 process not running at server startup."""


class AuthDenied(MCPIterm2Error):
    """User declined the cookie authorization prompt."""


class Disconnected(MCPIterm2Error):
    """Connection to iTerm2 is currently down; reconnect in progress."""


class NoCurrentSession(MCPIterm2Error):
    """No session_id provided and ITERM_SESSION_ID is not set."""


class SessionNotFound(MCPIterm2Error):
    """A session_id was provided but does not match a live session."""

    def __init__(self, session_id: str) -> None:
        super().__init__(session_id)
        self.session_id = session_id


class CursorInvalid(MCPIterm2Error, ValueError):
    """The supplied cursor string could not be parsed or belongs to a different session."""


def to_error_text(err: BaseException) -> str:
    """Render an exception as actionable text for an MCP tool error response."""
    match err:
        case ITermNotRunning():
            return "iTerm2 is not running. Start iTerm2 and try again."
        case AuthDenied():
            return (
                "iTerm2 denied API authorization. "
                "Re-enable in iTerm2 → Preferences → General → Magic."
            )
        case Disconnected():
            return "iTerm2 unavailable, reconnecting."
        case NoCurrentSession():
            return (
                "No current session — pass session_id or run the MCP server "
                "from inside an iTerm2 session."
            )
        case SessionNotFound() as e:
            return f"session_id {e.session_id} not found."
        case CursorInvalid():
            return "Invalid cursor. Pass null to start from scratch."
        case _:
            return f"Internal error: {err}"
