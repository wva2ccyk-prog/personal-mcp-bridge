from __future__ import annotations

from pathlib import Path

import pytest

from personal_mcp_bridge.bridge import ReadOnlyBridge
from personal_mcp_bridge.fs_safety import PathSafetyError
from personal_mcp_bridge.roots import RootRegistry


def test_empty_registry_blocks_all():
    reg = RootRegistry({})
    assert reg.is_empty
    bridge = ReadOnlyBridge(reg)
    assert bridge.list_roots() == {"roots": [], "empty": True}
    with pytest.raises(PathSafetyError):
        bridge.read_file("notes", "welcome.md")


def test_list_roots_hides_local_paths_by_default(registry):
    bridge = ReadOnlyBridge(registry)
    out = bridge.list_roots()
    assert out["roots"] == [{"alias": "notes"}]
    assert out["empty"] is False


def test_read_file_returns_alias_relative_ref(registry):
    bridge = ReadOnlyBridge(registry)
    out = bridge.read_file("notes", "welcome.md")
    assert out["ref"] == "notes/welcome.md"
    assert "budget" in out["content"]
    assert "local_path" not in out


def test_unknown_root_is_refused(registry):
    bridge = ReadOnlyBridge(registry)
    with pytest.raises(PathSafetyError):
        bridge.read_file("secrets", "x.md")


@pytest.mark.parametrize(
    "bad",
    ["../escape", "..\\escape", "/etc/passwd", "C:/Windows", "a/../../b", "x\x00y"],
)
def test_traversal_inputs_refused(registry, bad):
    bridge = ReadOnlyBridge(registry)
    with pytest.raises(PathSafetyError):
        bridge.read_file("notes", bad)


def test_symlink_escape_not_followed(registry, tmp_path: Path, sample_root: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("TOPSECRET budget\n", "utf-8")
    link = sample_root / "link.md"
    try:
        link.symlink_to(outside / "secret.md")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted in this environment")
    bridge = ReadOnlyBridge(registry)
    # The symlink resolves outside the root, so reading it must be refused.
    with pytest.raises(PathSafetyError):
        bridge.read_file("notes", "link.md")
    # And search must not surface its contents.
    result = bridge.search("notes", "TOPSECRET")
    assert result.matches == []


def test_search_finds_matches_with_refs(registry):
    bridge = ReadOnlyBridge(registry)
    result = bridge.search("notes", "budget")
    refs = {m.ref for m in result.matches}
    assert "notes/welcome.md" in refs
    assert "notes/sub/deep.md" in refs
    assert result.truncated is False


def test_search_empty_query_returns_nothing(registry):
    bridge = ReadOnlyBridge(registry)
    result = bridge.search("notes", "")
    assert result.matches == []


def test_read_is_size_bounded(registry, sample_root: Path):
    big = sample_root / "big.txt"
    big.write_text("x" * 5000, "utf-8")
    bridge = ReadOnlyBridge(registry, max_read_bytes=1000)
    out = bridge.read_file("notes", "big.txt")
    assert out["truncated"] is True
    assert out["bytes"] == 1000


def test_include_local_paths_only_in_private_mode(registry, monkeypatch):
    monkeypatch.setenv("INCLUDE_LOCAL_PATHS", "1")
    bridge = ReadOnlyBridge(registry)
    out = bridge.read_file("notes", "welcome.md")
    assert "local_path" in out
    # In public mode the same flag is ignored.
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    out2 = bridge.list_roots()
    assert out2["roots"] == [{"alias": "notes"}]
