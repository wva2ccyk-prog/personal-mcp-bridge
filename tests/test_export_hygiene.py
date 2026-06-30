"""Export-hygiene gate.

Scans the entire export tree and fails if any private surface leaked in:
forbidden runtime databases, agent/pilot machinery, private operating-system
coupling, absolute user paths, or auth tokens. This is the leak gate the public
boundary depends on.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

EXPORT_ROOT = Path(__file__).resolve().parent.parent

# Directories that never need scanning (build artifacts, caches, vcs).
_SKIP_DIRS = {
    "__pycache__", ".git", ".pytest_cache", ".hypothesis",
    ".venv", "venv", "build", "dist", ".eggs",
}

# Forbidden filename fragments: agent-runner / pilot / overlay / dashboard etc.
FORBIDDEN_FILENAME_FRAGMENTS = [
    "pilot", "agent_runner", "smoke_agent_runner", "run_web_gpt_agent",
    "codex_adapter", "APPLY_OVERLAY", "INSTALL_OVER_ORIGINAL",
    "RELOCATE_TO_THIS_FOLDER", "START_PATCHED_BRIDGE", "open_dashboard",
    "Run Personal MCP Dashboard", "CHANGED_FILES", "MANIFEST_DIRECT_OVERLAY",
    "audit.sqlite3", "cache.sqlite3", "agent_pilot_config",
]

FORBIDDEN_FILE_EXTS = {".sqlite3", ".vbs"}

# Forbidden content substrings: private workflow identifiers + coupling terms.
FORBIDDEN_CONTENT = [
    "pilot_", "agent_runner", ".kiro", "agent_pilot_config",
    "phase1_pilot", "plan_pilot_real", "PERSONAL_BRIDGE_TOKEN",
    "conversation_memory", "audit.sqlite3", "cache.sqlite3",
]

# Private handoff / operating-system terms. We avoid matching this test file
# itself and the security docs, which legitimately describe what is excluded.
HANDOFF_TERMS = ["handoff", "Kiro", "AGENTS.md"]

# Absolute-user-path patterns (Windows + POSIX home dirs).
ABS_PATH_RE = re.compile(r"[A-Za-z]:\\\\Users\\\\|[A-Za-z]:/Users/|/home/[a-z]|/Users/[A-Z]")

# Token-like strings: long hex/base64 runs that could be a real secret.
# Identifiers (snake_case) are excluded by rejecting underscores at match time.
TOKEN_RE = re.compile(r"\b(?:[A-Fa-f0-9]{40,}|[A-Za-z0-9\-]{48,})\b")

_TEXT_EXTS = {
    ".py", ".md", ".txt", ".toml", ".cfg", ".ini", ".yaml", ".yml",
    ".json", ".example", ".gitignore", "",
}

# Files allowed to mention forbidden terms because they document the exclusions
# or carry illustrative placeholder paths/tokens.
_DOC_ALLOWLIST = {
    "SECURITY.md",
    "THREAT_MODEL.md",
    "test_export_hygiene.py",
    "README.md",
    ".env.example",
}


def _iter_files():
    for path in EXPORT_ROOT.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def test_no_forbidden_filenames():
    offenders = []
    for path in _iter_files():
        name = path.name
        if path.suffix.lower() in FORBIDDEN_FILE_EXTS:
            offenders.append(str(path))
            continue
        for frag in FORBIDDEN_FILENAME_FRAGMENTS:
            if frag.lower() in name.lower():
                offenders.append(str(path))
                break
    assert offenders == [], f"forbidden files leaked: {offenders}"


def test_no_forbidden_content():
    offenders = []
    for path in _iter_files():
        if path.suffix.lower() not in _TEXT_EXTS:
            continue
        if path.name in _DOC_ALLOWLIST:
            continue
        text = path.read_text("utf-8", errors="ignore")
        for needle in FORBIDDEN_CONTENT:
            if needle in text:
                offenders.append(f"{path.name}: {needle!r}")
    assert offenders == [], f"forbidden content leaked: {offenders}"


def test_no_private_handoff_terms():
    offenders = []
    for path in _iter_files():
        if path.suffix.lower() not in _TEXT_EXTS:
            continue
        if path.name in _DOC_ALLOWLIST:
            continue
        text = path.read_text("utf-8", errors="ignore")
        for term in HANDOFF_TERMS:
            if term.lower() in text.lower():
                offenders.append(f"{path.name}: {term!r}")
    assert offenders == [], f"private handoff terms leaked: {offenders}"


def test_no_absolute_user_paths():
    # Absolute-user-path scanning has no documentation exception: not even the
    # README or .env.example may carry a real home-dir path.
    offenders = []
    for path in _iter_files():
        if path.suffix.lower() not in _TEXT_EXTS:
            continue
        if path.name == "test_export_hygiene.py":
            continue
        text = path.read_text("utf-8", errors="ignore")
        if ABS_PATH_RE.search(text):
            offenders.append(str(path.name))
    assert offenders == [], f"absolute user paths leaked: {offenders}"


def test_no_token_like_strings():
    offenders = []
    for path in _iter_files():
        if path.suffix.lower() not in _TEXT_EXTS:
            continue
        if path.name in _DOC_ALLOWLIST:
            continue
        text = path.read_text("utf-8", errors="ignore")
        for line in text.splitlines():
            # Ignore obvious placeholders and repeated-char demo tokens.
            if set(line.strip()) <= {"x"} | set("xX= "):
                continue
            for match in TOKEN_RE.findall(line):
                if len(set(match)) <= 2:
                    continue  # e.g. "xxxxxxxx..." demo placeholder
                offenders.append(f"{path.name}: {match[:12]}...")
    assert offenders == [], f"token-like strings found: {offenders}"


@pytest.mark.parametrize(
    "forbidden_dir",
    ["runtime", ".kiro", "scripts"],
)
def test_excluded_dirs_absent(forbidden_dir):
    assert not (EXPORT_ROOT / forbidden_dir).exists(), (
        f"{forbidden_dir}/ must not exist in the public export"
    )
