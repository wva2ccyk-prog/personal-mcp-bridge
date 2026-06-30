"""Run the read-only bridge with uvicorn.

Usage::

    python -m personal_mcp_bridge

Honours ``BRIDGE_HOST`` (default ``127.0.0.1``) and ``BRIDGE_PORT``
(default ``8787``). The default host is loopback on purpose; binding to a
public interface requires the operator to set it explicitly and to satisfy the
public-mode safety checks.
"""

from __future__ import annotations

import os

import uvicorn

from .server import create_app


def main() -> None:
    app = create_app()
    uvicorn.run(
        app,
        host=os.getenv("BRIDGE_HOST", "127.0.0.1"),
        port=int(os.getenv("BRIDGE_PORT", "8787")),
        reload=False,
    )


if __name__ == "__main__":
    main()
