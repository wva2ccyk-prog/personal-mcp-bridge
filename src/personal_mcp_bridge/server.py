"""HTTP surface for the read-only bridge.

Exposure rules enforced here:

- Dedicated read-only endpoints (``/roots``, ``/read``, ``/search``) are the
  only remote-reachable surface. They require a bearer token in public mode.
- A persistent token presented via ``?token=`` is refused in public mode and
  only honoured locally when ``ALLOW_QUERY_TOKEN_AUTH=1`` is set.
- The generic ``/call`` dispatch endpoint is localhost-only. Any request that
  arrives forwarded (``X-Forwarded-For``) or from a non-loopback client is
  refused with 403.
- No response ever contains an absolute local path or the auth token unless
  local-path debug output is explicitly enabled in private mode.
"""

from __future__ import annotations

import ipaddress
import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .bridge import ReadOnlyBridge
from .fs_safety import PathSafetyError
from .release_mode import (
    assert_release_mode_safe,
    persistent_token_query_auth_allowed,
    public_mode_enabled,
    startup_diagnostic,
)
from .roots import RootRegistry


def _client_is_loopback(request: Request) -> bool:
    # A forwarded request never counts as loopback, regardless of socket peer.
    if request.headers.get("x-forwarded-for"):
        return False
    if request.headers.get("forwarded"):
        return False
    client = request.client
    if client is None:
        return False
    try:
        return ipaddress.ip_address(client.host).is_loopback
    except ValueError:
        return False


def _expected_token() -> str:
    return os.getenv("BRIDGE_TOKEN", "").strip()


def _extract_token(request: Request) -> tuple[str | None, str]:
    """Return (token, source) where source is 'header' or 'query' or ''."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip(), "header"
    qtoken = request.query_params.get("token")
    if qtoken:
        return qtoken.strip(), "query"
    return None, ""


def _authorized(request: Request) -> tuple[bool, str]:
    """Authorize a request to a dedicated read-only endpoint.

    Returns (ok, reason). In private/local mode with no token configured, the
    bridge allows loopback callers for convenience. In public mode a strong
    bearer token is mandatory and URL tokens are refused.
    """
    expected = _expected_token()
    token, source = _extract_token(request)

    if source == "query" and not persistent_token_query_auth_allowed():
        return False, "token-in-url-refused"

    if public_mode_enabled():
        if not expected:
            return False, "server-misconfigured-no-token"
        if token != expected:
            return False, "invalid-token"
        return True, "ok"

    # Private/local mode.
    if expected:
        if token != expected:
            return False, "invalid-token"
        return True, "ok"
    if _client_is_loopback(request):
        return True, "ok-loopback"
    return False, "remote-without-token"


def create_app(registry: RootRegistry | None = None) -> Starlette:
    registry = registry if registry is not None else RootRegistry.from_env()
    bridge = ReadOnlyBridge(registry)
    assert_release_mode_safe()

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "exposure": startup_diagnostic()})

    async def roots(request: Request) -> JSONResponse:
        ok, reason = _authorized(request)
        if not ok:
            return JSONResponse({"error": reason}, status_code=403)
        return JSONResponse(bridge.list_roots())

    async def read_file(request: Request) -> JSONResponse:
        ok, reason = _authorized(request)
        if not ok:
            return JSONResponse({"error": reason}, status_code=403)
        alias = request.query_params.get("root", "")
        path = request.query_params.get("path", "")
        try:
            return JSONResponse(bridge.read_file(alias, path))
        except PathSafetyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        except FileNotFoundError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    async def search(request: Request) -> JSONResponse:
        ok, reason = _authorized(request)
        if not ok:
            return JSONResponse({"error": reason}, status_code=403)
        alias = request.query_params.get("root", "")
        query = request.query_params.get("q", "")
        try:
            result = bridge.search(alias, query)
        except PathSafetyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        return JSONResponse(
            {
                "query": result.query,
                "truncated": result.truncated,
                "matches": [
                    {"ref": m.ref, "line": m.line, "text": m.text}
                    for m in result.matches
                ],
            }
        )

    async def call(request: Request) -> JSONResponse:
        # Generic dispatch is localhost-only and never reachable remotely.
        if not _client_is_loopback(request):
            return JSONResponse(
                {"error": "generic /call is localhost-only"}, status_code=403
            )
        ok, reason = _authorized(request)
        if not ok:
            return JSONResponse({"error": reason}, status_code=403)
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            return JSONResponse({"error": "invalid-json"}, status_code=400)
        tool = payload.get("tool")
        args = payload.get("args") or {}
        try:
            if tool == "list_roots":
                return JSONResponse(bridge.list_roots())
            if tool == "read_file":
                return JSONResponse(
                    bridge.read_file(args.get("root", ""), args.get("path", ""))
                )
            if tool == "search":
                result = bridge.search(args.get("root", ""), args.get("q", ""))
                return JSONResponse(
                    {
                        "query": result.query,
                        "truncated": result.truncated,
                        "matches": [
                            {"ref": m.ref, "line": m.line, "text": m.text}
                            for m in result.matches
                        ],
                    }
                )
        except PathSafetyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=403)
        except FileNotFoundError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse({"error": f"unknown-tool: {tool}"}, status_code=400)

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/roots", roots, methods=["GET"]),
        Route("/read", read_file, methods=["GET"]),
        Route("/search", search, methods=["GET"]),
        Route("/call", call, methods=["POST"]),
    ]
    return Starlette(routes=routes)
