"""The minimal read-only bridge: list roots, read a file, search text.

Every result is shaped for web-facing safety: references are alias-relative,
never absolute local paths (unless local-path debug output is explicitly
enabled in private mode). Reads and searches are bounded in size so a caller
cannot exhaust memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .fs_safety import iter_safe_files
from .release_mode import include_local_paths
from .roots import RootRegistry

DEFAULT_MAX_READ_BYTES = 256 * 1024
DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_MATCHES = 200
TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".log", ".py", ".js", ".ts", ".html", ".css",
}


@dataclass
class SearchMatch:
    ref: str
    line: int
    text: str


@dataclass
class SearchResult:
    query: str
    matches: list[SearchMatch] = field(default_factory=list)
    truncated: bool = False


class ReadOnlyBridge:
    def __init__(
        self,
        registry: RootRegistry,
        *,
        max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_matches: int = DEFAULT_MAX_MATCHES,
    ) -> None:
        self.registry = registry
        self.max_read_bytes = max_read_bytes
        self.max_file_bytes = max_file_bytes
        self.max_matches = max_matches

    def list_roots(self) -> dict:
        """List allowlisted roots as public aliases.

        Absolute local paths are included only when local-path debug output is
        explicitly enabled in private mode.
        """
        expose_paths = include_local_paths()
        roots = []
        for alias in self.registry.aliases():
            entry: dict = {"alias": alias}
            if expose_paths:
                entry["local_path"] = str(self.registry.root_path(alias))
            roots.append(entry)
        return {"roots": roots, "empty": self.registry.is_empty}

    def read_file(self, alias: str, rel_path: str) -> dict:
        """Read a single allowlisted text file, bounded by ``max_read_bytes``."""
        resolved = self.registry.resolve(alias, rel_path)
        if not resolved.is_file():
            raise FileNotFoundError(f"Not a file: {alias}/{rel_path}")
        data = resolved.read_bytes()
        truncated = len(data) > self.max_read_bytes
        if truncated:
            data = data[: self.max_read_bytes]
        text = data.decode("utf-8", errors="replace")
        root = self.registry.root_path(alias)
        rel = resolved.relative_to(root).as_posix()
        result = {
            "ref": self.registry.public_ref(alias, rel),
            "content": text,
            "truncated": truncated,
            "bytes": len(data),
        }
        if include_local_paths():
            result["local_path"] = str(resolved)
        return result

    def search(self, alias: str, query: str, *, case_sensitive: bool = False) -> SearchResult:
        """Search text files under an allowlisted root for ``query``."""
        query = str(query or "")
        result = SearchResult(query=query)
        if not query:
            return result
        root = self.registry.root_path(alias)
        needle = query if case_sensitive else query.lower()
        for safe in iter_safe_files(
            root, allowed_exts=TEXT_EXTS, max_file_bytes=self.max_file_bytes
        ):
            try:
                content = safe.path.read_text("utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), start=1):
                hay = line if case_sensitive else line.lower()
                if needle in hay:
                    if len(result.matches) >= self.max_matches:
                        result.truncated = True
                        return result
                    result.matches.append(
                        SearchMatch(
                            ref=self.registry.public_ref(alias, safe.rel),
                            line=lineno,
                            text=line.strip()[:400],
                        )
                    )
        return result
