"""Non-destructive write tool implementations."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

import iterm2  # type: ignore[import-untyped]

from mcp_server_iterm2.errors import SubprocessTimeout
from mcp_server_iterm2.session import resolve_session

_NOTIFICATION_TIMEOUT_S = 5.0

_MAX_BADGE = 256
_MAX_TITLE = 256
_MAX_VAR_NAME = 256
_MAX_VAR_VALUE = 4096
_MAX_NOTIFICATION_TITLE = 128
_MAX_NOTIFICATION_BODY = 1024


def _check_length(field: str, value: str, limit: int) -> None:
    if len(value) > limit:
        raise ValueError(f"{field} length {len(value)} exceeds limit {limit}")


def _escape_applescript_string(s: str) -> str:
    """Escape a Python string for safe embedding inside an AppleScript "..." literal.

    Order matters: backslash MUST be doubled FIRST so subsequent escapes don't
    get re-escaped. Then escape the closing-quote character and the three
    AppleScript-recognised C-style control escapes.
    """
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


async def set_badge_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    text: str,
) -> dict[str, Any]:
    _check_length("badge text", text, _MAX_BADGE)
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_variable("user.badge", text)
    return {"ok": True, "badge": text}


async def set_title_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    title: str,
) -> dict[str, Any]:
    _check_length("title", title, _MAX_TITLE)
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_name(title)
    return {"ok": True, "title": title}


async def set_tab_color_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    r: int,
    g: int,
    b: int,
) -> dict[str, Any]:
    for name, v in (("r", r), ("g", g), ("b", b)):
        if not (0 <= v <= 255):
            raise ValueError(f"{name}={v} out of range; expected 0-255")
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_tab_color(iterm2.Color(r, g, b))
    profile.set_use_tab_color(True)
    await session.async_set_profile_properties(profile)
    return {"ok": True, "rgb": [r, g, b]}


async def set_user_variable_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    name: str,
    value: str,
) -> dict[str, Any]:
    if not name.startswith("user."):
        raise ValueError(f"variable name must start with 'user.' (got {name!r})")
    _check_length("variable name", name, _MAX_VAR_NAME)
    _check_length("variable value", value, _MAX_VAR_VALUE)
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_variable(name, value)
    return {"ok": True, "name": name, "value": value}


async def post_notification_impl(*, title: str, body: str) -> dict[str, Any]:
    """Post a macOS notification via osascript.

    Does not take a client/connection parameter — uses osascript directly,
    not the iTerm2 SDK, because iTerm2 doesn't expose user-notification posting.
    """
    _check_length("notification title", title, _MAX_NOTIFICATION_TITLE)
    _check_length("notification body", body, _MAX_NOTIFICATION_BODY)

    script = (
        f'display notification "{_escape_applescript_string(body)}" '
        f'with title "{_escape_applescript_string(title)}"'
    )
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=_NOTIFICATION_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessTimeout(
            what="posting notification", seconds=_NOTIFICATION_TIMEOUT_S
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip() or 'unknown error'}")
    return {"ok": True}
