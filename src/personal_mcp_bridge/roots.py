"""Allowlisted root registry.

The bridge only ever serves files inside explicitly allowlisted roots. Each
root has a stable *alias* (a short public name) and a local absolute path. All
web-facing output references files as ``alias/relative/path`` and never leaks
the absolute local path unless local-path debug output is explicitly enabled in
private mode.

Default behaviour is fail-closed: with no configured roots, every request is
blocked. This is allowlist mode with an empty list = block all.

Configuration is via the ``BRIDGE_ROOTS`` environment variable, a
semicolon-separated list of ``alias=absolute_path`` pairs, e.g.::

    BRIDGE_ROOTS="notes=/path/to/notes;docs=/path/to/work/docs"

Aliases must match ``[A-Za-z0-9_-]+``. Paths must already exist and be
directories; invalid entries are skipped (fail closed, never fail open).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .fs_safety import PathSafetyError, ensure_resolved_within, normalize_relative_path

_ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Root:
    alias: str
    path: Path


class RootRegistry:
    """Holds the allowlisted roots and resolves alias-relative references."""

    def __init__(self, roots: dict[str, Path] | None = None) -> None:
        self._roots: dict[str, Path] = {}
        for alias, path in (roots or {}).items():
            self._add(alias, path)

    def _add(self, alias: str, path: Path) -> None:
        if not _ALIAS_RE.match(alias):
            return
        try:
            resolved = Path(path).resolve()
        except (OSError, RuntimeError, ValueError):
            return
        if not resolved.is_dir():
            return
        self._roots[alias] = resolved

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "RootRegistry":
        source = env if env is not None else os.environ
        raw = source.get("BRIDGE_ROOTS", "").strip()
        roots: dict[str, Path] = {}
        if raw:
            for entry in raw.split(";"):
                entry = entry.strip()
                if not entry or "=" not in entry:
                    continue
                alias, _, path = entry.partition("=")
                alias = alias.strip()
                path = path.strip()
                if alias and path:
                    roots[alias] = Path(path)
        return cls(roots)

    @property
    def is_empty(self) -> bool:
        return not self._roots

    def aliases(self) -> list[str]:
        return sorted(self._roots)

    def has(self, alias: str) -> bool:
        return alias in self._roots

    def root_path(self, alias: str) -> Path:
        if alias not in self._roots:
            raise PathSafetyError(f"Unknown or non-allowlisted root: {alias!r}")
        return self._roots[alias]

    def resolve(self, alias: str, rel_path: object) -> Path:
        """Resolve ``alias`` + relative path to a safe absolute path.

        Raises :class:`PathSafetyError` if the alias is not allowlisted or the
        path escapes the root.
        """
        root = self.root_path(alias)
        rel = normalize_relative_path(rel_path)
        candidate = root if rel == "." else root / rel
        return ensure_resolved_within(root, candidate)

    def public_ref(self, alias: str, rel_path: str) -> str:
        """Build the alias-relative reference exposed to web-facing callers."""
        rel = rel_path.strip("/")
        return alias if not rel or rel == "." else f"{alias}/{rel}"
