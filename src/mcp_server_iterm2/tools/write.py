"""Non-destructive write tool implementations."""

from __future__ import annotations

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
