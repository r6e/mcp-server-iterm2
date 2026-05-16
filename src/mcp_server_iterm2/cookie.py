"""Request an iTerm2 API cookie via AppleScript."""

import subprocess

from mcp_server_iterm2.errors import AuthDenied, ITermNotRunning

_OSASCRIPT_COMMAND = [
    "osascript",
    "-e",
    'tell application "iTerm2" to request cookie',
]


def request_cookie() -> str:
    """Run osascript to request a one-time cookie.

    Returns the cookie string. Raises ITermNotRunning if iTerm2 is not
    running, or AuthDenied if the user rejects the prompt (or any other
    osascript failure occurs).
    """
    result = subprocess.run(
        _OSASCRIPT_COMMAND,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    stderr = result.stderr.lower()
    if "isn’t running" in result.stderr or "application isn't running" in stderr:
        raise ITermNotRunning()
    raise AuthDenied()
