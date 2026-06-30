"""Filesystem boundary helpers shared by the read-only bridge tools.

All path handling fails closed: relative-only inputs, no traversal, no drive
letters, no NUL bytes, no symlink escapes. Resolved paths must stay within an
allowlisted root.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path, PurePosixPath
from typing import NamedTuple


class SafeFile(NamedTuple):
    path: Path
    rel: str
    size: int


class PathSafetyError(PermissionError):
    """Raised when a requested path violates a filesystem boundary rule."""


def _is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base)
        return True
    except ValueError:
        return False


def normalize_relative_path(raw: object, *, default: str = ".") -> str:
    """Validate and normalise a caller-supplied POSIX-style relative path."""
    text = str(raw if raw is not None else "").strip()
    if not text:
        text = default
    if "\x00" in text:
        raise PathSafetyError("NUL bytes are not allowed in paths.")
    if "\\" in text:
        raise PathSafetyError(
            "Backslashes are not allowed; use POSIX-style relative paths."
        )
    rel = PurePosixPath(text)
    if rel.is_absolute():
        raise PathSafetyError("Absolute paths are not allowed.")
    if any(part in {"", ".", ".."} for part in rel.parts):
        if rel.as_posix() != ".":
            raise PathSafetyError(
                "Path segments '.', '..', and empty segments are not allowed."
            )
    for part in rel.parts:
        if ":" in part:
            raise PathSafetyError(
                "Drive letters and URI-like path segments are not allowed."
            )
    return rel.as_posix()


def ensure_resolved_within(root: Path, candidate: Path) -> Path:
    """Resolve ``candidate`` and confirm it stays inside ``root``."""
    root_resolved = root.resolve()
    resolved = candidate.resolve()
    if not _is_within(root_resolved, resolved):
        raise PathSafetyError("Path escapes allowed root.")
    return resolved


def iter_safe_files(
    root: Path,
    *,
    allowed_exts: Iterable[str] | None = None,
    max_file_bytes: int | None = None,
    follow_symlinks: bool = False,
) -> Iterator[SafeFile]:
    """Yield files under ``root`` that satisfy the safety constraints."""
    root_resolved = root.resolve()
    exts = {e.lower() for e in allowed_exts} if allowed_exts else None
    for discovered in root_resolved.rglob("*"):
        try:
            if discovered.is_symlink() and not follow_symlinks:
                continue
            resolved = discovered.resolve()
            if not _is_within(root_resolved, resolved):
                continue
            if not resolved.is_file():
                continue
            if exts is not None and resolved.suffix.lower() not in exts:
                continue
            stat = resolved.stat()
            if max_file_bytes is not None and stat.st_size > max_file_bytes:
                continue
            rel = resolved.relative_to(root_resolved).as_posix()
            yield SafeFile(resolved, rel, stat.st_size)
        except (OSError, RuntimeError, ValueError):
            continue
