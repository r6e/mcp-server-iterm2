from unittest.mock import MagicMock

import pytest

from mcp_server_iterm2.errors import NoCurrentSession, SessionNotFound
from mcp_server_iterm2.session import resolve_session


def _app_with(sessions: dict[str, MagicMock]) -> MagicMock:
    app = MagicMock()
    app.get_session_by_id = MagicMock(side_effect=lambda sid: sessions.get(sid))
    return app


def test_explicit_session_id_wins():
    s_explicit = MagicMock(name="explicit")
    app = _app_with({"explicit-id": s_explicit})
    result = resolve_session(app, session_id_arg="explicit-id", env_session_id="env-id")
    assert result is s_explicit


def test_falls_back_to_env_session_id():
    s_env = MagicMock(name="env")
    app = _app_with({"env-id": s_env})
    result = resolve_session(app, session_id_arg=None, env_session_id="env-id")
    assert result is s_env


def test_no_current_session_when_both_missing():
    app = _app_with({})
    with pytest.raises(NoCurrentSession):
        resolve_session(app, session_id_arg=None, env_session_id=None)


def test_no_current_session_when_env_is_empty_string():
    app = _app_with({})
    with pytest.raises(NoCurrentSession):
        resolve_session(app, session_id_arg=None, env_session_id="")


def test_session_not_found_raises_with_id():
    app = _app_with({})
    with pytest.raises(SessionNotFound) as exc:
        resolve_session(app, session_id_arg="missing-id", env_session_id=None)
    assert exc.value.session_id == "missing-id"


def test_session_not_found_for_stale_env_id():
    app = _app_with({})
    with pytest.raises(SessionNotFound) as exc:
        resolve_session(app, session_id_arg=None, env_session_id="stale-id")
    assert exc.value.session_id == "stale-id"
