"""Unit tests for Shell Command Execution tool (REQ-025)."""

from __future__ import annotations

import tempfile

import pytest

from backend.tools.shell import execute_shell


@pytest.fixture
def workspace_dir() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory()


@pytest.mark.unit
@pytest.mark.smoke
def test_execute_shell_basic(workspace_dir: tempfile.TemporaryDirectory[str]) -> None:
    ws = workspace_dir.name
    res = execute_shell("echo 'Hello From Shell'", workspace_root=ws)
    assert "Hello From Shell" in res


@pytest.mark.unit
def test_execute_shell_deny_list(
    workspace_dir: tempfile.TemporaryDirectory[str],
) -> None:
    ws = workspace_dir.name
    # Dangerous patterns must be blocked immediately
    with pytest.raises(PermissionError):
        execute_shell("rm -rf /", workspace_root=ws)

    with pytest.raises(PermissionError):
        execute_shell("sudo su", workspace_root=ws)


@pytest.mark.unit
def test_execute_shell_timeout(workspace_dir: tempfile.TemporaryDirectory[str]) -> None:
    ws = workspace_dir.name
    res = execute_shell("sleep 5", workspace_root=ws, timeout=1)
    assert "[ERROR]" in res
    assert "timed out" in res
