"""File system tools with workspace path containment (REQ-023, REQ-024).

All operations resolve paths against the caller-supplied workspace root and
reject anything that escapes it.  This is a defence-in-depth measure on top
of the PolicyEngine check; neither layer alone should be relied upon.
"""

from __future__ import annotations

import os
from pathlib import Path

# Default workspace root used when no root is specified (tests / ad-hoc calls).
_DEFAULT_WORKSPACE = Path(os.getenv("FORGE_WORKSPACE", "/tmp/forge_workspace"))


def _resolve_safe(path: str, workspace: str | Path | None = None) -> Path:
    """Resolve *path* and verify it is inside *workspace*.

    Raises :class:`PermissionError` if the resolved path escapes the workspace.
    """
    root = Path(workspace).resolve() if workspace else _DEFAULT_WORKSPACE.resolve()
    resolved = (
        (root / path).resolve()
        if not Path(path).is_absolute()
        else Path(path).resolve()
    )
    try:
        resolved.relative_to(root)
    except ValueError:
        raise PermissionError(
            f"Path '{path}' resolves to '{resolved}' which is outside workspace '{root}'"
        )
    return resolved


# ── REQ-023: File read and search ─────────────────────────────────────────────


def read_file(path: str, workspace: str | Path | None = None) -> str:
    """Return the UTF-8 contents of *path* (relative or absolute).

    Raises :class:`PermissionError` for paths outside the workspace.
    Raises :class:`FileNotFoundError` if the file does not exist.
    """
    safe = _resolve_safe(path, workspace)
    return safe.read_text(encoding="utf-8")


def list_directory(path: str = ".", workspace: str | Path | None = None) -> str:
    """Return a newline-separated listing of *path*."""
    safe = _resolve_safe(path, workspace)
    if not safe.is_dir():
        raise NotADirectoryError(f"'{path}' is not a directory")
    entries = sorted(safe.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = []
    for entry in entries:
        kind = "FILE" if entry.is_file() else "DIR "
        size = f"{entry.stat().st_size:>10}" if entry.is_file() else "          "
        lines.append(f"{kind}  {size}  {entry.name}")
    return "\n".join(lines) or "(empty directory)"


def search_files(
    directory: str,
    pattern: str,
    file_glob: str = "*",
    workspace: str | Path | None = None,
) -> str:
    """Recursively search files matching *file_glob* for lines containing *pattern*.

    Returns grep-style ``path:lineno:line`` output, capped at 200 matches.
    """
    safe_dir = _resolve_safe(directory, workspace)
    if not safe_dir.is_dir():
        raise NotADirectoryError(f"'{directory}' is not a directory")

    matches: list[str] = []
    for filepath in sorted(safe_dir.rglob(file_glob)):
        if not filepath.is_file():
            continue
        try:
            for i, line in enumerate(
                filepath.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if pattern.lower() in line.lower():
                    rel = filepath.relative_to(safe_dir)
                    matches.append(f"{rel}:{i}:{line.rstrip()}")
                    if len(matches) >= 200:
                        matches.append("[... truncated at 200 matches ...]")
                        return "\n".join(matches)
        except OSError:
            continue

    return "\n".join(matches) or f"No matches for '{pattern}' in '{directory}'"


# ── REQ-024: File write and edit ──────────────────────────────────────────────


def write_file(path: str, content: str, workspace: str | Path | None = None) -> str:
    """Write *content* to *path*, creating parent directories as needed."""
    safe = _resolve_safe(path, workspace)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} bytes to {path}"


def edit_file(
    path: str,
    old_string: str,
    new_string: str,
    workspace: str | Path | None = None,
) -> str:
    """Replace the first occurrence of *old_string* with *new_string* in *path*.

    Raises :class:`ValueError` if *old_string* is not found.
    """
    safe = _resolve_safe(path, workspace)
    content = safe.read_text(encoding="utf-8")
    if old_string not in content:
        raise ValueError(f"String not found in '{path}': {old_string!r}")
    new_content = content.replace(old_string, new_string, 1)
    safe.write_text(new_content, encoding="utf-8")
    return f"Successfully edited '{path}'"
