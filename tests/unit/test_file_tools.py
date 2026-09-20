"""Unit tests for File System tools (REQ-023, REQ-024)."""

from __future__ import annotations

import tempfile

import pytest

from backend.tools.file import (
    edit_file,
    list_directory,
    read_file,
    search_files,
    write_file,
)


@pytest.fixture
def workspace_dir() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory()


@pytest.mark.unit
@pytest.mark.smoke
def test_write_and_read_file(workspace_dir: tempfile.TemporaryDirectory[str]) -> None:
    ws = workspace_dir.name

    # Write file
    res_write = write_file("test.txt", "Hello World!\nLine 2", ws)
    assert "Successfully wrote" in res_write

    # Read file
    content = read_file("test.txt", ws)
    assert content == "Hello World!\nLine 2"


@pytest.mark.unit
def test_edit_file(workspace_dir: tempfile.TemporaryDirectory[str]) -> None:
    ws = workspace_dir.name

    write_file("code.py", "def old_name():\n    pass\n", ws)

    res_edit = edit_file("code.py", "def old_name():", "def new_name():", ws)
    assert "Successfully edited" in res_edit

    content = read_file("code.py", ws)
    assert "def new_name():" in content


@pytest.mark.unit
def test_list_directory_and_search_files(
    workspace_dir: tempfile.TemporaryDirectory[str],
) -> None:
    ws = workspace_dir.name

    write_file("sub/file1.txt", "SpecialKeyword in file 1", ws)
    write_file("sub/file2.txt", "Another text here", ws)
    write_file("file3.txt", "SpecialKeyword in file 3", ws)

    # List directory
    listing = list_directory("sub", ws)
    assert "file1.txt" in listing
    assert "file2.txt" in listing

    # Search files
    search_res = search_files("sub", "SpecialKeyword", workspace=ws)
    assert "file1.txt" in search_res
    assert "SpecialKeyword in file 1" in search_res


@pytest.mark.unit
def test_workspace_path_escape_blocked(
    workspace_dir: tempfile.TemporaryDirectory[str],
) -> None:
    ws = workspace_dir.name

    # Reading outside workspace
    with pytest.raises(PermissionError):
        read_file("../../etc/passwd", ws)

    # Writing outside workspace
    with pytest.raises(PermissionError):
        write_file("../out.txt", "evil", ws)
