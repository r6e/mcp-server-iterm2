"""Manual smoke test: exercises every tool against the current iTerm2 session.

Run from inside an iTerm2 session:

    uv run python scripts/smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp_server_iterm2.connection import ITermClient
from mcp_server_iterm2.tools import read, write


async def main() -> int:
    sid = os.environ.get("ITERM_SESSION_ID")
    if not sid:
        print("ERROR: ITERM_SESSION_ID is not set. Run this from inside an iTerm2 session.")
        return 1

    client = ITermClient()
    await client._connect_once()
    passes = 0
    failures: list[tuple[str, str]] = []

    def _record(label: str, value: object, error: Exception | None) -> None:
        nonlocal passes
        if error is not None:
            failures.append((label, repr(error)))
            print(f"FAIL  {label:<24} {error!r}")
            return
        passes += 1
        preview = repr(value)
        if len(preview) > 80:
            preview = preview[:77] + "..."
        print(f"PASS  {label:<24} {preview}")

    async def _run(label: str, coro: object) -> None:
        try:
            value = await coro  # type: ignore[misc]
        except Exception as e:
            _record(label, None, e)
            return
        _record(label, value, None)

    def _run_sync(label: str, fn: object) -> None:
        try:
            value = fn()  # type: ignore[operator]
        except Exception as e:
            _record(label, None, e)
            return
        _record(label, value, None)

    # list_sessions_impl is the only sync impl; everything else is async.
    _run_sync("list_sessions", lambda: read.list_sessions_impl(client))
    await _run(
        "get_session_info",
        read.get_session_info_impl(client, session_id_arg=sid, env_session_id=None),
    )
    await _run(
        "get_screen_contents",
        read.get_screen_contents_impl(client, session_id_arg=sid, env_session_id=None),
    )
    await _run(
        "get_scrollback",
        read.get_scrollback_impl(client, session_id_arg=sid, env_session_id=None),
    )
    await _run(
        "get_recent_output",
        read.get_recent_output_impl(client, session_id_arg=sid, env_session_id=None, cursor=None),
    )
    await _run(
        "get_selection",
        read.get_selection_impl(client, session_id_arg=sid, env_session_id=None),
    )
    await _run(
        "get_variable",
        read.get_variable_impl(
            client, session_id_arg=sid, env_session_id=None, name="session.path"
        ),
    )
    await _run("list_profiles", read.list_profiles_impl(client))

    await _run(
        "set_badge",
        write.set_badge_impl(client, session_id_arg=sid, env_session_id=None, text="smoke"),
    )
    await _run(
        "set_title",
        write.set_title_impl(client, session_id_arg=sid, env_session_id=None, title="smoke test"),
    )
    await _run(
        "set_tab_color",
        write.set_tab_color_impl(
            client, session_id_arg=sid, env_session_id=None, r=80, g=160, b=240
        ),
    )
    await _run(
        "set_user_variable",
        write.set_user_variable_impl(
            client, session_id_arg=sid, env_session_id=None, name="user.smoke", value="ok"
        ),
    )
    await _run(
        "post_notification",
        write.post_notification_impl(title="smoke", body="all tools exercised"),
    )

    total = passes + len(failures)
    print(f"\n{passes}/{total} passed; {len(failures)} failed.")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
