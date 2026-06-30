from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

from personal_mcp_bridge.roots import RootRegistry  # noqa: E402


@pytest.fixture
def sample_root(tmp_path: Path) -> Path:
    root = tmp_path / "notes"
    root.mkdir()
    (root / "welcome.md").write_text("hello budget world\nsecond line\n", "utf-8")
    (root / "todo.txt").write_text("buy milk\nplan roadmap\n", "utf-8")
    sub = root / "sub"
    sub.mkdir()
    (sub / "deep.md").write_text("budget appears here too\n", "utf-8")
    return root


@pytest.fixture
def registry(sample_root: Path) -> RootRegistry:
    return RootRegistry({"notes": sample_root})


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "BRIDGE_PUBLIC_MODE",
        "BRIDGE_TUNNEL_MODE",
        "BRIDGE_TOKEN",
        "ALLOW_QUERY_TOKEN_AUTH",
        "INCLUDE_LOCAL_PATHS",
        "BRIDGE_ROOTS",
    ):
        monkeypatch.delenv(name, raising=False)
