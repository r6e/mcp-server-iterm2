"""Request an iTerm2 API cookie via AppleScript."""

import subprocess

from mcp_server_iterm2.errors import APINotEnabled, AuthDenied, ITermNotRunning

_OSASCRIPT_COMMAND = [
    "/usr/bin/osascript",
    "-e",
    'tell application "iTerm2" to request cookie',
]


def request_cookie() -> str:
    """Run osascript to request a one-time cookie.

    Returns the cookie string. Raises:
      - ITermNotRunning if iTerm2 isn't running.
      - APINotEnabled if the Python API toggle is off in iTerm2 prefs.
      - AuthDenied if the user denied this script (or any other osascript failure).
    """
    result = subprocess.run(
        _OSASCRIPT_COMMAND,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    stderr_lower = result.stderr.lower()
    if "isn’t running" in result.stderr or "application isn't running" in stderr_lower:
        raise ITermNotRunning()
    if "python api is not enabled" in stderr_lower:
        raise APINotEnabled()
    raise AuthDenied()
