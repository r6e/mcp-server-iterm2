import subprocess
from unittest.mock import patch

import pytest

from mcp_server_iterm2.cookie import request_cookie
from mcp_server_iterm2.errors import APINotEnabled, AuthDenied, ITermNotRunning


def _fake_completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(
        args=["osascript"], returncode=returncode, stdout=stdout, stderr=stderr
    )


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_returns_cookie_on_success(mock_run):
    mock_run.return_value = _fake_completed(stdout="abc123\n")
    assert request_cookie() == "abc123"


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_iterm_not_running_when_osascript_says_so(mock_run):
    mock_run.return_value = _fake_completed(
        returncode=1, stderr="execution error: iTerm2 got an error: Application isn’t running."
    )
    with pytest.raises(ITermNotRunning):
        request_cookie()


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_api_not_enabled_when_preference_disabled(mock_run):
    mock_run.return_value = _fake_completed(
        returncode=1,
        stderr="29:43: execution error: iTerm got an error: The Python API is not enabled. (1)",
    )
    with pytest.raises(APINotEnabled):
        request_cookie()


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_auth_denied_when_user_rejects(mock_run):
    mock_run.return_value = _fake_completed(
        returncode=1, stderr="User did not authorize API access."
    )
    with pytest.raises(AuthDenied):
        request_cookie()


@patch("mcp_server_iterm2.cookie.subprocess.run")
def test_other_failure_reraised_as_authdenied(mock_run):
    mock_run.return_value = _fake_completed(returncode=1, stderr="some other failure")
    with pytest.raises(AuthDenied):
        request_cookie()
