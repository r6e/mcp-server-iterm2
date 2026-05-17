import base64
import json

import pytest

from mcp_server_iterm2.output_cursor import (
    CursorInvalid,
    decode_cursor,
    diff_since,
    encode_cursor,
)


def test_encode_decode_roundtrip():
    raw = encode_cursor(session_id="abc-123", line_number=42)
    assert decode_cursor(raw) == ("abc-123", 42)


def test_decode_invalid_string_raises():
    with pytest.raises(CursorInvalid):
        decode_cursor("not-a-real-cursor")


def test_decode_cursor_from_wrong_session_raises():
    raw = encode_cursor(session_id="abc-123", line_number=10)
    with pytest.raises(CursorInvalid):
        decode_cursor(raw, expected_session_id="other-id")


def test_diff_since_no_cursor_returns_last_screenful():
    result = diff_since(overflow=0, line_count=200, last_seen=None)
    assert result.first_line == 0
    assert result.last_line == 199
    assert result.cursor_expired is False
    assert result.new_last_seen == 199


def test_diff_since_advances_from_last_seen():
    result = diff_since(overflow=0, line_count=200, last_seen=99)
    assert result.first_line == 100
    assert result.last_line == 199
    assert result.cursor_expired is False
    assert result.new_last_seen == 199


def test_diff_since_no_new_lines_returns_empty_range():
    result = diff_since(overflow=0, line_count=200, last_seen=199)
    assert result.first_line is None
    assert result.last_line is None
    assert result.new_last_seen == 199
    assert result.cursor_expired is False


def test_diff_since_cursor_expired_when_below_overflow():
    result = diff_since(overflow=500, line_count=200, last_seen=100)
    assert result.first_line == 500
    assert result.last_line == 699
    assert result.cursor_expired is True
    assert result.new_last_seen == 699


def test_diff_since_empty_session_returns_empty():
    result = diff_since(overflow=0, line_count=0, last_seen=None)
    assert result.first_line is None
    assert result.last_line is None
    assert result.cursor_expired is False
    assert result.new_last_seen == -1


def test_decode_cursor_rejects_oversize_input():
    # Length must be a multiple of 4 so base64 padding is valid — otherwise
    # the decoder rejects it first and the length guard is never reached.
    big = "A" * 16388  # 16388 % 4 == 0; still > _MAX_CURSOR_LEN (16384)
    with pytest.raises(CursorInvalid, match="exceeds limit"):
        decode_cursor(big)


def test_decode_cursor_rejects_non_string_sid():
    """Defense-in-depth: a base64-encoded cursor with a non-string sid must fail."""
    payload = json.dumps({"sid": 42, "line": 0}).encode("utf-8")
    cursor = base64.urlsafe_b64encode(payload).decode("ascii")
    with pytest.raises(CursorInvalid, match="not a string"):
        decode_cursor(cursor)


def test_decode_cursor_rejects_line_above_max():
    """Reject cursors with line numbers exceeding the iTerm2 line-index range."""
    payload = json.dumps({"sid": "sess-1", "line": 2**31}).encode("utf-8")
    cursor = base64.urlsafe_b64encode(payload).decode("ascii")
    with pytest.raises(CursorInvalid, match="line number out of range"):
        decode_cursor(cursor)


def test_decode_cursor_rejects_line_below_min():
    """Reject cursors with line numbers below the encodable range."""
    payload = json.dumps({"sid": "sess-1", "line": -(2**31) - 1}).encode("utf-8")
    cursor = base64.urlsafe_b64encode(payload).decode("ascii")
    with pytest.raises(CursorInvalid, match="line number out of range"):
        decode_cursor(cursor)


def test_decode_cursor_accepts_boundary_line_values():
    """The bounds are inclusive: 2**31 - 1 and -2**31 must both decode cleanly."""
    for value in (2**31 - 1, -(2**31)):
        payload = json.dumps({"sid": "sess-1", "line": value}).encode("utf-8")
        cursor = base64.urlsafe_b64encode(payload).decode("ascii")
        sid, line = decode_cursor(cursor)
        assert sid == "sess-1"
        assert line == value
