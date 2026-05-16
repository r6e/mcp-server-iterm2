"""Non-destructive write tool implementations."""

from __future__ import annotations

from typing import Any

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
