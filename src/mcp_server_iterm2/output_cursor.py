"""Opaque cursor encoding + scrollback diff logic for get_recent_output."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from mcp_server_iterm2.errors import CursorInvalid as CursorInvalid  # re-export

_MAX_CURSOR_LEN = 16384


def encode_cursor(*, session_id: str, line_number: int) -> str:
    payload = json.dumps({"sid": session_id, "line": line_number}).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_cursor(cursor: str, *, expected_session_id: str | None = None) -> tuple[str, int]:
    if len(cursor) > _MAX_CURSOR_LEN:
        raise CursorInvalid(f"cursor length {len(cursor)} exceeds limit {_MAX_CURSOR_LEN}")
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        sid = data["sid"]
        line = int(data["line"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CursorInvalid(str(exc)) from exc
    if not isinstance(sid, str):
        raise CursorInvalid("cursor sid is not a string")
    if expected_session_id is not None and sid != expected_session_id:
        raise CursorInvalid("cursor session_id mismatch")
    return sid, line


@dataclass(frozen=True)
class DiffResult:
    """The range of absolute line numbers to fetch (inclusive), or None if no new lines."""

    first_line: int | None
    last_line: int | None
    new_last_seen: int
    cursor_expired: bool


def diff_since(*, overflow: int, line_count: int, last_seen: int | None) -> DiffResult:
    """Compute the range of new lines since last_seen.

    iTerm2 line numbering is monotonically increasing. The currently
    addressable range is [overflow, overflow + line_count - 1].
    """
    if line_count == 0:
        return DiffResult(None, None, -1, False)

    highest = overflow + line_count - 1
    lowest = overflow

    if last_seen is None:
        return DiffResult(lowest, highest, highest, False)

    if last_seen < lowest:
        return DiffResult(lowest, highest, highest, True)

    if last_seen >= highest:
        return DiffResult(None, None, last_seen, False)

    return DiffResult(last_seen + 1, highest, highest, False)
