from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from personal_mcp_bridge import release_mode
from personal_mcp_bridge.server import create_app

STRONG = "x" * 40


def _client(registry, **headers):
    app = create_app(registry)
    # Present a loopback peer so localhost-only checks behave as in production.
    return TestClient(app, headers=headers, client=("127.0.0.1", 12345))


def test_public_mode_refuses_start_without_token(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    with pytest.raises(RuntimeError):
        create_app(registry)


def test_public_mode_refuses_short_token(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", "short")
    with pytest.raises(RuntimeError):
        create_app(registry)


def test_public_mode_refuses_token_in_url(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", STRONG)
    client = _client(registry)
    r = client.get("/roots", params={"token": STRONG})
    assert r.status_code == 403
    assert r.json()["error"] == "token-in-url-refused"


def test_public_mode_accepts_bearer_header(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", STRONG)
    client = _client(registry, authorization=f"Bearer {STRONG}")
    r = client.get("/roots")
    assert r.status_code == 200
    assert r.json()["roots"] == [{"alias": "notes"}]


def test_public_mode_rejects_bad_bearer(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", STRONG)
    client = _client(registry, authorization="Bearer nope")
    assert client.get("/roots").status_code == 403


def test_generic_call_refused_for_forwarded_request(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", STRONG)
    client = _client(
        registry,
        authorization=f"Bearer {STRONG}",
    )
    r = client.post(
        "/call",
        json={"tool": "list_roots"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert r.status_code == 403
    assert "localhost-only" in r.json()["error"]


def test_generic_call_works_on_loopback(registry):
    # No public mode, loopback client, no forwarded header.
    client = _client(registry)
    r = client.post("/call", json={"tool": "list_roots"})
    assert r.status_code == 200
    assert r.json()["roots"] == [{"alias": "notes"}]


def test_read_response_has_no_local_path_in_public_mode(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", STRONG)
    # INCLUDE_LOCAL_PATHS is ignored in public mode.
    monkeypatch.setenv("INCLUDE_LOCAL_PATHS", "1")
    with pytest.raises(RuntimeError):
        # Setting INCLUDE_LOCAL_PATHS in public mode is itself a refusal.
        create_app(registry)


def test_private_loopback_allows_read_without_token(registry):
    client = _client(registry)
    r = client.get("/read", params={"root": "notes", "path": "welcome.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["ref"] == "notes/welcome.md"
    assert "local_path" not in body


def test_startup_diagnostic_is_path_free(registry, monkeypatch):
    monkeypatch.setenv("BRIDGE_PUBLIC_MODE", "1")
    monkeypatch.setenv("BRIDGE_TOKEN", STRONG)
    diag = release_mode.startup_diagnostic()
    assert diag["public_mode"] is True
    assert diag["persistent_token_query_auth_allowed"] is False
    assert diag["generic_call_remote_allowed"] is False
    assert diag["problems"] == []
