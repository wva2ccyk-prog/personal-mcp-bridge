"""Run-the-demo: boot the real bridge against synthetic mock data.

This script does not touch any of your real files. It allowlists only the
bundled ``demo/mock_data`` directory under two aliases, starts the actual
uvicorn server on a loopback port, and drives the three read-only tools over
HTTP using only the standard library. No test or HTTP client dependency is
required beyond the runtime deps (starlette + uvicorn).

Run it from anywhere::

    python demo/run_demo.py
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Make the package importable when run from a clean checkout without install.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import uvicorn  # noqa: E402

from personal_mcp_bridge.roots import RootRegistry  # noqa: E402
from personal_mcp_bridge.server import create_app  # noqa: E402

HOST = "127.0.0.1"
PORT = 8799
BASE = f"http://{HOST}:{PORT}"


def build_demo_registry() -> RootRegistry:
    base = Path(__file__).resolve().parent / "mock_data"
    return RootRegistry(
        {
            "notes": base / "notes",
            "reports": base / "reports",
        }
    )


def _get(endpoint: str, **params) -> tuple[int, dict]:
    url = BASE + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> int:
    registry = build_demo_registry()
    app = create_app(registry)
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(50):
            if server.started:
                break
            time.sleep(0.1)

        print("== health ==")
        print(json.dumps(_get("/health")[1], indent=2))

        print("\n== list_roots ==")
        print(json.dumps(_get("/roots")[1], indent=2))

        print("\n== read_file notes/welcome.md ==")
        print(json.dumps(_get("/read", root="notes", path="welcome.md")[1], indent=2))

        print("\n== search reports for 'budget' ==")
        print(json.dumps(_get("/search", root="reports", q="budget")[1], indent=2))

        print("\n== traversal attempt is refused ==")
        status, body = _get("/read", root="notes", path="../../secret")
        print(status, json.dumps(body))
    finally:
        server.should_exit = True
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
