"""Request an iTerm2 API cookie via AppleScript."""

import subprocess

from mcp_server_iterm2.errors import APINotEnabled, AuthDenied, ITermNotRunning, SubprocessTimeout

_OSASCRIPT_COMMAND = [
    "/usr/bin/osascript",
    "-e",
    'tell application "iTerm2" to request cookie',
]
_COOKIE_TIMEOUT_S = 30.0


def request_cookie() -> str:
    """Run osascript to request a one-time cookie.

    Returns the cookie string. Raises:
      - ITermNotRunning if iTerm2 isn't running.
      - APINotEnabled if the Python API toggle is off in iTerm2 prefs.
      - AuthDenied if the user denied this script.
      - SubprocessTimeout if osascript doesn't return within _COOKIE_TIMEOUT_S.
    """
    try:
        result = subprocess.run(
            _OSASCRIPT_COMMAND,
            capture_output=True,
            text=True,
            check=False,
            timeout=_COOKIE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessTimeout(what="requesting iTerm2 cookie", seconds=_COOKIE_TIMEOUT_S) from exc

    if result.returncode == 0:
        return result.stdout.strip()

    stderr_lower = result.stderr.lower()
    if "isn’t running" in result.stderr or "application isn't running" in stderr_lower:
        raise ITermNotRunning()
    if "python api is not enabled" in stderr_lower:
        raise APINotEnabled()
    raise AuthDenied()
