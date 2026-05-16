"""Non-destructive write tool implementations."""

from __future__ import annotations

import subprocess
from typing import Any

import iterm2  # type: ignore[import-untyped]

from mcp_server_iterm2.session import resolve_session


async def set_badge_impl(
    client: Any,
    *,
    session_id_arg: str | None,
    env_session_id: str | None,
    text: str,
) -> dict[str, Any]:
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
    app = client.require_app()
    session = resolve_session(app, session_id_arg, env_session_id)
    await session.async_set_variable(name, value)
    return {"ok": True, "name": name, "value": value}


async def post_notification_impl(*, title: str, body: str) -> dict[str, Any]:
    # AppleScript string-literal escape (distinct from shell escaping):
    # double the backslashes first, then escape embedded double quotes and
    # control characters that would break the single-line string literal.
    def _escape(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )

    script = f'display notification "{_escape(body)}" with title "{_escape(title)}"'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip() or 'unknown error'}")
    return {"ok": True}
