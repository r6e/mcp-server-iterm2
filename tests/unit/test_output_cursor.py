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
