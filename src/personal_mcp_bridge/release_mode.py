"""Release / exposure mode helpers.

These helpers centralise the difference between a private localhost session and
a session that is (or may be) exposed to a remote network through a tunnel.

Key ideas:

1. ``public_mode_enabled()`` -- the operator has declared this process is meant
   to be reachable from outside localhost (``BRIDGE_PUBLIC_MODE=1`` or the
   common tunnel flag ``BRIDGE_TUNNEL_MODE=1``). In this mode the bridge fails
   closed on unsafe convenience features.

2. ``persistent_token_query_auth_allowed()`` -- whether a *persistent* bridge
   token may be presented through the ``?token=`` URL parameter. URL tokens leak
   through logs, history, proxies, analytics, and referrers, so persistent-token
   URL auth is OFF by default and only enabled for local/dev convenience via
   ``ALLOW_QUERY_TOKEN_AUTH=1``. It is always refused in public mode.

3. ``include_local_paths()`` -- whether web-facing output may include absolute
   local paths. OFF by default and always OFF in public mode; outputs expose
   alias-relative references only.

The startup refusal check (:func:`assert_release_mode_safe`) blocks the most
dangerous combinations before the server begins serving in public mode.
"""

from __future__ import annotations

import os


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip() in {"1", "true", "True", "yes", "on"}


def public_mode_enabled() -> bool:
    """True when the operator declared this process may be exposed off-localhost."""
    return _truthy("BRIDGE_PUBLIC_MODE") or _truthy("BRIDGE_TUNNEL_MODE")


def persistent_token_query_auth_allowed() -> bool:
    """Whether a persistent bridge token may be presented via ``?token=``.

    Off by default. Enabled only by an explicit local/dev opt-in, and never
    honoured in public/tunnel mode regardless of the flag.
    """
    if public_mode_enabled():
        return False
    return _truthy("ALLOW_QUERY_TOKEN_AUTH")


def include_local_paths() -> bool:
    """Whether web-facing outputs may include absolute local paths (debug only)."""
    if public_mode_enabled():
        return False
    return _truthy("INCLUDE_LOCAL_PATHS")


def generic_call_remote_allowed() -> bool:
    """The generic ``/call`` dispatch endpoint is localhost-only by design.

    It is never reachable for remote/forwarded requests. There is no flag to
    relax this; remote callers must use the dedicated read-only endpoints.
    """
    return False


def release_mode_problems() -> list[str]:
    """Return unsafe-configuration strings for the current environment.

    Empty list means no blocking problem was detected. This is only meaningful
    when :func:`public_mode_enabled` is true; in private/local mode the bridge
    intentionally allows developer conveniences.
    """
    problems: list[str] = []
    if not public_mode_enabled():
        return problems

    token = os.getenv("BRIDGE_TOKEN", "")
    if not token:
        problems.append("BRIDGE_TOKEN is required in public/tunnel mode.")
    elif len(token) < 32:
        problems.append(
            "BRIDGE_TOKEN must be at least 32 characters in public/tunnel mode."
        )

    if _truthy("ALLOW_QUERY_TOKEN_AUTH"):
        problems.append(
            "ALLOW_QUERY_TOKEN_AUTH=1 is not honoured and must not be set in "
            "public/tunnel mode; use short-lived session tokens instead."
        )

    if _truthy("INCLUDE_LOCAL_PATHS"):
        problems.append(
            "INCLUDE_LOCAL_PATHS=1 must not be set in public/tunnel mode; "
            "web-facing output must expose alias-relative refs only."
        )

    return problems


def assert_release_mode_safe() -> None:
    """Raise ``RuntimeError`` if public/tunnel mode is on with an unsafe combo.

    Called at server startup. In private/local mode this is a no-op.
    """
    problems = release_mode_problems()
    if problems:
        joined = "\n  - ".join(problems)
        raise RuntimeError(
            "Refusing to start in public/tunnel mode with unsafe configuration:\n  - "
            + joined
        )


def startup_diagnostic() -> dict:
    """Compact, path-free snapshot of the current exposure posture."""
    return {
        "public_mode": public_mode_enabled(),
        "persistent_token_query_auth_allowed": persistent_token_query_auth_allowed(),
        "include_local_paths": include_local_paths(),
        "generic_call_remote_allowed": generic_call_remote_allowed(),
        "problems": release_mode_problems(),
    }
